import cv2
import mediapipe as mp
import numpy as np
import requests

from src.pose_utils import PoseUtils
from src.motion_limiter import MotionLimiter

CAM_VIEW_TITLE = "Pose Estimation (Mirrored)"
limiter = MotionLimiter()

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=False,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_drawing = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

def draw_overlay_info(frame, pitch, roll, yaw, height):
    orientation_text = f"Pitch: {pitch:.1f}  Roll: {roll:.1f}  Yaw: {yaw:.1f}"
    height_text = f"Height: {height}"
    cv2.putText(frame, orientation_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(frame, height_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

def draw_sent_data(frame, data, sent, pos=(10, -30)):
    h, w = frame.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    color = (0, 255, 0)
    thickness = 1
    line_height = 20

    lines = [
        f"Calculated: P={data['x']:.3f}, R={data['y']:.3f}, Y={data['z']:.3f}, H={data['h']:.3f}",
        f"Sent:       P={sent['x']:.3f}, R={sent['y']:.3f}, Y={sent['z']:.3f}, H={sent['h']:.3f}"
    ]

    for i, text in enumerate(lines):
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        x = w - text_size[0] - 10
        y = h + (pos[1] if pos[1] < 0 else 0) - (len(lines) - i) * line_height
        cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)

    if results.multi_face_landmarks:  # type: ignore
        face_landmarks = results.multi_face_landmarks[0]  # type: ignore
        pose_utils = PoseUtils(face_landmarks.landmark, frame)

        roll = pose_utils.calculate_roll()
        pitch = pose_utils.calculate_pitch()
        yaw = pose_utils.calculate_yaw()
        height = pose_utils.estimate_height()

        x = limiter.smooth('x', pitch)
        y = limiter.smooth('y', roll)
        z = limiter.smooth('z', yaw)
        h = limiter.smooth('h', height)
        e = limiter.smooth('e', height)

        draw_overlay_info(frame, pitch, roll, yaw, height)

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
            "mirror": True
        }

        sent_data = data if should_send else {"x": 0, "y": 0, "z": 0, "h": 0}
        draw_sent_data(frame, data, sent_data)

        if should_send:
            try:
                requests.post("http://localhost:8000/position", json=data)
                print(f"Sent -> Pitch: {x:.3f}, Roll: {y:.3f}, Yaw: {z:.3f}, Height: {h:.3f}, Duration: {duration:.2f}s")
            except Exception as e:
                print("Error sending to Blossom:", e)

        mp_drawing.draw_landmarks(
            frame,
            face_landmarks,
            mp_face_mesh.FACEMESH_TESSELATION,
            landmark_drawing_spec=None,
            connection_drawing_spec=mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
        )

    cv2.imshow(CAM_VIEW_TITLE, frame)
    if cv2.waitKey(5) & 0xFF == 27:
        break
    try:
        if cv2.getWindowProperty(CAM_VIEW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break
    except cv2.error:
        break

cap.release()
cv2.destroyAllWindows()
