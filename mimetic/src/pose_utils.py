import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose


def calculate_orientation(landmarks):
    """
    Calculate pitch, roll, and yaw based on shoulder and hip positions.

    Args:
        landmarks: List of pose landmarks from MediaPipe.

    Returns:
        Tuple of (pitch, roll, yaw) in degrees.
    """

    def v(l): return np.array([l.x, l.y, l.z])

    # Get key joint positions
    l_shoulder = v(landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER])
    r_shoulder = v(landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER])
    l_hip = v(landmarks[mp_pose.PoseLandmark.LEFT_HIP])
    r_hip = v(landmarks[mp_pose.PoseLandmark.RIGHT_HIP])

    # Compute shoulder direction vector and vertical trunk vector
    shoulder_vec = r_shoulder - l_shoulder
    vertical_vec = (r_shoulder + l_shoulder) / 2 - (r_hip + l_hip) / 2

    # Compute angles in degrees
    roll = np.arctan2(shoulder_vec[1], shoulder_vec[0]) * 180 / np.pi
    pitch = np.arctan2(vertical_vec[2], vertical_vec[1]) * 180 / np.pi
    yaw = np.arctan2(shoulder_vec[2], shoulder_vec[0]) * 180 / np.pi

    return pitch, roll, yaw


def estimate_height(landmarks):
    """
    Estimate vertical posture height using nose and ankle landmarks.

    Args:
        landmarks: List of pose landmarks from MediaPipe.

    Returns:
        Estimated height value mapped to [0, 100].
    """
    nose_y = landmarks[mp_pose.PoseLandmark.NOSE].y
    l_ankle_y = landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y
    r_ankle_y = landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].y
    ankle_y = min(l_ankle_y, r_ankle_y)

    # Compute relative height ratio, clipped to [0, 1]
    height_ratio = max(0.0, min(1.0, (ankle_y - nose_y) * 2))
    return int(height_ratio * 100)
