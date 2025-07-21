import cv2
import mediapipe as mp
import requests
import time
from mimetic.src.visual_utils import Visualization
from src.pose_utils import PoseUtils
from src.motion_limiter import MotionLimiter
import argparse
from src.config import MIRROR_VIDEO

CAM_VIEW_TITLE = "Pose Estimation " +  " (Mirrored)" if MIRROR_VIDEO else ""


def parse_args():
    parser = argparse.ArgumentParser(description="Mimetic Blossom Controller")
    parser.add_argument("--host", default="localhost", help="IP address of the Blossom server (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port of the Blossom server (default: 8000)")
    return parser.parse_args()

args = parse_args()

limiter = MotionLimiter()


mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=0,
    enable_segmentation=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = time.time()

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1) if MIRROR_VIDEO else frame
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mesh_results = face_mesh.process(image_rgb)
    pose_results = pose.process(image_rgb)

    face_detected = mesh_results.multi_face_landmarks # type: ignore
    body_detected = pose_results.pose_landmarks # type: ignore

    if face_detected and body_detected:
        face_landmarks = face_detected[0]
        pose_landmarks = pose_results.pose_landmarks.landmark # type: ignore
        pose_utils = PoseUtils(face_landmarks.landmark, pose_landmarks, frame)

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

        data = {
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

        current_time = time.time()
        fps = 1.0 / (current_time - prev_time)
        prev_time = current_time


        sent_data = data if should_send else {"x": 0, "y": 0, "z": 0, "h": 0}
        info = {
            "axis": axis,
            "blossom_data": {
                "calc_data":
                    {"x": x, "y": y, "z": z, "h": h},
                "sent_data": sent_data
            },
            "height": height,
            "fps": fps}
        visualization = Visualization(frame, mesh_results, pose_results, info)

        visualization.draw_overlay_data()
        visualization.draw_sent_data()
        visualization.draw_landmarks()
        visualization.draw_shoulder_line()

        if should_send:
            data["duration"] = int(duration * 1000)
            try:
                requests.post(f"http://{args.host}:{args.port}/position", json=data)
                print(f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
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

cap.release()
face_mesh.close()
pose.close()
cv2.destroyAllWindows()
