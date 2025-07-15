import cv2
import mediapipe as mp
import numpy as np
import requests
mp_pose = mp.solutions.pose
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

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark
        pitch, roll, yaw = calculate_orientation(lm)
        height = estimate_height(lm)

        data = {
            "x": pitch,
            "y": roll,
            "z": yaw,
            "h": height,
            "ears": 50,
            "ax": 0,
            "ay": 0,
            "az": -1,
            "mirror": False
        }

        try:
            requests.post("http://robot:8000/position", json=data)
        except Exception as e:
            print("Erro ao enviar para Blossom:", e)

    if cv2.waitKey(5) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
