import threading
import time

from mimetic.src.logging_utils import Logger
from mimetic.src.recording_tools import Recorder
from mimetic.src.threads.frame_capture import FrameCaptureThread


class AutonomousRecorderThread(threading.Thread):
    """
    A thread that autonomously records video frames from a camera using a Recorder instance.
    It captures frames from a FrameCaptureThread, writes them to the recorder, and maintains a specified frames per second (fps).
    The thread can be stopped gracefully, and it handles errors during the recording process.
    """
    def __init__(self, recorder: Recorder, capture_thread: FrameCaptureThread, resolution: (int, int)=(1280, 720), fps: int=30, mirror: bool=True, logger: Logger=None):
        """
        Initializes the AutonomousRecorderThread with a recorder, capture thread, resolution, fps, and mirror settings.
        :param recorder: Recorder instance to handle video recording.
        :type recorder: Recorder
        :param capture_thread: FrameCaptureThread instance to get frames from the camera.
        :type capture_thread: FrameCaptureThread
        :param resolution: Tuple specifying the resolution of the video frames (width, height).
        :type resolution: tuple(int, int)
        :param fps: Frames per second for the video recording.
        :type fps: int
        :param mirror: Boolean indicating whether to mirror the video frames.
        :type mirror: bool
        :param logger: Logger instance for logging messages (optional).
        :type logger: Logger
        """
        super().__init__()
        self.logger = logger
        self.recorder = recorder
        self.capture_thread = capture_thread
        self.resolution = resolution
        self.fps = fps
        self.mirror = mirror
        self.running = True

    def run(self):
        """
        The main loop of the thread that starts recording video frames.
        It continuously retrieves frames from the capture thread, writes them to the recorder, and handles timing
        to maintain the specified frames per second (fps).
        If an error occurs during recording, it logs the error and prints the traceback.
        """
        self.logger("[AutonomousRecorder] Started", level="info")
        if not self.capture_thread.running:
            self.logger("[AutonomousRecorder] Capture thread is not running. Exiting.", level="error")
            return
        try:
            self.recorder.start_recording(frame_size=self.resolution)
        except Exception as e:
            self.logger(f"[AutonomousRecorder] CRASHED: {e}", level="critical")
            import traceback
            traceback.print_exc()

        self.logger(f"[AutonomousRecorder] Recording started at {self.fps} FPS with resolution {self.resolution[0]}x{self.resolution[1]}", level="info")

        delay = 1.0 / self.fps
        next_frame_time = time.time()
        try:
            while self.running:
                now = time.time()
                sleep_time = max(0.0, next_frame_time - now)
                time.sleep(sleep_time)
                frame = self.capture_thread.get_frame(mirror_video=self.mirror)
                if frame is not None and frame.size > 0:
                    self.recorder.write_frame(frame)
                next_frame_time += delay
        except Exception as e:
            self.logger(f"[AutonomousRecorder] CRASHED: {e}", level="critical")
            import traceback
            traceback.print_exc()
        try:
            self.recorder.stop_recording()
        except Exception as e:
            self.logger(f"[AutonomousRecorder] Error stopping recording: {e}", level="error")

    def stop(self):
        """
        Stops the recording thread and releases the recorder.
        It sets the running flag to False and stops the recorder.
        """
        self.running = False
        self.recorder.stop_recording()
        self.logger("[AutonomousRecorder] Thread stopped", level="info")
