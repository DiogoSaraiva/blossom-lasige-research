import os
import threading
from queue import Queue, Empty

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision
from mediapipe.tasks.python.vision import (
    FaceLandmarkerOptions, PoseLandmarkerOptions,
    FaceLandmarkerResult, PoseLandmarkerResult
)

from src.logging_utils import Logger
from mimetic.src.pose_utils import PoseUtils
from mimetic.src.pose_buffer import PoseBuffer


class MediaPipeThread(threading.Thread):
    """
    Thread for processing video frames using MediaPipe for face and pose landmark detection.

    This thread uses MediaPipe's FaceLandmarker and PoseLandmarker to detect facial and body landmarks
    in real-time from video frames. It runs asynchronously and processes frames from a queue.

    Args:
        result_buffer (PoseBuffer): Buffer to store processed pose data.
        model_dir (str, optional): Directory containing MediaPipe model files.
        max_queue (int, optional): Maximum number of frames in the processing queue.
        logger (Logger, optional): Logger instance for logging messages.
    """
    def __init__(self, result_buffer: PoseBuffer, logger: Logger, model_dir: str = None, max_queue=8):
        """
        Initialize the MediaPipeThread.

        Args:
            result_buffer (PoseBuffer): Buffer to store processed pose data.
            model_dir (str, optional): Directory containing MediaPipe model files.
            max_queue (int, optional): Maximum number of frames in the processing queue.
            logger (Logger): Logger instance for logging messages.
        """
        super().__init__()
        self.logger = logger
        self.queue = Queue(maxsize=max_queue)
        self.result_buffer = result_buffer
        self.running = True
        self.latest_face = None
        self.latest_pose = None
        self.last_timestamp = 0
        self.face_valid_until = 0
        self.pose_valid_until = 0
        self.landmark_timeout_ms = 500

        if model_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(current_dir, "..", "..", "models")
        model_dir = os.path.abspath(model_dir)

        face_model = os.path.join(model_dir, "face_landmarker.task")
        pose_model = os.path.join(model_dir, "pose_landmarker_full.task")

        if not os.path.exists(face_model) or not os.path.exists(pose_model):
            raise FileNotFoundError(f"MediaPipe models not found in {model_dir}")

        try:
            self._init_landmarkers(face_model, pose_model)
        except Exception as e:
            self.logger(f"[MediaPipe] Error initializing MediaPipe models: {e}", level="critical")
            raise RuntimeError("Failed to initialize MediaPipe models") from e

    def _init_landmarkers(self, face_model, pose_model):
        base_delegate = BaseOptions.Delegate.GPU
        face_options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=face_model, delegate=base_delegate),
            running_mode=vision.RunningMode.LIVE_STREAM,
            result_callback=self.face_callback
        )
        self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)
        pose_options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=pose_model, delegate=base_delegate),
            running_mode=vision.RunningMode.LIVE_STREAM,
            result_callback=self.pose_callback
        )
        self.pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)

    def run(self):
        """
        Main thread loop for processing frames from the queue using MediaPipe.

        Continuously retrieves frames from the queue, processes them with MediaPipe,
        and handles exceptions and logging.
        """
        self.logger("[MediaPipe] Thread started", level="info")
        if not self.face_landmarker or not self.pose_landmarker:
            self.logger("[MediaPipe] Models not initialized properly, stopping thread", level="error")
            self.running = False
            return
        try:
            while self.running:
                try:
                    item = self.queue.get(timeout=0.1)
                    if not self._valid_queue_item(item):
                        continue
                    frame, timestamp = item
                    self._process_frame(frame, timestamp)
                except Empty:
                    continue
                except Exception as e:
                    self.logger(f"[MediaPipe] Frame processing error: {e}", level="debug")
        except Exception as e:
            import traceback
            self.logger(f"[MediaPipe] CRASHED: {e} \n {traceback.format_exc()}", level="critical")

    def _valid_queue_item(self, item):
        return item is not None and isinstance(item, tuple) and len(item) == 2

    def _process_frame(self, frame, timestamp):
        if not isinstance(frame, np.ndarray):
            self.logger("[MediaPipe] Invalid frame", level="Warning")
            return
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        self.face_landmarker.detect_async(mp_image, timestamp)
        self.pose_landmarker.detect_async(mp_image, timestamp)

    def send(self, frame: np.ndarray):
        """
        Send a frame to the MediaPipe queue for processing.

        Checks if the queue is full before adding the frame. If the queue is full, logs a debug message.

        Args:
            frame (numpy.ndarray): The video frame to be processed.
        """
        try:
            if self.queue.full():
                self.logger("[MEDIAPIPE] MediaPipe queue full", level="debug")
                return
            timestamp = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
            if timestamp <= self.last_timestamp:
                timestamp = self.last_timestamp + 1
            self.last_timestamp = timestamp
            self.queue.put_nowait((frame, timestamp))
        except Exception as e:
            self.logger(f"[MediaPipe] Error sending frame: {e}", level="error")
            import traceback
            traceback.print_exc()

    def face_callback(self, result: FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        """
        Callback function for face landmark detection.

        Called by MediaPipe when face landmarks are detected. Updates the latest face landmarks
        and calls try_process to process the data.

        Args:
            result (FaceLandmarkerResult): The result of the face landmark detection.
            output_image (mp.Image): The output image with detected landmarks (not used).
            timestamp_ms (int): The timestamp of the frame in milliseconds.
        """
        if not result.face_landmarks or not result.face_landmarks[0]:
            self.logger("[MediaPipe] No face landmarks detected", level="debug")
            return
        try:
            self.latest_face = result
            self.face_valid_until = timestamp_ms + self.landmark_timeout_ms
            self.try_process(timestamp_ms)
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing face data: {e}", level="error")
            import traceback
            traceback.print_exc()

    def pose_callback(self, result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        """
        Callback function for pose landmark detection.

        Called by MediaPipe when pose landmarks are detected. Updates the latest pose landmarks
        and calls try_process to process the data.

        Args:
            result (PoseLandmarkerResult): The result of the pose landmark detection.
            output_image (mp.Image): The output image with detected landmarks (not used).
            timestamp_ms (int): The timestamp of the frame in milliseconds.
        """
        if not result.pose_landmarks or not result.pose_landmarks[0]:
            self.logger("[MediaPipe] No pose landmarks detected", level="debug")
            return
        try:
            self.latest_pose = result
            self.pose_valid_until = timestamp_ms + self.landmark_timeout_ms
            self.try_process(timestamp_ms)
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing pose data: {e}", level="error")
            import traceback
            traceback.print_exc()

    def try_process(self, timestamp_ms: int):
        """
        Processes the latest face and pose landmarks if available.

        Calculates the pose data (pitch, roll, yaw, height) and adds it to the result buffer.
        Called whenever new face or pose landmarks are detected.

        Args:
            timestamp_ms (int): The timestamp of the frame in milliseconds.
        """
        face_valid = self.latest_face is not None and timestamp_ms <= self.face_valid_until
        pose_valid = self.latest_pose is not None and timestamp_ms <= self.pose_valid_until
        if not face_valid or not pose_valid:
            return
        try:
            face_landmarks = self.latest_face.face_landmarks[0]
            pose_landmarks = self.latest_pose.pose_landmarks[0]
            pose_utils = PoseUtils(
                logger=self.logger,
                facemesh_landmarks=face_landmarks,
                pose_landmarks=pose_landmarks
            )

            pitch, roll, yaw = pose_utils.get_head_orientation()
            # pitch = pose_utils.calculate_pitch()
            # roll = pose_utils.calculate_roll()
            # yaw = pose_utils.calculate_yaw()
            pose_data = {
                "pitch": pitch,
                "roll": roll,
                "yaw": yaw,
                "height": pose_utils.estimate_height(),
                "timestamp_ms": timestamp_ms
            }
            self.result_buffer.add("pose_data", pose_data, timestamp_ms)
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing pose data: {e}", level="error")
            import traceback
            traceback.print_exc()

    def stop(self):
        """
        Stops the MediaPipe thread and releases resources.

        Sets the running flag to False, closes the face and pose landmarker instances,
        and allows the thread to exit gracefully.
        """
        self.logger("[MediaPipe] Stopping thread", level="info")
        if not self.running:
            self.logger("[MediaPipe] Thread already stopped", level="warning")
            return
        self.running = False
        try:
            self.face_landmarker.close()
            self.pose_landmarker.close()
        except Exception as e:
            self.logger(f"[MediaPipe] Error closing MediaPipe models: {e}", level="error")
        self.queue.put(None)
        with self.queue.mutex:
            self.queue.queue.clear()
        self.logger("[MediaPipe] Thread stopped", level="info")