#!/usr/bin/env python3

"""
 * Copyright (C) WasteAnt - All Rights Reserved
 * Unauthorized copying of this file, via any medium is strictly prohibited.
 * Proprietary and confidential
 * See accompanying/further LICENSES below or attached
 * Created by Tannous Geagea <tannous.geagea@wasteant.com>, December 2024
 * Edited by:
 *
"""

import cv2
import json
import time
import rospy
import logging
import message_filters
from datetime import datetime, timezone
from std_msgs.msg import Header
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image, CompressedImage
from typing import Optional, Union, List, AnyStr
from common_utils.time.time_tracker import KeepTrackOfTime

def default_process_messages(messages):
    print(f'DEFAULT CALLBACK: {messages.keys()}')
  
keep_track_of_time = KeepTrackOfTime()  

class ROSManager:
    def __init__(
        self, topics:Optional[Union[List, AnyStr]], msg_type:Optional[Union[List, AnyStr]], callback=None,
        node_name="video_buffer_data_acquisition",
    ):  
        self.bridge = CvBridge()
        
        if isinstance(topics, str):
            topics = [topics]
            
        if isinstance(msg_type, str):
            msg_type = [msg_type]
            
        assert len(topics) == len(msg_type), f"length of given topics {len(topics)} must be equal length of msg type {len(msg_type)}"        
        
        self.init_node(node_name)
        for i, topic in enumerate(topics):
            self.create_subscription(
                self.message_type(msg_type=msg_type[i]),
                topic, 
                self.callback_factory(topic, callback), 
                10
                )

    def create_subscription(self, msg_type, topic, callback, queue_size=10):
        try:
            rospy.Subscriber(topic, msg_type, callback, queue_size=queue_size)
            rospy.spin()
        except Exception as err:
            logging.error(
                "Unexpected Error while listening to topic %s: %s"
                % (topic, err)
            )

    def init_node(self, node_name):
        """initialize ros node"""
        try:
            logging.info("Init %s" % node_name)
            rospy.init_node(node_name, anonymous=True)
        except Exception as err:
            logging.error("Unexpected Error where initializing ros node: %s" % err)
            
    def callback_factory(self, topic, callback=None):
        """
        Default Callback to image subscription
        """
        def callback_(msg):
            
            if keep_track_of_time.check_if_time_less_than_diff(
                start=keep_track_of_time.what_is_the_time,
                end=time.time(),
                diff=1,
            ):
                return
            
            logging.info(f"Received message from {topic}")
            cv_image = self.msg_to_cv2(msg)
            h0, w0, _ = cv_image.shape
            cv_image = cv2.resize(cv_image, (int(w0 * 0.25), int(h0 * 0.25)), interpolation=cv2.INTER_NEAREST)
            
            dt = datetime.now(tz=timezone.utc)
            payload = {
                "cv_image": cv_image,
                "img_key": str(time.time()),
                "timestamp": str(msg.header.stamp),
                "set_name": str(topic),
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                "filename": dt.strftime("%Y-%m-%d_%H-%M-%S") + '.jpg',
            }

            if callback:
                callback(payload)
            
            keep_track_of_time.update_time()
                
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
        
        
        