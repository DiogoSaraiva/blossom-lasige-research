import threading
import time, os
from queue import Queue, Empty

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
from mediapipe.tasks.python.vision import (
    FaceLandmarkerOptions, PoseLandmarkerOptions,
    FaceLandmarkerResult, PoseLandmarkerResult
)

from mimetic.src.pose_utils import PoseUtils


class MediaPipeThread(threading.Thread):
    def __init__(self, result_buffer, model_dir=None, max_queue=8):
        super().__init__()
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

    def run(self):
        print("[MediaPipe] Thread started")
        try:
            while self.running:
                try:
                    frame, timestamp = self.queue.get(timeout=0.1)
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
                    self.face_landmarker.detect_async(mp_image, timestamp)
                    self.pose_landmarker.detect_async(mp_image, timestamp)
                except Empty:
                    continue
        except Exception as e:
            print(f"[MediaPipe] CRASHED: {e}")
            import traceback
            traceback.print_exc()
        print("[MediaPipe] Thread stopped")

    def send(self, frame):
        if self.queue.full():
            print("[DEBUG] MediaPipe queue full")
        if not self.queue.full():
            timestamp = int(cv2.getTickCount() / cv2.getTickFrequency() * 1000)
            if timestamp <= self.last_timestamp:
                timestamp = self.last_timestamp + 1
            self.last_timestamp = timestamp

            self.queue.put_nowait((frame, timestamp))


    def face_callback(self, result: FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        self.latest_face = result
        self.try_process(timestamp_ms)

    def pose_callback(self, result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        self.latest_pose = result
        self.try_process(timestamp_ms)

    def try_process(self, timestamp_ms: int):
        if self.latest_face is None or self.latest_pose is None:
            return
        if not self.latest_face.face_landmarks or not self.latest_pose.pose_landmarks:
            return

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

    def stop(self):
        self.running = False
        self.face_landmarker.close()
        self.pose_landmarker.close()
