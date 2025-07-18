import math
import numpy as np
import mediapipe as mp

FACE_MESH_LANDMARKS = {
    'left_eye': 33,
    'right_eye': 263,
    'nose_tip': 1,
    'chin': 152,
    'forehead': 10,
    'left_cheek': 234,
    'right_cheek': 454,
    'left_shoulder': 234,
    'right_shoulder': 454
}

class PoseUtils:
    def __init__(self, facemesh_landmarks, pose_landmarks, frame):
        self.landmarks = facemesh_landmarks
        self.frame = frame
        self.mp_pose = mp.solutions.pose
        self.pose_landmarks = pose_landmarks

    def calculate_roll(self):
        h, w = self.frame.shape[:2]
        l_eye = self.landmarks[FACE_MESH_LANDMARKS['left_eye']]
        r_eye = self.landmarks[FACE_MESH_LANDMARKS['right_eye']]
        x1, y1 = int(l_eye.x * w), int(l_eye.y * h)
        x2, y2 = int(r_eye.x * w), int(r_eye.y * h)
        angle_rad = math.atan2(y2 - y1, x2 - x1)
        return math.degrees(angle_rad)

    def calculate_pitch(self):
        nose = self.landmarks[FACE_MESH_LANDMARKS['nose_tip']]
        chin = self.landmarks[FACE_MESH_LANDMARKS['chin']]
        return math.degrees(math.atan2(chin.y - nose.y, chin.z - nose.z))

    def calculate_yaw(self):
        left = self.landmarks[FACE_MESH_LANDMARKS['left_cheek']]
        right = self.landmarks[FACE_MESH_LANDMARKS['right_cheek']]
        return math.degrees(math.atan2(right.z - left.z, right.x - left.x))

    def estimate_height(self):
        nose_y = self.landmarks[FACE_MESH_LANDMARKS['nose_tip']].y
        mouth_y = (
                          self.pose_landmarks[self.mp_pose.PoseLandmark.MOUTH_LEFT].y +
                          self.pose_landmarks[self.mp_pose.PoseLandmark.MOUTH_RIGHT].y
                  ) / 2
        head_center_y = (nose_y + mouth_y) / 2

        l_shoulder = self.pose_landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        r_shoulder = self.pose_landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]

        shoulder_y = (l_shoulder.y + r_shoulder.y) / 2
        vertical_diff = shoulder_y - head_center_y
        shoulder_dx = abs(r_shoulder.x - l_shoulder.x)

        if shoulder_dx < 0.01:
            return None

        posture_ratio = np.clip((vertical_diff - 0.15) / (0.25 - 0.15), 0.0, 1.0)

        raw_distance = (shoulder_dx - 0.28) / (0.40 - 0.28)
        raw_distance = max(raw_distance, 0.0)
        distance_ratio = np.clip(raw_distance ** 0.5, 0.0, 1.0)

        combined = 0.8 * posture_ratio + 0.2 * distance_ratio
        return int(combined * 100)


