import cv2
import time
import rclpy
import logging
import numpy as np
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge, CvBridgeError
from datetime import datetime, timezone
from typing import Optional, Union, List, Dict
from collections import defaultdict
import threading
from common_utils.time.time_tracker import KeepTrackOfTime

keep_track_of_time = KeepTrackOfTime() 
class ROS2Manager(Node):
    def __init__(
        self, 
        sources: List[Dict[str, str]],
        callback=None, 
        node_name="video_buffer_data_acquisition",
        max_retries=3,
        timeout_seconds=30
    ):
        super().__init__(node_name)
        self.bridge = CvBridge()
        self.callback = callback

        self.faulty_sources = defaultdict(int) 
        self.last_message_time = {} 
        self.lock = threading.Lock() 
        self.timeout_seconds = timeout_seconds

        topics = [source["source_name"] for source in sources if source["source_name"]]
        msg_types = [source["message_type"] for source in sources if source["message_type"]]
        camera = [source["camera"] for source in sources if source["camera"]]

        if not topics:
            logging.warning("⚠️ No valid sources provided. ROS2Manager will not subscribe to any topics.")
            return

        assert len(topics) == len(msg_types), f"Length of topics ({len(topics)}) must equal length of message types ({len(msg_types)})"        
        
        for i, topic in enumerate(topics):
            msg_type = self.message_type(msg_types[i])

            if msg_type:
                logging.info(f"📡 Subscribing to {topic} with type {msg_types[i]}")
                self.create_subscription(
                    msg_type,
                    topic, 
                    self.callback_factory(topic, msg_types[i], camera[i]), 
                    10
                )
                self.last_message_time[topic] = time.time()
            else:
                logging.warning(f"⚠️ Skipping {topic} due to unsupported message type: {msg_types[i]}")
        
        # Start thread to monitor inactive sources
        self.monitor_thread = threading.Thread(target=self.monitor_inactive_sources, daemon=True)
        self.monitor_thread.start()
    
    def callback_factory(self, topic, msg_type, camera_info):
        """
        Generates a callback function for each topic.
        Handles faulty sources and retries.
        """
        def callback_(msg):
            logging.info(f"✅ Received message from {topic}")
            self.last_message_time[topic] = time.time()  # Update last received time

            if keep_track_of_time.check_if_time_less_than_diff(
                start=keep_track_of_time.what_is_the_time,
                end=time.time(),
                diff=1,
            ):
                return

            try:
                cv_image = self.msg_to_cv2(msg)
                h0, w0, _ = cv_image.shape

                cv_image = cv2.resize(cv_image, (int(w0 / 4), int(h0 / 4)))
                dt = datetime.now(tz=timezone.utc)

                payload = {
                    "cv_image": cv_image,
                    "img_key": str(time.time()),
                    "timestamp": str(msg.header.stamp.sec + msg.header.stamp.nanosec * 10e-9),
                    "set_name": str(topic),
                    "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "filename": dt.strftime("%Y-%m-%d_%H-%M-%S") + '.jpg',
                    "camera": camera_info,
                }

                if self.callback:
                    self.callback(payload)

                keep_track_of_time.update_time()
                
                # Reset faulty source counter on success
                with self.lock:
                    self.faulty_sources[topic] = 0 

            except Exception as err:
                with self.lock:
                    self.faulty_sources[topic] += 1

                retry_count = self.faulty_sources[topic]
                if retry_count <= 3:
                    logging.error(f"❌ Error processing message from {topic}. Retry {retry_count}/3: {err}")
                else:
                    logging.error(f"⛔ Too many failures for {topic}. Disabling further processing.")
        
        return callback_

    def message_type(self, msg_type):
        """
        Returns the correct ROS2 message type.
        """
        try:
            if msg_type == "sensor_msgs/msg/Image":
                return Image
            elif msg_type == "sensor_msgs/msg/CompressedImage":
                return CompressedImage
            else:
                logging.error(f"❌ Unsupported message type: {msg_type}")
                return None
        except Exception as err:
            logging.error(f"❌ Error mapping message type: {err}")
            return None

    def msg_to_cv2(self, msg):
        """
        Converts a ROS2 message to an OpenCV image.
        """
        try:
            if isinstance(msg, Image):
                return self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            elif isinstance(msg, CompressedImage):
                return self.bridge.compressed_imgmsg_to_cv2(msg)
            else:
                raise ValueError(f"❌ Unsupported message format: {type(msg)}")
        except CvBridgeError as err:
            raise CvBridgeError(f"❌ CvBridge error converting image: {err}")
        except Exception as err:
            raise ValueError(f"❌ Unknown error converting image: {err}")

    def monitor_inactive_sources(self):
        """
        Periodically checks if any source has been inactive beyond `timeout_seconds`.
        If a source hasn't sent data, it's considered inactive.
        """
        while rclpy.ok():
            with self.lock:
                current_time = time.time()
                for topic, last_time in self.last_message_time.items():
                    if (current_time - last_time) > self.timeout_seconds:
                        logging.warning(f"⚠️ No messages received from {topic} in the last {self.timeout_seconds} seconds. Marking as inactive.")
                        self.last_message_time[topic] = current_time  # Reset to avoid duplicate warnings
            
            time.sleep(10)  # Check every 10 seconds
