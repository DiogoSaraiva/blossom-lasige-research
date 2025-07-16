import math
import numpy as np

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
    def __init__(self, face_landmarks, frame):
        self.landmarks = face_landmarks
        self.frame = frame

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
      return 50
      # TODO