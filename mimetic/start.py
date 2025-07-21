import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
import requests
import time
import argparse
from mimetic.src.visual_utils import Visualization
from src.pose_utils import PoseUtils
from src.motion_limiter import MotionLimiter
from src.config import MIRROR_VIDEO

CAM_VIEW_TITLE = "Pose Estimation " + " (Mirrored)" if MIRROR_VIDEO else ""

def parse_args():
    parser = argparse.ArgumentParser(description="Mimetic Blossom Controller")
    parser.add_argument("--host", default="localhost", help="IP address of the Blossom server (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port of the Blossom server (default: 8000)")
    return parser.parse_args()

args = parse_args()

limiter = MotionLimiter()
visualization = Visualization()


pose_options = vision.PoseLandmarkerOptions(
    base_options=mp_tasks.BaseOptions(model_asset_path="models/pose_landmarker_full.task", delegate=mp_tasks.BaseOptions.Delegate.GPU),
    running_mode=vision.RunningMode.VIDEO,
    output_segmentation_masks=False,
    num_poses=1,
)
pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)

face_options = vision.FaceLandmarkerOptions(
    base_options=mp_tasks.BaseOptions(model_asset_path="models/face_landmarker.task", delegate=mp_tasks.BaseOptions.Delegate.GPU),
    running_mode=vision.RunningMode.VIDEO,
    output_face_blendshapes=False,
    num_faces=1,

)
face_landmarker = vision.FaceLandmarker.create_from_options(face_options)


cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
time.sleep(1.0)

prev_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1) if MIRROR_VIDEO else frame
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)

    timestamp = int(time.time() * 1000)
    face_results = face_landmarker.detect_for_video(mp_image, timestamp)
    pose_results = pose_landmarker.detect_for_video(mp_image, timestamp)

    current_time = time.time()
    fps = 1.0 / (current_time - prev_time)
    prev_time = current_time

    if pose_results.pose_landmarks and face_results.face_landmarks:
        face_landmarks = face_results.face_landmarks[0]
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

        if should_send:
            try:
                requests.post(f"http://{args.host}:{args.port}/position", json=payload)
                print(f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
            except Exception as e:
                print("Error sending to Blossom:", e)
    else:
        # Safe fallback data for visualization even if no landmarks
        fallback_data = {
            "axis": {"pitch": 0.0, "roll": 0.0, "yaw": 0.0},
            "blossom_data": {
                "calc_data": {"x": 0.0, "y": 0.0, "z": 0.0, "h": 0.0},
                "sent_data": {"x": 0.0, "y": 0.0, "z": 0.0, "h": 0.0}
            },
            "height": 0.0,
            "fps": fps
        }
        visualization.update(frame, face_results, pose_results, fallback_data)
        visualization.render()

    # Show result
    cv2.imshow(CAM_VIEW_TITLE, frame)
    if cv2.waitKey(5) & 0xFF == 27:
        break
    try:
        if cv2.getWindowProperty(CAM_VIEW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break
    except cv2.error:
        break

# Cleanup
cap.release()
pose_landmarker.close()
face_landmarker.close()
cv2.destroyAllWindows()
