import time
import numpy as np

from mimetic.src.logging_utils import Logger

class MotionLimiter:
    """
    A class to limit and smooth motion data for pose estimation.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        alpha_map (dict): Mapping of keys to smoothing factors.
        smoothed (dict): Stores the last smoothed value for each key.
        last_sent (float): Timestamp of the last sent update.
        min_interval (float): Minimum interval between updates (in seconds).
        threshold (float): Minimum change required to trigger an update.
        last_data (dict): Last sent smoothed values.
        values (dict): Stores the last value for each key.
    """

    def __init__(self, alpha_map: dict=None, rate_hz: int=5, threshold: int=2.0, logger:Logger=None):
        """
        Initializes the MotionLimiter with smoothing parameters, update rate, threshold, and logger.

        Args:
            alpha_map (dict, optional): Mapping of keys to smoothing factors.
            rate_hz (int, optional): Update rate in Hz. Default is 5.
            threshold (float, optional): Minimum change to trigger update. Default is 2.0.
            logger (Logger, optional): Logger instance.
        """
        self.logger = logger
        self.alpha_map = alpha_map or {
            "x": 0.3,  # pitch
            "y": 0.2,  # roll
            "z": 0.1,  # yaw
            "h": 0.3,  # height
            "e": 0.2   # ears
        }
        self.smoothed = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "h": 50.0,
            "e": 70.0
        }
        self.last_sent = 0
        self.min_interval = 1.0 / rate_hz
        self.threshold = threshold
        self.last_data = self.smoothed.copy()
        self.values = {}

    @staticmethod
    def to_six_unit_range(value: float, min_val: float, max_val: float) -> float:
        """
        Scales a value to a 0-6 range, clipping to [min_val, max_val].

        Args:
            value (float): Value to scale.
            min_val (float): Minimum value of the range.
            max_val (float): Maximum value of the range.

        Returns:
            float: Value scaled to [0, 6].
        """
        return np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0) * 6.0

    def smooth_and_scale(self, key: str, value: float) -> float:
        """
        Smooths and scales the value for a given key.

        Args:
            key (str): Key to smooth and scale.
            value (float): Value to process.

        Returns:
            float: Smoothed and scaled value.
        """
        smoothed = self._smooth(key, value)

        match key:
            case "x" | "y":
                return self.to_six_unit_range(np.clip(smoothed, -150, 150), -150, 150)
            case "z":
                return self.to_six_unit_range(np.clip(smoothed, -40, 40), 0, 100)
            case "h":
                return self.to_six_unit_range(np.clip(smoothed, 0, 100), 0, 100)
            case "e":
                return self.to_six_unit_range(np.clip(smoothed, 50, 130), 50, 130)
            case _:
                return smoothed

    def smooth(self, key: str, value: float) -> float | None:
        """
        Wrapper to smooth and scale a value for a given key.

        Args:
            key (str): Key to process.
            value (float): Value to process.

        Returns:
            float or None: Smoothed and scaled value, or None if key is not recognized.
        """
        match key:
            case "x" | "y":
                return self.smooth_and_scale("x", value)
            case "z":
                return self.smooth_and_scale("z", value)
            case "h":
                return self.smooth_and_scale("h", value)
            case "e":
                return self.smooth_and_scale("e", value)
        return None

    def _smooth(self, key: str, value: float) -> float:
        """
        Applies exponential moving average smoothing to a value.

        Args:
            key (str): Key to smooth.
            value (float): Value to smooth.

        Returns:
            float: Smoothed value.
        """
        alpha = self.alpha_map.get(key, 0.3)
        prev = self.smoothed.get(key, 0.0)
        if value is None:
            return None
        smoothed = alpha * value + (1 - alpha) * prev
        self.smoothed[key] = smoothed
        return smoothed

    def should_send(self, keys: list) -> tuple[bool, float | None]:
        """
        Determines if an update should be sent based on smoothed values and time interval.

        Args:
            keys (list): Keys to check for changes.

        Returns:
            tuple: (should_send (bool), duration (float or None))
        """
        now = time.time()
        if now - self.last_sent < self.min_interval:
            return False, None

        max_change = max(abs(self.smoothed[k] - self.last_data[k]) for k in keys)
        if max_change > self.threshold:
            self.last_sent = now
            self.last_data = {k: self.smoothed[k] for k in keys}
            duration = np.clip(max_change / 100.0, 0.1, 0.4)
            return True, duration

        return False, None

    def last(self, key: str) -> float:
        """
        Returns the last value for a given key.

        Args:
            key (str): Key to retrieve.

        Returns:
            float: Last value for the key, or 0 if not found.
        """
        return self.values.get(key, 0)