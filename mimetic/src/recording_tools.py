import cv2
from pathlib import Path

from mimetic.src.config import VIDEO_WIDTH, VIDEO_HEIGHT
from mimetic.src.logging_utils import Logger

class Recorder:
    """
    Recorder class for handling video recording using OpenCV.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        video_writer (cv2.VideoWriter): OpenCV VideoWriter object.
        fps (int): Frames per second for the video recording.
        output_path (str): Path where the recorded video will be saved.
        is_recording (bool): Indicates if recording is active.
        pts_list (list): List of presentation timestamps (PTS) for written frames.
    """

    def __init__(self, output_path, fps: int=30, logger: Logger=None):
        """
        Initializes the Recorder with an output path, frames per second (fps), and a logger.

        Args:
            output_path (str): Path where the recorded video will be saved.
            fps (int, optional): Frames per second for the video recording (default is 30).
            logger (Logger, optional): Logger instance for logging messages.
        """
        self.pts_list = []
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
        "t", "f", "1", "0" and returns the corresponding boolean value.

        Args:
            value (str or bool): String value to convert to boolean.

        Returns:
            bool: Boolean value corresponding to the input string.

        Raises:
            ValueError: If the input is not a recognized boolean string.
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

        Args:
            frame_size (tuple of int, optional): Width and height of the video frames (default is (VIDEO_WIDTH, VIDEO_HEIGHT)).
        """
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            fourcc = cv2.VideoWriter_fourcc(*'MJPG') # type: ignore
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

    def write_frame(self, frame, pts: int):
        """
        Writes a single frame to the video file.

        Args:
            frame (numpy.ndarray): The frame to write, should be a valid image array.
            pts (int): Presentation timestamp for the frame.

        Notes:
            Skips frames with non-increasing PTS to avoid duplicates.
        """
        if not self.is_recording or not self.video_writer:
            self.logger("[Recorder] Cannot write frame: not recording or writer missing.", level='critical')
            return

        # Prevent duplicated or non-increasing PTS
        if pts is not None:
            if self.pts_list and pts <= self.pts_list[-1]:
                self.logger(f"[Recorder] Skipping frame with non-increasing pts={pts}", level='warning')
                return
            self.pts_list.append(pts)

        self.video_writer.write(frame)

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