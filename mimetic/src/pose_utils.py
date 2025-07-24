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
}

POSE_LANDMARKS = {
    'left_shoulder': 11,
    'right_shoulder': 12,
    'mouth_left': 9,
    'mouth_right': 10
}

class PoseUtils:
    def __init__(self, facemesh_landmarks=None, pose_landmarks=None):
        self.landmarks = facemesh_landmarks
        self.pose_landmarks = pose_landmarks
        self.mp_pose = mp.solutions.pose

    def update(self, facemesh_landmarks, pose_landmarks):
        self.landmarks = facemesh_landmarks
        self.pose_landmarks = pose_landmarks

    def calculate_roll(self):
        l_eye = self.landmarks[FACE_MESH_LANDMARKS['left_eye']]
        r_eye = self.landmarks[FACE_MESH_LANDMARKS['right_eye']]
        dx = r_eye.x - l_eye.x
        dy = r_eye.y - l_eye.y
        angle_rad = math.atan2(dy, dx)
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
        try:
            nose_y = self.landmarks[FACE_MESH_LANDMARKS['nose_tip']].y
            mouth_left_y = self.pose_landmarks[POSE_LANDMARKS['mouth_left']].y
            mouth_right_y = self.pose_landmarks[POSE_LANDMARKS['mouth_right']].y
            mouth_y = (mouth_left_y + mouth_right_y) / 2
            head_center_y = (nose_y + mouth_y) / 2

            l_shoulder = self.pose_landmarks[POSE_LANDMARKS['left_shoulder']]
            r_shoulder = self.pose_landmarks[POSE_LANDMARKS['right_shoulder']]

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
        except:
            return None
