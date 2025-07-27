import threading
import cv2

from mimetic.src.logging_utils import Logger

class FrameCaptureThread(threading.Thread):
    """
    A thread that captures frames from a camera and provides methods to retrieve the latest frame.
    This thread continuously reads frames from the camera and stores the latest frame in a thread-safe manner.
    It can resize and mirror the video frames as needed.
    :param cam_index: Index of the camera to capture from (default is 0).
    :type cam_index: int
    """
    def __init__(self, cam_index=0, logger:Logger=None):
        """
        Initializes the FrameCaptureThread with a camera index and a logger.
        :param cam_index: Index of the camera to capture from (default is 0).
        :type cam_index: int
        :param logger: Logger instance for logging messages (optional).
        :type logger: Logger
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
            self.logger("[ERROR] Camera failed to open.", level="error")
            raise RuntimeError("Failed to open camera")
        for width, height in resolutions:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_width == width and actual_height == height:
                self.logger(f"[INFO] Usando resolução máxima suportada: {width}x{height}", level="info")
                break
        self.running = True
        self.latest_frame = None
        self.lock = threading.Lock()

    def run(self):
        """
        The main loop of the thread that captures frames from the camera.
        It continuously reads frames from the camera and updates the latest frame.
        If an error occurs during frame capture, it logs the error and prints the traceback.
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
        Retrieves the latest captured frame.
        If the frame is not available, it returns None.
        If width and height are specified, it resizes the frame to those dimensions.
        If mirror_video is True, it mirrors the frame horizontally.
        :param width: Desired width of the frame (optional).
        :type width: int
        :param height: Desired height of the frame (optional).
        :type height: int
        :param mirror_video: Whether to mirror the video frame horizontally (default is False).
        :type mirror_video: bool
        :return: The latest frame, resized and/or mirrored as specified, or None if no frame is available.
        :rtype: numpy.ndarray or None
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
        Stops the frame capture thread and releases the camera.
        """
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        self.logger("[FrameCaptureThread] Thread stopped", level="info")