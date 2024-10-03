

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
from typing import Callable
from fastapi import Request
from fastapi import Response
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi.routing import APIRoute

django.setup()
from django.core.exceptions import ObjectDoesNotExist
from metadata.models import (
    Metadata,
    MetadataColumn,
    MetadataLocalization,
    Language,
)

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


summary="Retrieve Delivery Metadata"
description="""
Retrieves the metadata for delivery information in the specified language.

The metadata includes the column titles, types, and descriptions based on the specified language code (e.g., "en" for English, "de" for German). 
The `metadata_id` is used to specify which set of metadata to retrieve.

### Path Parameters
- **language**: A string representing the language code (e.g., "en" for English, "de" for German). Default is "de".

### Query Parameters
- **metadata_id**: An integer representing the ID of the metadata to retrieve. Default is 1.

### Responses
- **200 OK**: Returns the metadata details.
- **404 Not Found**: Returns an error if the specified metadata ID or language is not found.
- **500 Internal Server Error**: Returns an error if an unexpected error occurs.
"""


@router.api_route(
    "/video/metadata/{language}", methods=["GET"], tags=["Video"], summary=summary, description=description,
)
def get_delivery_metadata(response: Response, language:str="de", metadata_id:int=1):
    metadata = {}
    try:
        if not MetadataColumn.objects.filter(metadata_id=metadata_id).exists():
            metadata = {
                "error": {
                    "status_code": "not found",
                    "status_description": f"Metadata ID {metadata_id} not found",
                    "deatil": f"Metadata ID {metadata_id} not found",
                }
            }
            
            response.status_code = status.HTTP_404_NOT_FOUND
            return metadata

        if not Language.objects.filter(code=language).exists():
            metadata["error"] = {
                "status_code": "not found",
                "status_description": f"language {language} not found",
                "detail": f"language {language} not found",
            }
        
            response.status_code = status.HTTP_404_NOT_FOUND
            return metadata

        language = Language.objects.get(code=language)
        columns = MetadataColumn.objects.filter(metadata_id=metadata_id).select_related('metadata').prefetch_related('localizations')

        col = []
        for column in columns:
            localization = column.localizations.filter(language=language).first()
            if not localization:
                metadata = {
                    "error": {
                        "status_code": "not found",
                        "status_description": f"language {language} not found",
                        "deatil": f"language {language} not found",
                    }
                }
                
                response.status_code = status.HTTP_404_NOT_FOUND
                return metadata
            
            col.append(
                {
                    column.column_name: {
                        "title": localization.title,
                        "type": column.type,
                        "description": localization.description                        
                    }

                }
            )
            
        metadata = {
            "metadata":{
                "columns": col,
                "primary_key": Metadata.objects.get(id=metadata_id).primary_key,
            }
        }
        
        return metadata

    except Exception as e:
        metadata = {
            "error": {
                "status_code": "internal server error",
                "status_description": f"Error {e}",
                "deatil": f"Error: {e}",
            }
        }
        
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return metadata