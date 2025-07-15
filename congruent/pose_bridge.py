import cv2
import mediapipe as mp
import numpy as np
import requests
from src.motion_limiter import MotionLimiter

CAM_VIEW_TITLE = "Pose Estimation (Mirrored)"
limiter = MotionLimiter()

# Initialize MediaPipe Pose module and drawing utilities
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
pose = mp_pose.Pose()
cap = cv2.VideoCapture(0)

def calculate_orientation(landmarks):
    l_shoulder = np.array([landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x,
                           landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y,
                           landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].z])
    r_shoulder = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x,
                           landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y,
                           landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].z])
    l_hip = np.array([landmarks[mp_pose.PoseLandmark.LEFT_HIP].x,
                      landmarks[mp_pose.PoseLandmark.LEFT_HIP].y,
                      landmarks[mp_pose.PoseLandmark.LEFT_HIP].z])
    r_hip = np.array([landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x,
                      landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y,
                      landmarks[mp_pose.PoseLandmark.RIGHT_HIP].z])
    shoulder_vector = r_shoulder - l_shoulder
    vertical_vector = ((r_shoulder + l_shoulder) / 2) - ((r_hip + l_hip) / 2)
    roll = np.arctan2(shoulder_vector[1], shoulder_vector[0]) * 180 / np.pi
    pitch = np.arctan2(vertical_vector[2], vertical_vector[1]) * 180 / np.pi
    yaw = np.arctan2(shoulder_vector[2], shoulder_vector[0]) * 180 / np.pi
    return pitch, roll, yaw

def estimate_height(landmarks):
    nose_y = landmarks[mp_pose.PoseLandmark.NOSE].y
    l_ankle_y = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y
    r_ankle_y = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].y
    ankle_y = min(l_ankle_y, r_ankle_y)
    height_ratio = max(0.0, min(1.0, (ankle_y - nose_y) * 2))
    return int(height_ratio * 100)

# Main loop
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(image_rgb)

    if hasattr(results, 'pose_landmarks') and results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        pitch, roll, yaw = calculate_orientation(lm)
        height = estimate_height(lm)

        # Smooth all relevant axes
        x = limiter.smooth("x", pitch)
        y = limiter.smooth("y", roll)
        z = limiter.smooth("z", yaw)
        h = limiter.smooth("h", height)

        # Decide whether to send update
        should_send, duration = limiter.should_send(["x", "y", "z", "h"])

        if should_send:
            data = {
                "x": x,
                "y": y,
                "z": z,
                "h": h,
                "ears": limiter.smooth("e", h),  # optional: ears follow height
                "ax": 0,
                "ay": 0,
                "az": -1,
                "mirror": True
            }

            try:
                response = requests.post("http://robot:8000/position", json=data)
                print(f"Sent → Pitch: {x:.1f}, Roll: {y:.1f}, Yaw: {z:.1f}, Height: {h:.1f}, Duration: {duration:.2f}s")
            except Exception as e:
                print("Error sending to Blossom:", e)

        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

    cv2.imshow(CAM_VIEW_TITLE, frame)
    if cv2.waitKey(5) & 0xFF == 27:
        break
    if cv2.getWindowProperty(CAM_VIEW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
        break

cap.release()
cv2.destroyAllWindows()
