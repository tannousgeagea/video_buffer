import cv2
import time
import rclpy
import logging
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Image
from sensor_msgs.msg import CompressedImage
from cv_bridge import CvBridge, CvBridgeError
from typing import Optional, Union, List, AnyStr

class ROS2Manager(Node):
    def __init__(self, topics:Optional[Union[List, AnyStr]], msg_type:Optional[Union[List, AnyStr]], callback=None, 
                 node_name="video_buffer_data_acquisition"):
        super().__init__(node_name)
        
        self.bridge = CvBridge()
        
        if isinstance(topics, str):
            topics = [topics]
            
        if isinstance(msg_type, str):
            msg_type = [msg_type]
            
        assert len(topics) == len(msg_type), f"length of given topics {len(topics)} must be equal length of msg type {len(msg_type)}"        
        
        for i, topic in enumerate(topics):
            self.create_subscription(
                self.message_type(msg_type=msg_type[i]),
                topic, 
                self.callback_factory(topic, callback), 
                10
                )
            
    def callback_factory(self, topic, callback=None):
        """
        Default Callback to image subscription
        """
        def callback_(msg):
            logging.info(f"Received message from {topic}")
            cv_image = self.msg_to_cv2(msg)
            
            payload = {
                "cv_image": cv_image,
                "img_key": str(time.time()),
                "timestamp": str(msg.header.stamp.sec + msg.header.stamp.nanosec * 10e-9),
                "set_name": str(topic),
            }

            if callback:
                callback(payload)
                
        return callback_
        
    def message_type(self, msg_type):
        try:
            if msg_type=="image":
                return Image
            elif msg_type=="compressed_image":
                return CompressedImage
            else:
                raise ValueError(f"msg type {msg_type} not supported")
        except Exception as err:
            raise ValueError(f"Failed to map message type ros sensor messgae: {err}")


    def msg_to_cv2(self, msg):
        try:
            if type(msg) == Image:
                return self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            elif type(msg) == CompressedImage:
                return self.bridge.compressed_imgmsg_to_cv2(msg)
            else:
                raise ValueError(f"Failed to decode image msg to cv2 image: {type(msg)} not supported")
        except Exception as err:
            raise ValueError(f"Failed to encode img msg to cv2: {err}")
        except CvBridgeError as err:
            raise CvBridgeError(f"Failed to encode img to cv2 {err}")