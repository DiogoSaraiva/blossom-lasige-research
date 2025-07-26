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

from mimetic.src.logging_utils import Logger
from mimetic.src.pose_utils import PoseUtils
from mimetic.src.stream_buffer import ResultBuffer


class MediaPipeThread(threading.Thread):
    """
    A thread for processing video frames using MediaPipe for face and pose landmark detection.
    This thread uses MediaPipe's FaceLandmarker and PoseLandmarker to detect facial and body landmarks
    in real-time from video frames. It runs asynchronously and processes frames from a queue.
    """
    def __init__(self, result_buffer: ResultBuffer, model_dir: str=None, max_queue=8, logger: Logger=None):
        """
        Initializes the MediaPipeThread with the given parameters.
        :param result_buffer: A ResultBuffer instance to store the results.
        :type result_buffer: ResultBuffer
        :param model_dir: Directory containing the MediaPipe model files (optional).
        :type model_dir: str
        :param max_queue: Maximum size of the frame queue (default is 8).
        :type max_queue: int
        :param logger: Logger instance for logging messages.
        :type logger: Logger
        """
        super().__init__()
        self.logger = logger
        self.queue = Queue(maxsize=max_queue)
        self.result_buffer = result_buffer
        self.running = True
        self.latest_face = None
        self.latest_pose = None
        self.last_timestamp = 0

        if model_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_dir = os.path.join(current_dir, "..", "..", "models")
        model_dir = os.path.abspath(model_dir)

        face_model = os.path.join(model_dir, "face_landmarker.task")
        pose_model = os.path.join(model_dir, "pose_landmarker_full.task")

        if not os.path.exists(face_model):
            raise FileNotFoundError(f"FaceLandmarker not found: {face_model}")
        if not os.path.exists(pose_model):
            raise FileNotFoundError(f"PoseLandmarker not found: {pose_model}")
        try:
            face_options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=face_model, delegate=BaseOptions.Delegate.GPU),
                running_mode=vision.RunningMode.LIVE_STREAM,
                result_callback=self.face_callback
            )
            self.face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

            pose_options = PoseLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=pose_model, delegate=BaseOptions.Delegate.GPU),
                running_mode=vision.RunningMode.LIVE_STREAM,
                result_callback=self.pose_callback
            )
            self.pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)
        except Exception as e:
            self.logger(f"[MediaPipe] Error initializing MediaPipe models: {e}", level="critical")
            raise RuntimeError("Failed to initialize MediaPipe models") from e

    def run(self):
        self.logger("[MediaPipe] Thread started", level="info")
        if not self.face_landmarker or not self.pose_landmarker:
            self.logger("[MediaPipe] Models not initialized properly, stopping thread", level="error")
            self.running = False
            return
        try:
            while self.running:
                try:
                    item = self.queue.get(timeout=0.1)
                    if item is None or not isinstance(item, tuple) or len(item) != 2:
                        continue
                    frame, timestamp = item
                    if not isinstance(frame, (np.ndarray,)):
                        self.logger("[MediaPipe] Invalid frame")
                        continue
                    try:
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
                        self.face_landmarker.detect_async(mp_image, timestamp)
                        self.pose_landmarker.detect_async(mp_image, timestamp)
                    except Exception as e:
                        self.logger(f"[MediaPipe] Error during detect_async: {e}", level="error")
                        self.logger("[MediaPipe] Frame processing failed, skipping frame", level="debug")
                        import traceback
                        traceback.print_exc()
                except Empty:
                    continue
        except Exception as e:
            self.logger(f"[MediaPipe] CRASHED: {e}", level="critical")
            import traceback
            traceback.print_exc()
        self.logger("[MediaPipe] Thread stopped", level="info")

    def send(self, frame: np.ndarray):
        """
        Sends a frame to the MediaPipe queue for processing.
        This method checks if the queue is full before adding the frame.
        If the queue is full, it logs a debug message.
        :param frame: The video frame to be processed.
        :type frame: numpy.ndarray
        """
        try:
            if self.queue.full():
                self.logger("[MEDIAPIPE] MediaPipe queue full", level="debug")
            else:
                timestamp = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
                if timestamp <= self.last_timestamp:
                    timestamp = self.last_timestamp + 1
                self.last_timestamp = timestamp
                self.queue.put_nowait((frame, timestamp))
        except RuntimeError as e:
            self.logger(f"[MediaPipe] RuntimeError: {e}", level="error")
            raise RuntimeError("Failed to send frame to MediaPipe queue") from e
        except ValueError as ve:
            self.logger(f"[MediaPipe] ValueError: {ve}", level="error")
            raise ValueError("Invalid frame data") from ve
        except Exception as e:
            self.logger(f"[MediaPipe] Error sending frame: {e}", level="error")
            import traceback
            traceback.print_exc()
            raise RuntimeError("Failed to send frame to MediaPipe queue") from e

    def face_callback(self, result: FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        """
        Callback function for face landmark detection.
        This function is called by MediaPipe when face landmarks are detected.
        It updates the latest face landmarks and calls try_process to process the data.
        :param result: The result of the face landmark detection.
        :type result: FaceLandmarkerResult
        :param output_image: The output image with detected landmarks (not used here).
        :type output_image: mp.Image
        :param timestamp_ms: The timestamp of the frame in milliseconds.
        :type timestamp_ms: int
        """
        if not result.face_landmarks:
            self.logger("[MediaPipe] No face landmarks detected", level="debug")
            return
        if not isinstance(result, FaceLandmarkerResult):
            self.logger("[MediaPipe] Invalid result type for face landmarks", level="error")
            return
        if not result.face_landmarks[0]:
            self.logger("[MediaPipe] No valid face landmarks in result", level="debug")
            return
        try:
            self.latest_face = result
            self.try_process(timestamp_ms)
        except ValueError as ve:
            self.logger(f"[MediaPipe] ValueError: {ve}", level="error")
        except RuntimeError as re:
            self.logger(f"[MediaPipe] RuntimeError: {re}", level="error")
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing face data: {e}", level="error")
            import traceback
            traceback.print_exc()

    def pose_callback(self, result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        """
        Callback function for pose landmark detection.
        This function is called by MediaPipe when pose landmarks are detected.
        It updates the latest pose landmarks and calls try_process to process the data.
        :param result: The result of the pose landmark detection.
        :type result: PoseLandmarkerResult
        :param output_image: The output image with detected landmarks (not used here).
        :type output_image: mp.Image
        :param timestamp_ms: The timestamp of the frame in milliseconds.
        :type timestamp_ms: int
        """
        if not result.pose_landmarks:
            self.logger("[MediaPipe] No pose landmarks detected", level="debug")
            return
        if not isinstance(result, PoseLandmarkerResult):
            self.logger("[MediaPipe] Invalid result type for pose landmarks", level="error")
            return
        if not result.pose_landmarks[0]:
            self.logger("[MediaPipe] No valid pose landmarks in result", level="debug")
            return
        self.latest_pose = result
        try:
            self.try_process(timestamp_ms)
        except ValueError as ve:
            self.logger(f"[MediaPipe] ValueError: {ve}", level="error")
        except RuntimeError as re:
            self.logger(f"[MediaPipe] RuntimeError: {re}", level="error")
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing pose data: {e}", level="error")
            import traceback
            traceback.print_exc()
    def try_process(self, timestamp_ms: int):
        """
        Processes the latest face and pose landmarks if available.
        This function calculates the pose data (pitch, roll, yaw, height) and adds it
        to the result buffer. It is called whenever new face or pose landmarks are detected.
        :param timestamp_ms: The timestamp of the frame in milliseconds.
        :type timestamp_ms: int
        """
        if self.latest_face is None or self.latest_pose is None:
            return
        if not self.latest_face.face_landmarks or not self.latest_pose.pose_landmarks:
            self.logger("[MediaPipe] No face or pose landmarks detected", level="debug")
            return
        try:
            face_landmarks = self.latest_face.face_landmarks[0]
            pose_landmarks = self.latest_pose.pose_landmarks[0]

            # Calcula dados da pose
            pose_utils = PoseUtils(face_landmarks, pose_landmarks)
            pitch = pose_utils.calculate_pitch()
            roll = pose_utils.calculate_roll()
            yaw = pose_utils.calculate_yaw()
            height = pose_utils.estimate_height()

            pose_data = {
                "pitch": pitch,
                "roll": roll,
                "yaw": yaw,
                "height": height,
                "timestamp_ms": timestamp_ms
            }

            self.result_buffer.add("pose_data", pose_data, timestamp_ms)

            self.latest_face = None
            self.latest_pose = None
        except ValueError as ve:
            self.logger(f"[MediaPipe] ValueError: {ve}", level="error")
        except RuntimeError as re:
            self.logger(f"[MediaPipe] RuntimeError: {re}", level="error")
        except Exception as e:
            self.logger(f"[MediaPipe] Error processing pose data: {e}", level="error")
            import traceback
            traceback.print_exc()


    def stop(self):
        """
        Stops the MediaPipe thread and releases resources.
        This method sets the running flag to False, closes the face and pose landmarker instances,
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
        self.queue.put(None)  # Ensure the thread can exit if it's waiting on the queue
        self.logger("[MediaPipe] Thread stopped", level="info")
