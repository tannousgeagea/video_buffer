import os
import grpc
import json
import sys
import uuid
import time
import logging
from datetime import datetime, timezone, timedelta
from common_utils.models.common import save_image
from data_reader.interface.grpc import data_acquisition_pb2
from data_reader.interface.grpc import data_acquisition_pb2_grpc

def run(payload):
    try:
        with grpc.insecure_channel(f'localhost:{os.environ.get("GRPC_DATA_READER")}') as channel:
            start_time = time.time()
            stub = data_acquisition_pb2_grpc.ComputingUnitStub(channel)
            
            assert isinstance(payload, dict), f"payload are expected to be dict, but got {type(payload)}"
            assert 'cv_image' in payload.keys(), f"key: cv_image not found in payload"
            assert 'img_key' in payload.keys(), f"key: img_key not found in payload"
            assert 'set_name' in payload.keys(), f"key: set_name not found in payload"
            
            if not(len(payload)):
                return
            
            cv_image = payload["cv_image"]
            img_key = payload["img_key"]
            set_name = payload["set_name"]
            dt = datetime.now(tz=timezone.utc)
            
            save_image(
                cv_image=cv_image,
                image_id=img_key,
                image_name=f"{payload['filename']}",
                image_format=os.path.basename(payload['filename']).split('.')[-1],
                timestamp=dt,
                expires_at=(dt + timedelta(minutes=15)),
                source=set_name,
            )
            
            signal = {key: value for key, value in payload.items() if key!='cv_image'}
            
            data = json.dumps(signal)
            response = stub.ProcessData(data_acquisition_pb2.ProcessDataRequest(data=data))
            response_data = json.loads(response.result)        
            exectution_time = time.time() - start_time

            print(f"Execution Time: {int(exectution_time * 1000)} milliseconds!")
            print("Data Acquisition Computing Service responded with updated data:", response_data)
            
    except Exception as err:
        logging.error(f"Error while reading and processing data in data acquisition: {err}")