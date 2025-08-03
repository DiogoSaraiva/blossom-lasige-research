import threading
# noinspection PyPackageRequirements
import cv2

from src.logging_utils import Logger

class FrameCaptureThread(threading.Thread):
    """
    Thread that captures frames from a camera and provides methods to retrieve the latest frame.
    Continuously reads frames from the camera and stores the latest frame in a thread-safe way.
    Supports resizing and mirroring of video frames.

    Args:
        cam_index (int, optional): Index of the camera to capture from. Defaults to 0.
        logger (Logger, optional): Logger instance for logging messages.
    """
    def __init__(self, logger:Logger, cam_index=0):
        """
        Initializes the FrameCaptureThread with a camera index and a logger.

        Args:
            cam_index (int, optional): Index of the camera to capture from. Defaults to 0.
            logger (Logger): Logger instance for logging messages.
        """
        super().__init__()

        resolutions = [
            (1280, 720),  # HD
            (1024, 576),
            (800, 600),
            (640, 480)
        ]

        self.logger = logger
        self.cap = cv2.VideoCapture(cam_index)
        if not self.cap.isOpened():
            self.logger("[CaptureThread] Camera failed to open.", level="error")
            raise RuntimeError("Failed to open camera")
        for width, height in resolutions:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_width == width and actual_height == height:
                self.logger(f"[INFO] Using max supported resolution: {width}x{height}", level="info")
                break
        self.running = True
        self.latest_frame = None
        self.lock = threading.Lock()

    def run(self):
        """
        Main loop of the thread that captures frames from the camera.
        Continuously reads frames and updates the latest frame.
        Logs errors and prints traceback if an exception occurs.
        """
        self.logger("[FrameCaptureThread] Thread started")
        try:
            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
            self.cap.release()
        except Exception as e:
            self.logger(f"[FrameCaptureThread] CRASHED: {e}", level="critical")
            import traceback
            traceback.print_exc()

    def get_frame(self, width: int=None, height: int=None, mirror_video: bool=False):
        """
        Retrieves the latest captured frame, optionally resizing and/or mirroring it.

        Args:
            width (int, optional): Desired width of the frame.
            height (int, optional): Desired height of the frame.
            mirror_video (bool, optional): Whether to mirror the frame horizontally. Defaults to False.

        Returns:
            numpy.ndarray or None: The latest frame, processed as specified, or None if unavailable.
        """
        with self.lock:
            if self.latest_frame is None:
                return None
            frame = self.latest_frame.copy()
            if width and height:
                frame = cv2.resize(frame, (width, height))
            if mirror_video:
               frame = cv2.flip(frame, 1)
            return frame

    def stop(self):
        """
        Stops the frame capture thread and releases the camera resource.
        """
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        self.logger("[FrameCaptureThread] Thread stopped", level="info")