from idlelib.configdialog import HelpFrame

import cv2
from pathlib import Path

from mimetic.src.config import VIDEO_WIDTH, VIDEO_HEIGHT

from mimetic.src.logging_utils import Logger


class Recorder:
    def __init__(self, output_path, fps: int=30, logger: Logger=None):
        """
        Initializes the Recorder with an output path, frames per second (fps), and a logger.
        :param output_path: Path where the recorded video will be saved.
        :type output_path: str
        :param fps: Frames per second for the video recording (default is 30).
        :type fps: int
        :param logger: Logger instance for logging messages (optional).
        :type logger: Logger
        """

        self.logger = logger
        self.video_writer = None
        self.fps = fps
        self.output_path = output_path
        self.is_recording = False


    @staticmethod
    def str2bool(value):
        """
        Converts a string representation of truth to a boolean value.
        Accepts various string inputs like "yes", "no", "true", "false",
        "t", "f", "1", "0" and returns the corresponding boolean value
        :param value: String value to convert to boolean.
        :type value: str
        :return: Boolean value corresponding to the input string.
        :rtype: bool
        """
        if isinstance(value, bool):
            return value
        value = value.lower()
        if value in ("yes", "true", "t", "1"):
            return True
        elif value in ("no", "false", "f", "0"):
            return False
        else:
            raise ValueError("Expected a boolean value (true/false)")

    def start_recording(self, frame_size=(VIDEO_WIDTH, VIDEO_HEIGHT)):
        """
        Starts the video recording by initializing the VideoWriter with the specified frame size.
        Creates the output directory if it does not exist.
        :param frame_size: Tuple specifying the width and height of the video frames (default is (1280, 720)).
        :type frame_size: tuple(int, int)
        """
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            temp_writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, frame_size)
            if not temp_writer.isOpened():
                temp_writer.release()
                raise IOError(f"cv2.VideoWriter failed to open file: {self.output_path}")
            self.video_writer = temp_writer
            self.is_recording = True
            self.logger(f"[Recorder] Recording enabled. Saving to: {self.output_path}", level='info')
        except Exception as e:
            self.video_writer = None
            self.is_recording = False
            self.logger(f"[Recorder] Failed to open video writer: {e}", level='critical')
            import traceback
            traceback.print_exc()


    def write_frame(self, frame):
        """
        Writes a single frame to the video file.
        :param frame: The frame to write, should be a valid image array.
        :type frame: numpy.ndarray
        """
        if self.is_recording:
            if self.video_writer:
                self.video_writer.write(frame)
            else:
                self.logger("[Recorder] VideoWriter is not initialized or recording stopped. Cannot write frame.", level='critical')

    def stop_recording(self):
        """
        Stops the video recording and releases the VideoWriter.
        If the VideoWriter is not initialized, it does nothing.
        """
        if self.video_writer:
            self.video_writer.release()
            self.logger(f"[Recorder] Recording saved to: {self.output_path}", level='info')
            self.video_writer = None
        self.is_recording = False