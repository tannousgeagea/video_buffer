import logging
from data_reader.interface.grpc import client
from data_reader.endpoints.ros2 import core as ros2_core
from configure.client import ConfigManager

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

mapping = {
    'ros2': ros2_core.main,
}

active_sources = ConfigManager.get_active_data_sources()

params = {
    "mode": "ros2",
    "sources": active_sources
}


print(params)
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