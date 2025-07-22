from argparse import ArgumentParser
import cv2
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python import vision
import requests
import time
from mediapipe.tasks.python.vision import (
    FaceLandmarkerResult, FaceLandmarkerOptions,
    PoseLandmarkerResult, PoseLandmarkerOptions
)
from mimetic.src.stream_buffer import ResultBuffer
from mimetic.src.visual_utils import Visualization
from src.pose_utils import PoseUtils
from src.motion_limiter import MotionLimiter
from src.config import MIRROR_VIDEO, VIDEO_WIDTH, VIDEO_HEIGHT
from src.recording_tools import RecordingTools

parser = ArgumentParser(description="Mimetic Blossom Controller")
parser.add_argument("--host", default="localhost", help="IP address of the Blossom server (default: localhost)")
parser.add_argument("--port", type=int, default=8000, help="Port of the Blossom server (default: 8000)")
parser.add_argument("--record", type=RecordingTools.str2bool, default=False, help="Enable video recording (true/false)",
)
CAM_VIEW_TITLE = "Pose Estimation " + " (Mirrored)" if MIRROR_VIDEO else ""
args = parser.parse_args()

limiter = MotionLimiter()
visualization = Visualization()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, VIDEO_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, VIDEO_HEIGHT)

buffer = ResultBuffer()
recorder = RecordingTools()
if args.record:
    recorder.start_recording()

def face_callback(result: FaceLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    buffer.add("face", result, timestamp_ms)

def pose_callback(result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    buffer.add("pose", result, timestamp_ms)

face_options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="models/face_landmarker.task", delegate=BaseOptions.Delegate.GPU),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=face_callback
)
face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

pose_options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path="models/pose_landmarker_full.task", delegate=BaseOptions.Delegate.GPU),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=pose_callback
)
pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)

prev_time = time.time()
frame_count = 0
try:
    while cap.isOpened():
        frame_count += 1
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1) if MIRROR_VIDEO else frame

        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

        timestamp = int(time.time() * 1000)
        face_landmarker.detect_async(mp_image, timestamp)
        pose_landmarker.detect_async(mp_image, timestamp)

        face_results, pose_results = buffer.get_latest_complete()

        current_time = time.time()
        fps = 1.0 / (current_time - prev_time)
        prev_time = current_time
        print(f"FPS: {fps:.2f}")

        if  pose_results and face_results and pose_results.pose_landmarks and face_results.face_landmarks:
            face_landmarks   = face_results.face_landmarks[0]
            pose_landmarks = pose_results.pose_landmarks[0]

            pose_utils = PoseUtils(face_landmarks, pose_landmarks, frame)

            roll = pose_utils.calculate_roll()
            pitch = pose_utils.calculate_pitch()
            yaw = pose_utils.calculate_yaw()
            height = pose_utils.estimate_height()

            x = limiter.smooth('x', pitch)
            y = limiter.smooth('y', roll)
            z = limiter.smooth('z', yaw)
            h = limiter.smooth('h', height)
            e = limiter.smooth('e', height)

            axis = { 'pitch': pitch, 'roll': roll, 'yaw': yaw }
            should_send, duration = limiter.should_send(["x", "y", "z", "h"])

            payload = {
                "x": x,
                "y": y,
                "z": z,
                "h": h,
                "ears": e,
                "ax": 0,
                "ay": 0,
                "az": -1,
                "mirror": True,
                "duration_ms": int(duration * 1000) if duration else 500
            }

            sent_data = payload if should_send else {"x": 0, "y": 0, "z": 0, "h": 0}
            data = {
                "axis": axis,
                "blossom_data": {
                    "calc_data": {"x": x, "y": y, "z": z, "h": h},
                    "sent_data": sent_data
                },
                "height": height,
                "fps": fps
            }
            visualization.update(frame, face_results, pose_results, data)
            visualization.render()

            if args.record:
                recorder.write_frame(frame)

            if should_send:
                try:
                    requests.post(f"http://{args.host}:{args.port}/position", json=payload)
                    print(
                        f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
                except Exception as e:
                    print("Error sending to Blossom:", e)

        cv2.imshow(CAM_VIEW_TITLE, frame)
        if cv2.waitKey(5) & 0xFF == 27:
            break
        try:
            if cv2.getWindowProperty(CAM_VIEW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
                break
        except cv2.error:
            break

except Exception as e:
    print(f"[ERROR] Crash: {e}")
finally:
    #Cleanup
    print("[INFO] Cleaning up...")
    recorder.stop_recording()
    cap.release()
    pose_landmarker.close()
    face_landmarker.close()
    cv2.destroyAllWindows()
    print("[INFO] Shutdown complete.")