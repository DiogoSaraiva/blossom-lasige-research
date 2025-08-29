from typing import Tuple

import numpy as np

RIGHT_EYE_CORNERS = (33, 133)
LEFT_EYE_CORNERS  = (362, 263)
RIGHT_IRIS = [468, 469, 470, 471]
LEFT_IRIS  = [473, 474, 475, 476]

class GazeEstimator:
    def __init__(self, alpha=0.5, left_threshold=0.45, right_threshold=0.55, mirror=False):
        self.alpha = alpha
        self.left_threshold = left_threshold
        self.right_threshold = right_threshold
        self.smooth_ratio = None
        self.mirror = mirror

    @staticmethod
    def _iris_center(landmarks, indexes):
        pts = np.array([(landmarks[i].x, landmarks[i].y) for i in indexes], dtype=np.float32)
        return pts.mean(axis=0)

    @staticmethod
    def _eye_ratio(landmarks, outer_idx, inner_idx, cx):
        x_out = landmarks[outer_idx].x
        x_in  = landmarks[inner_idx].x
        left_x, right_x = (x_out, x_in) if x_out < x_in else (x_in, x_out)
        denom = (right_x - left_x)
        if denom <= 1e-6:
            return 0.5
        r = (cx - left_x) / denom
        return float(np.clip(r, 0.0, 1.0))

    def update_from_landmarks(self, landmarks) -> Tuple[str, float]:

        if not landmarks or len(landmarks) < 477:
            self.smooth_ratio = self.smooth_ratio if self.smooth_ratio is not None else 0.5
            return "center", self.smooth_ratio

        right_iris_center = self._iris_center(landmarks, RIGHT_IRIS)
        left_iris_center = self._iris_center(landmarks, LEFT_IRIS)

        right_ratio = self._eye_ratio(landmarks, RIGHT_EYE_CORNERS[0], RIGHT_EYE_CORNERS[1], right_iris_center[0])
        left_ratio  = self._eye_ratio(landmarks,  LEFT_EYE_CORNERS[0],  LEFT_EYE_CORNERS[1],  left_iris_center[0])
        ratio = (right_ratio + left_ratio) * 0.5

        self.smooth_ratio = ratio if self.smooth_ratio is None else (self.alpha * ratio + (1 - self.alpha) * self.smooth_ratio)

        if self.smooth_ratio < self.left_threshold:
            label = "left"
        elif self.smooth_ratio > self.right_threshold:
            label = "right"
        else:
            label = "center"

        if self.mirror and label in ("left", "right"):
            label = "left" if label == "right" else "right"

        return label, self.smooth_ratio
