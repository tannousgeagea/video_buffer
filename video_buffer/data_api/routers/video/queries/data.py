import os
import time
import math
import django
from django.db import connection
from django.db.models import Q
from fastapi import status
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Callable, List
from fastapi import Request
from fastapi import Response
from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel
from fastapi.routing import APIRoute

django.setup()
from django.core.exceptions import ObjectDoesNotExist
from database.models import Video


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"

class TimedRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        async def custom_route_handler(request: Request) -> Response:
            before = time.time()
            response: Response = await original_route_handler(request)
            duration = time.time() - before
            response.headers["X-Response-Time"] = str(duration)
            print(f"route duration: {duration}")
            print(f"route response: {response}")
            print(f"route response headers: {response.headers}")
            return response

        return custom_route_handler
    

router = APIRouter(
    route_class=TimedRoute,
)



class VideoItemResponse(BaseModel):
    """Schema for an individual video record."""
    video_id: str
    date: str
    start: str
    end: str
    location: str
    
class VideoResponse(BaseModel):
    """Schema for the overall delivery response."""
    type: str
    total_record: int
    pages: int
    items: List[VideoItemResponse]

description = """
    TO DO
"""

@router.api_route(
    "/video", methods=["GET"], tags=["Video"], description=description
)
def get_data(
    response: Response, 
    gate_id:str=None, 
    from_date:datetime=None, 
    to_date:datetime=None, 
    items_per_page:int=15, 
    page:int=1, 
    metadata_id:int=1
    ):
    results:dict = {}
    try:
        
        result = []
        today = datetime.today()
        if from_date is None:
            from_date = datetime(today.year, today.month, today.day)
        
        if to_date is None:
            to_date = from_date + timedelta(days=1)
            
        from_date = from_date.replace(tzinfo=timezone.utc)
        to_date = to_date.replace(tzinfo=timezone.utc) + timedelta(days=1)
        
        if page < 1:
            page = 1
        
        if items_per_page==0:
            results['error'] = {
                'status_code': 'bad request',
                'status_description': f'Bad Request, items_per_pages should not be 0',
                'detail': "division by zero."
            }

            response.status_code = status.HTTP_400_BAD_REQUEST
            return results
        
        videos = Video.objects.filter(created_at__range=(from_date, to_date)).order_by('-created_at')
        rows = []
        total_record = len(videos)
        for video in videos[(page - 1) * items_per_page:page * items_per_page]:
            
            beginn = video.start_time
            ende = video.end_time


              
            row = VideoItemResponse(
                video_id=video.video_id,
                date=(beginn + timedelta(hours=2)).strftime('%Y-%m-%d'),
                start=(beginn + timedelta(hours=2)).strftime('%H:%M:%S'),
                end=(ende + timedelta(hours=2)).strftime('%H:%M:%S'),
                location='Tor06'
            )
            
            rows.append(row.dict())
        
        results = {
            "data": VideoResponse(
            type='collection',
            total_record=total_record,
            pages=math.ceil(total_record / items_per_page),
            items=rows,
        )
        }
        return results
        
        
    except ObjectDoesNotExist as e:
        results['error'] = {
            'status_code': "non-matching-query",
            'status_description': f'Matching query was not found',
            'detail': f"matching query does not exist. {e}"
        }

        response.status_code = status.HTTP_404_NOT_FOUND
        
    except HTTPException as e:
        results['error'] = {
            "status_code": "not found",
            "status_description": "Request not Found",
            "detail": f"{e}",
        }
        
        response.status_code = status.HTTP_404_NOT_FOUND
    
    except Exception as e:
        results['error'] = {
            'status_code': 'server-error',
            "status_description": "Internal Server Error",
            "detail": str(e),
        }
        
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return results