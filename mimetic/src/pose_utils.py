import math
import numpy as np
import mediapipe as mp

from src.logging_utils import Logger

FACE_MESH_LANDMARKS = {
    'left_eye': 33,
    'right_eye': 263,
    'nose_tip': 1,
    'chin': 152,
    'forehead': 10,
    'left_cheek': 234,
    'right_cheek': 454,
    'mouth_left': 61,
    'mouth_right': 291
}

POSE_LANDMARKS = {
    'left_shoulder': 11,
    'right_shoulder': 12,
    'mouth_left': 9,
    'mouth_right': 10
}

class PoseUtils:
    """
    Utility class for pose estimation calculations using MediaPipe landmarks.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        face_landmarks (list): List of face mesh landmarks.
        pose_landmarks (list): List of pose landmarks.
        mp_pose: Reference to MediaPipe pose solution.
    """

    def __init__(self, facemesh_landmarks, pose_landmarks, logger:Logger):
        """
        Initializes the PoseUtils class with face mesh and pose landmarks, and a logger.

        Args:
            facemesh_landmarks (list): Face mesh landmarks from MediaPipe.
            pose_landmarks (list): Pose landmarks from MediaPipe.
            logger (Logger): Logger instance for logging messages.
        """
        self.logger = logger
        self.face_landmarks = facemesh_landmarks
        self.pose_landmarks = pose_landmarks
        self.mp_pose = mp.solutions.pose

    def update(self, facemesh_landmarks, pose_landmarks):
        """
        Updates the PoseUtils instance with new face mesh and pose landmarks.

        Args:
            facemesh_landmarks (list): New face mesh landmarks from MediaPipe.
            pose_landmarks (list): New pose landmarks from MediaPipe.
        """
        self.face_landmarks = facemesh_landmarks
        self.pose_landmarks = pose_landmarks

    def _get_landmark(self, key, source='face'):
        try:
            if source == 'face':
                index = FACE_MESH_LANDMARKS[key]
                return self.face_landmarks[index]
            elif source == 'pose':
                index = POSE_LANDMARKS[key]
                return self.pose_landmarks[index]
            else:
                self.logger(f"[PoseUtils] Unknown landmark source: {source}", level='warning')
                return None
        except (KeyError, IndexError, TypeError) as e:
            self.logger(f"[PoseUtils] Failed to get landmark {key} from source: {source}: {e}", level='warning')
            return None


    def calculate_roll(self):
        """
        Calculates the roll angle of the face based on the position of the eyes.

        Returns:
            float or None: Roll angle in degrees, or None if landmarks are unavailable.
        """
        if not self.face_landmarks or len(self.face_landmarks) < 2:
            self.logger("[PoseUtils] No landmarks available for roll calculation", level='warning')
            return None
        l_eye = self._get_landmark('left_eye', 'face')
        r_eye = self._get_landmark('right_eye', 'face')
        dx = r_eye.x - l_eye.x
        dy = r_eye.y - l_eye.y
        angle_rad = math.atan2(dy, dx)
        return math.degrees(angle_rad)



    def calculate_pitch(self):
        """
        Calculates the pitch angle of the face based on the position of the nose and chin.

        Returns:
            float or None: Pitch angle in degrees, or None if landmarks are unavailable.
        """
        if not self.face_landmarks or len(self.face_landmarks) < 2: #TODO verify this
            self.logger("[PoseUtils] No landmarks available for pitch calculation", level='debug')
            return None
        if 'nose_tip' not in FACE_MESH_LANDMARKS or 'chin' not in FACE_MESH_LANDMARKS: #TODO verify this too
            self.logger("[PoseUtils] Required landmarks for pitch calculation are missing", level='debug')
            return None
        nose = self._get_landmark('nose_tip', 'face')
        chin = self._get_landmark('chin', 'face')
        return math.degrees(math.atan2(chin.y - nose.y, chin.z - nose.z))

    def calculate_yaw(self):
        """
        Calculates the yaw angle of the face based on the position of the left and right cheeks.

        Returns:
            float or None: Yaw angle in degrees, or None if landmarks are unavailable.
        """
        if not self.face_landmarks or len(self.face_landmarks) < 2:
            self.logger("[PoseUtils] No landmarks available for yaw calculation", level='debug')
            return None
        left = self._get_landmark('left_cheek', 'face')
        right = self._get_landmark('right_cheek', 'face')

        return math.degrees(math.atan2(right.z - left.z, right.x - left.x))

    def estimate_height(self):
        """
        Estimates the height of the person based on the position of the shoulders and head.

        Returns:
            int or None: Estimated height as a percentage of a reference height, or None if estimation fails.
        """
        if not self.face_landmarks or not self.pose_landmarks:
            self.logger("[PoseUtils] No landmarks available for height estimation", level='debug')
            return None
        try:
            nose = self._get_landmark('nose_tip', 'face')
            mouth_left = self._get_landmark('mouth_left', 'face')
            mouth_right = self._get_landmark('mouth_right', 'face')
            mouth_y = (mouth_left.y + mouth_right.y) / 2
            head_center_y = (nose.y + mouth_y) / 2

            l_shoulder = self._get_landmark('left_shoulder', 'pose')
            r_shoulder = self._get_landmark('right_shoulder', 'pose')

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
        except Exception as e:
            self.logger(f"[PoseUtils] Error estimating height: {e}", level='warning')
            return None

    @staticmethod
    def normalize_vector(v):
        norm = np.linalg.norm(v)
        if isinstance(norm, np.ndarray):
            norm = norm.item()
        return v / norm if norm > 1e-8 else np.zeros_like(v)

    def get_head_orientation(self):
        """
        Calculates pitch, yaw, and roll using a 3D orthonormal basis built from head landmarks.
        Returns:
            tuple or None: (pitch, yaw, roll) in degrees, or None if landmarks are missing.
        """
        nose = self._get_landmark('nose_tip', 'face')
        chin = self._get_landmark('chin', 'face')
        forehead = self._get_landmark('forehead', 'face')
        l_cheek = self._get_landmark('left_cheek', 'face')
        r_cheek = self._get_landmark('right_cheek', 'face')

        if not all([nose, chin, forehead, l_cheek, r_cheek]):
            self.logger("[PoseUtils] Missing landmarks for 3D head orientation", level='debug')
            return None

        up = self.normalize_vector(np.array([
            forehead.x - chin.x,
            forehead.y - chin.y,
            forehead.z - chin.z
        ]))
        right = self.normalize_vector(np.array([
            r_cheek.x - l_cheek.x,
            r_cheek.y - l_cheek.y,
            r_cheek.z - l_cheek.z
        ]))
        forward = self.normalize_vector(np.cross(up, right))
        right = self.normalize_vector(np.cross(forward, up))  # re-orthogonalize

        # noinspection PyPep8Naming
        R = np.array([right, up, forward]).T

        try:
            pitch = math.atan2(R[2, 1], R[2, 2])
            roll = math.atan2(R[1, 0], R[0, 0])
            yaw = math.atan2(-R[0, 2], R[0, 0])

            return (
                math.degrees(pitch),
                math.degrees(roll),
                math.degrees(yaw)
            )
        except Exception as e:
            self.logger(f"[PoseUtils] Error computing head orientation: {e}", level='warning')
            return None
