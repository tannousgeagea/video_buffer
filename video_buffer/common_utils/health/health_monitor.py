# health_monitor.py
"""
Health monitoring daemon that periodically checks service health
and triggers Supervisor restarts on critical failures
"""
import os
import requests
import time
import logging
import sys
from typing import Dict, Any
from xmlrpc.client import ServerProxy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HEALTH_ENDPOINT = f"http://localhost:{os.getenv('DATA_API_PORT')}/api/v1/health/ready"
CHECK_INTERVAL = 30  # seconds
FAILURE_THRESHOLD = 3  # consecutive failures before restart
SUPERVISOR_RPC = f'http://{os.environ["user"]}:{os.environ["password"]}@localhost:{os.environ["INET_HTTP_SERVER_PORT"]}/RPC2'

class HealthMonitor:
    def __init__(self):
        self.consecutive_failures = 0
        self.supervisor = ServerProxy(SUPERVISOR_RPC)
    
    def check_health(self):
        """Check service health via HTTP endpoint"""
        try:
            response = requests.get(
                HEALTH_ENDPOINT,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Health check passed")
                self.consecutive_failures = 0
                return True
            else:
                logger.warning(
                    f"Health check failed with status {response.status_code}: "
                    f"{response.text}"
                )
                self.consecutive_failures += 1
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Health check error: {e}")
            self.consecutive_failures += 1
            return False
    
    def restart_service(self, service_name:str):
        """Restart FastAPI service via Supervisor"""
        try:
            logger.warning(
                f"Restarting service {service_name} after {self.consecutive_failures} "
                "consecutive failures"
            )
            
            # Stop the service
            self.supervisor.supervisor.stopProcess(service_name)
            time.sleep(2)
            
            # Start the service
            self.supervisor.supervisor.startProcess(service_name)
            
            logger.info(f"Service {service_name} restarted successfully")
            self.consecutive_failures = 0
            
        except Exception as e:
            logger.error(f"Failed to restart service {service_name}: {e}")
    
    def get_running_processes(self) -> Dict[str, Any]:
        """Get all processes running under Supervisor"""
        try:
            processes = self.supervisor.supervisor.getAllProcessInfo()
            
            return {
                "total": len(processes),
                "processes": [
                    {
                        "fullname": f"{p['group']}:{p['name']}" if p['group'] != p['name'] else p['name'],
                        **p
                    }
                    for p in processes
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get processes: {e}")
            return {"error": str(e)}

    def restart_services(self,):
        """Restart multiple services via Supervisor"""
        services = self.get_running_processes()
        for service in services['processes']:
            if 'health' in service['fullname']:
                continue
            
            self.restart_service(service_name=service['fullname'])

    def run(self):
        """Main monitoring loop"""
        logger.info("Health monitor started")
        
        # Wait for service to start
        time.sleep(10)
        
        while True:
            try:
                is_healthy = self.check_health()
                
                if not is_healthy:
                    if self.consecutive_failures >= FAILURE_THRESHOLD:
                        self.restart_services()
                        # Wait longer after restart
                        time.sleep(60)
                    else:
                        logger.warning(
                            f"Failure count: {self.consecutive_failures}/"
                            f"{FAILURE_THRESHOLD}"
                        )
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Health monitor stopped")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor = HealthMonitor()
    monitor.run()