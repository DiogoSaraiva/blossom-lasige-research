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

import numpy as np

def estimate_height(landmarks):
    nose_y = landmarks[mp_pose.PoseLandmark.NOSE].y
    mouth_y = (landmarks[mp_pose.PoseLandmark.MOUTH_LEFT].y + landmarks[mp_pose.PoseLandmark.MOUTH_RIGHT].y) / 2
    head_center_y = (nose_y + mouth_y) / 2

    l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

    shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
    vertical_diff = shoulder_y - head_center_y
    shoulder_dx = abs(r_shoulder.x - l_shoulder.x)

    # Normalize vertical posture (center of head above shoulders)
    posture_ratio = np.clip((vertical_diff - 0.15) / (0.25 - 0.15), 0.0, 1.0)

    # Normalize shoulder width (approximate depth / closeness)
    raw_distance = (shoulder_dx - 0.28) / (0.40 - 0.28)
    distance_ratio = np.clip(raw_distance ** 0.5, 0.0, 1.0)

    # Combine both factors
    combined = 0.8 * posture_ratio + 0.2 * distance_ratio

    return int(combined * 100)





def draw_overlay_info(frame, pitch, roll, yaw, height):
    """
    Draws pitch, roll, yaw and height info on the video frame.
    """
    orientation_text = f"Pitch: {pitch:.1f}  Roll: {roll:.1f}  Yaw: {yaw:.1f}"
    height_text = f"Height: {height}"

    cv2.putText(frame, orientation_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
    cv2.putText(frame, height_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

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

        draw_overlay_info(frame, pitch, roll, yaw, height)

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
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
            try:
                response = requests.post("http://robot:8000/position", json=data)
                print(f"Sent → Pitch: {x:.1f}, Roll: {y:.1f}, Yaw: {z:.1f}, Height: {h:.1f}, Duration: {duration:.2f}s")
            except Exception as e:
                print("Error sending to Blossom:", e)

        mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

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
