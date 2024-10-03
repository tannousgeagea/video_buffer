import os
import logging
import sys
from common_utils.services.ros_manager import ROSManager
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main(params:dict, callback=None):
    # define  a default callback
    def default_callback(*data):
        print(f'running default callback: {type(data)}')
        
    callback = callback if not callback is None else default_callback
            
    try:
        assert "topics" in params.keys(), f"key: topic not found in params"
        assert "msg_type" in params.keys(), f"key: msg_type not found in params"

        # Create a MultiCameraSubscriber node
        multi_camera_subscriber = ROSManager(
            params['topics'], 
            msg_type=params["msg_type"],
            callback=callback
            )
    
    except Exception as err:
        logging.error(f'Error in getting data from ROS: {err}')

if __name__ == '__main__':
    main()