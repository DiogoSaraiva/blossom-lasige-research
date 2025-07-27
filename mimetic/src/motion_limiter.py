import time
import numpy as np

from mimetic.src.logging_utils import Logger


class MotionLimiter:
    """
    A class to limit the motion of a subject by smoothing and scaling pose data.
    This class applies a smoothing factor to the pose data, scales it to a six-unit range
    for specific keys, and determines when to send updates based on a threshold.
    It uses a logger for logging messages and can be configured with different smoothing parameters.
    :param alpha_map: A dictionary mapping keys to smoothing factors.
    :type alpha_map: dict
    :param rate_hz: The rate at which to send updates, in Hz.
    :type rate_hz: int
    :param threshold: The minimum change required to trigger an update.
    :type threshold: int
    :param logger: Logger instance for logging messages (optional).
    :type logger: Logger

    """
    def __init__(self, alpha_map: dict=None, rate_hz: int=5, threshold: int=2.0, logger:Logger=None):
        """
        Initializes the MotionLimiter with smoothing parameters, rate, threshold, and a logger.
        :param alpha_map: A dictionary mapping keys to smoothing factors.
        :type alpha_map: dict
        :param rate_hz: The rate at which to send updates, in Hz.
        :type rate_hz: int
        :param threshold: The minimum change required to trigger an update.
        :type threshold: int
        :param logger: Logger instance for logging messages (optional).
        :type logger: Logger
        """
        self.logger = logger
        self.alpha_map = alpha_map or {
            "x": 0.3,  # pitch
            "y": 0.2,  # roll
            "z": 0.1,  # yaw
            "h": 0.3,  # height
            "e": 0.2  # ears
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
        Converts a value to a six-unit range based on the provided minimum and maximum values.
        The value is clipped to the range [min_val, max_val] and then scaled to a range of 0 to 6.
        :param value: The value to convert.
        :type value: float
        :param min_val: The minimum value of the range.
        :type min_val: float
        :param max_val: The maximum value of the range.
        :type max_val: float
        :return: The value scaled to a six-unit range.
        :rtype: float
        :raises ValueError: If min_val is equal to max_val, which would cause division by zero.
        :raises TypeError: If value, min_val, or max_val are not numeric types.
        :raises Exception: If an unexpected error occurs during conversion.
        """
        return np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0) * 6.0

    def smooth_and_scale(self, key: str, value: float) -> float:
        """
        Smooths the value for the given key and scales it to a six-unit range.
        The value is first smoothed using an exponential moving average based on the alpha factor for the key.
        Then, it is clipped to a specific range based on the key and scaled to a six-unit range.
        :param key: The key for which the value is being smoothed and scaled.
        :type key: str
        :param value: The value to be smoothed and scaled.
        :type value: float
        :return: The smoothed and scaled value.
        :rtype: float
        :raises KeyError: If the key is not recognized.
        :raises TypeError: If value is not a numeric type.
        :raises Exception: If an unexpected error occurs during smoothing and scaling.
        :raises RuntimeError: If the logger fails to log a message.
        :raises RuntimeError: If the logger is not provided and no default logger is available.
        :raises RuntimeError: If the logger is not None and does not have a log method
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
        Smooths the value for the given key and scales it to a six-unit range.
        This method is a wrapper around the smooth_and_scale method, which applies smoothing
        and scaling based on the key.
        :param key: The key for which the value is being smoothed and scaled.
        :type key: str
        :param value: The value to be smoothed and scaled.
        :type value: float
        :return: The smoothed and scaled value, or None if the key is not recognized.
        :rtype: float or None
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
        Smooths the value for the given key using an exponential moving average.
        The smoothing factor is determined by the alpha_map for the key.
        :param key: The key for which the value is being smoothed.
        :type key: str
        :param value: The value to be smoothed.
        :type value: float
        :return: The smoothed value.
        :rtype: float
        :raises KeyError: If the key is not recognized.
        :raises TypeError: If value is not a numeric type.
        :raises Exception: If an unexpected error occurs during smoothing.
        :raises RuntimeError: If the logger fails to log a message.
        :raises RuntimeError: If the logger is not provided and no default logger is available.
        :raises RuntimeError: If the logger is not None and does not have a log method
        """
        alpha = self.alpha_map.get(key, 0.3)
        prev = self.smoothed.get(key, 0.0)
        smoothed = alpha * value + (1 - alpha) * prev
        self.smoothed[key] = smoothed
        return smoothed

    def should_send(self, keys: list) -> tuple[bool, float | None]:
        """
        Determines if the motion limiter should send an update based on the smoothed values.
        It checks if the time since the last sent update is greater than the minimum interval,
        and if the maximum change in the smoothed values exceeds the threshold.
        If both conditions are met, it updates the last sent time and returns True with a duration
        based on the maximum change. Otherwise, it returns False and None.
        :param keys: A list of keys to check for changes.
        :type keys: list
        :return: A tuple containing a boolean indicating whether to send an update,
                    and the duration for the update if applicable.
        :rtype: tuple (bool, float | None)
        :raises TypeError: If keys is not a list.
        :raises ValueError: If keys is empty.
        :raises Exception: If an unexpected error occurs during the check.
        :raises RuntimeError: If the logger fails to log a message.
        :raises RuntimeError: If the logger is not provided and no default logger is available.
        :raises RuntimeError: If the logger is not None and does not have a log method
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
        Returns the last smoothed value for the given key.
        :param key: The key for which to retrieve the last smoothed value.
        :type key: str
        :return: The last smoothed value for the key, or 0 if the key
        :rtype: float
        :raises KeyError: If the key is not recognized.
        :raises TypeError: If key is not a string.
        :raises Exception: If an unexpected error occurs while retrieving the value.
        :raises RuntimeError: If the logger fails to log a message.
        :raises RuntimeError: If the logger is not provided and no default logger is available.
        :raises RuntimeError: If the logger is not None and does not have a log method
        """
        return self.values.get(key, 0)