"""
Health Check Endpoint for Django + FastAPI System
Monitors database, Celery, disk space, and service uptime
"""
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from django.db import connection, connections, close_old_connections
from django.core.cache import cache
from datetime import datetime
from typing import Dict, Any
import psutil
import time
import os
from asgiref.sync import sync_to_async
from celery import Celery
from celery.exceptions import OperationalError as CeleryOperationalError

router = APIRouter()



# Track service start time
SERVICE_START_TIME = time.time()

# Configure Celery (adjust broker URL as needed)

RABBITMQ_PORT = os.environ.get('RABBITMQ_PORT', "5672")
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', "localhost")
celery_app = Celery(
    'health_check',
    broker=os.environ.get("CELERY_BROKER_URL", f"amqp://guest:guest@{RABBITMQ_HOST}:{RABBITMQ_PORT}//")
)

celery_app.conf.update(accept_content=['json', 'pickle'])

class HealthCheckError(Exception):
    """Custom exception for health check failures"""
    pass

@sync_to_async
def check_database() -> Dict[str, Any]:
    """
    Check database connectivity via Django ORM
    Returns status and details about the connection
    """
    try:
        start_time = time.time()
        # Test default database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        response_time_ms = (time.time() - start_time) * 1000
        # Get connection info
        db_vendor = connection.vendor
        db_name = connection.settings_dict.get('NAME', 'unknown')
        
        # Check all configured databases
        all_dbs_healthy = True
        db_statuses = {}
        
        for db_alias in connections:
            try:
                with connections[db_alias].cursor() as cursor:
                    cursor.execute("SELECT 1")
                db_statuses[db_alias] = "healthy"
            except Exception as e:
                all_dbs_healthy = False
                db_statuses[db_alias] = f"error: {str(e)}"
        
        return {
            "status": "healthy" if all_dbs_healthy else "degraded",
            "vendor": db_vendor,
            "database": db_name,
            "databases": db_statuses,
            "response_time_ms": response_time_ms
        }
    except Exception as e:
        raise HealthCheckError(f"Database check failed: {str(e)}")


def check_celery(timeout: int = 5) -> Dict[str, Any]:
    """
    Check Celery broker reachability
    Attempts to inspect active workers
    """
    try:
        # Check broker connection
        inspector = celery_app.control.inspect(timeout=timeout)
        
        # Try to get active workers
        active = inspector.active()
        
        if active is None:
            # No workers responding, but broker is reachable
            return {
                "status": "degraded",
                "broker": celery_app.connection().as_uri(),
                "workers": 0,
                "message": "Broker reachable but no workers responding"
            }
        
        worker_count = len(active)
        
        return {
            "status": "healthy",
            "broker": celery_app.connection().as_uri(),
            "workers": worker_count,
            "worker_names": list(active.keys())
        }
    except CeleryOperationalError as e:
        raise HealthCheckError(f"Celery broker unreachable: {str(e)}")
    except Exception as e:
        raise HealthCheckError(f"Celery check failed: {str(e)}")


def check_disk_space(threshold_percent: float = 90.0) -> Dict[str, Any]:
    """
    Check disk space availability
    Raises error if usage exceeds threshold
    """
    try:
        disk_usage = psutil.disk_usage('/')
        
        percent_used = disk_usage.percent
        is_critical = percent_used >= threshold_percent
        
        return {
            "status": "critical" if is_critical else "healthy",
            "total_gb": round(disk_usage.total / (1024**3), 2),
            "used_gb": round(disk_usage.used / (1024**3), 2),
            "free_gb": round(disk_usage.free / (1024**3), 2),
            "percent_used": percent_used,
            "threshold_percent": threshold_percent
        }
    except Exception as e:
        raise HealthCheckError(f"Disk check failed: {str(e)}")


def check_cache() -> Dict[str, Any]:
    """
    Check cache backend (Redis/Memcached) availability
    """
    try:
        # Try to set and get a test value
        test_key = "_health_check_test"
        test_value = str(time.time())
        
        cache.set(test_key, test_value, timeout=60)
        retrieved = cache.get(test_key)
        
        if retrieved != test_value:
            raise HealthCheckError("Cache value mismatch")
        
        cache.delete(test_key)
        
        return {
            "status": "healthy",
            "backend": cache.__class__.__name__
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "message": "Cache unavailable but not critical"
        }


def get_uptime_info() -> Dict[str, Any]:
    """
    Get service uptime and system metadata
    """
    uptime_seconds = time.time() - SERVICE_START_TIME
    
    return {
        "service_start_time": datetime.fromtimestamp(SERVICE_START_TIME).isoformat(),
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_hours": round(uptime_seconds / 3600, 2),
        "current_time": datetime.now().isoformat(),
        "pid": os.getpid(),
        "hostname": os.getenv('HOSTNAME', 'unknown')
    }


@router.get("/health")
async def health_check(
    include_celery: bool = True,
    include_disk: bool = True,
    include_cache: bool = True
):
    """
    Comprehensive health check endpoint
    
    Query parameters:
    - include_celery: Check Celery broker (default: True)
    - include_disk: Check disk space (default: True)
    - include_cache: Check cache backend (default: True)
    
    Returns:
    - 200: All critical systems healthy
    - 503: One or more critical systems unhealthy
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    errors = []
    has_critical_failure = False
    
    # Critical: Database check (always performed)
    try:
        health_status["checks"]["database"] = await check_database()
        if health_status["checks"]["database"]["status"] == "degraded":
            has_critical_failure = True
            errors.append("Database degraded")
    except HealthCheckError as e:
        has_critical_failure = True
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        errors.append(str(e))
    
    # Optional: Celery check
    if include_celery:
        try:
            health_status["checks"]["celery"] = check_celery()
            if health_status["checks"]["celery"]["status"] == "degraded":
                # Celery degraded is not critical - log but don't fail
                errors.append("Celery degraded")
        except HealthCheckError as e:
            # Celery failure is critical
            has_critical_failure = True
            health_status["checks"]["celery"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            errors.append(str(e))
    
    # Optional: Disk space check
    if include_disk:
        try:
            disk_status = check_disk_space()
            health_status["checks"]["disk"] = disk_status
            if disk_status["status"] == "critical":
                has_critical_failure = True
                errors.append("Disk space critical")
        except HealthCheckError as e:
            health_status["checks"]["disk"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            errors.append(str(e))
    
    # Optional: Cache check (non-critical)
    if include_cache:
        health_status["checks"]["cache"] = check_cache()
        if health_status["checks"]["cache"]["status"] == "degraded":
            errors.append("Cache degraded")
    
    # Always include uptime info
    health_status["uptime"] = get_uptime_info()
    
    # Set overall status
    if has_critical_failure:
        health_status["status"] = "unhealthy"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif errors:
        health_status["status"] = "degraded"
        response_status = status.HTTP_200_OK
    else:
        response_status = status.HTTP_200_OK
    
    if errors:
        health_status["errors"] = errors
    
    return JSONResponse(
        status_code=response_status,
        content=health_status
    )


@router.get("/health/live")
async def liveness_check():
    """
    Simple liveness check - is the service running?
    Use this for Kubernetes liveness probes
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - is the service ready to handle requests?
    Only checks critical dependencies (database)
    """
    try:
        db_check = await check_database()
        if db_check["status"] == "degraded":
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "status": "not_ready",
                    "reason": "Database degraded"
                }
            )
        
        return {
            "status": "ready",
            "timestamp": datetime.now().isoformat()
        }
    except HealthCheckError as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": str(e)
            }
        )