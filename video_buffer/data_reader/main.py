import logging
from data_reader.interface.grpc import client
# from data_reader.endpoints.ros2 import core as ros2_core
from data_reader.endpoints.ros import core as ros_core

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

mapping = {
    'ros': ros_core.main,
}

params = {
    "mode": "ros",
    "topics": '/sensor_raw/rgbmatrix_01/image_raw/compressed',
    "msg_type": "compressed_image",
}

def main(mode="ros"):
    assert mode in mapping.keys(), f"mode is not supported: {mode}"
    print(f"Readind Data from {mode} ...")
    
    module = mapping.get(mode)
    if module:
        module(
            params=params,
            callback=client.run
            )
    

if __name__ == "__main__":
    main(mode=params['mode'])