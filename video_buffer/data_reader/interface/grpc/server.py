# implementation of the gRPC server

import os
import sys
import grpc
import json
import time
from concurrent import futures

from data_reader.interface.grpc import data_acquisition_pb2
from data_reader.interface.grpc import data_acquisition_pb2_grpc

class ServiceImpl(data_acquisition_pb2_grpc.ComputingUnitServicer):
    def ProcessData(self, request, context):
        print(f"Receiving Request: {request.data}")
        data = json.loads(request.data)
        
        result = json.dumps(data)
        return data_acquisition_pb2.ProcessDataResponse(result=result)
    
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    data_acquisition_pb2_grpc.add_ComputingUnitServicer_to_server(ServiceImpl(), server)
    server.add_insecure_port(f'[::]:{os.environ.get("GRPC_DATA_READER")}')
    server.start()
    server.wait_for_termination()
    
    
if __name__=="__main__":
    serve()
