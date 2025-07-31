import threading
import time
from src.ffmpeg_recorder import FFmpegRecorder
from src.logging_utils import Logger
from src.threads.frame_capture import FrameCaptureThread


class RecorderThread(threading.Thread):
    def __init__(self, output_path: str, capture_thread: FrameCaptureThread, logger: Logger,
                 resolution: (int, int) = (1280, 720), fps: int = 30, mirror: bool = True):
        super().__init__()
        self.logger = logger
        self.capture_thread = capture_thread
        self.resolution = resolution
        self.fps = fps
        self.mirror = mirror
        self.running = False
        self.stopped = True
        self.recorder = FFmpegRecorder(output_path=output_path, fps=self.fps, resolution=self.resolution, logger=self.logger)

    def run(self):
        self.running = True
        self.stopped = False
        self.logger("[Recorder] Started", level="info")

        if not self.capture_thread.running:
            self.logger("[Recorder] Capture thread is not running. Exiting.", level="error")
            self.stopped = True
            return

        try:
            self.recorder.start_recording()
        except Exception as e:
            import traceback
            self.logger(f"[Recorder] CRASHED: {e}\n{traceback.format_exc()}", level="critical")
            self.stopped = True
            return

        self.logger(f"[Recorder] Recording started at {self.fps} FPS with resolution {self.resolution[0]}x{self.resolution[1]}", level="info")

        interval = 1.0 / self.fps
        next_frame_time = time.time() + interval
        first_written = False

        try:
            while self.running:
                frame = self.capture_thread.get_frame(mirror_video=self.mirror)
                if frame is not None and frame.size > 0:
                    success = self.recorder.write_frame(frame)
                    if success and not first_written:
                        self.logger("[Recorder] First frame written.", level="info")
                        first_written = True
                else:
                    self.logger("[Recorder] Skipped empty frame", level="warning")
                    time.sleep(0.1)
                    continue

                time.sleep(max(0.0, next_frame_time - time.time()))
                next_frame_time += interval

        except Exception as e:
            import traceback
            self.logger(f"[Recorder] CRASHED: {e}\n{traceback.format_exc()}", level="critical")

        finally:
            if not self.stopped:
                try:
                    self.recorder.stop_recording()
                except Exception as e:
                    self.logger(f"[Recorder] Error stopping recording: {e}", level="error")
                self.stopped = True
            self.logger("[Recorder] Thread stopped", level="info")
            self.logger(f"[Recorder] Recordings saved to {self.recorder.output_path}", level="info")

    def stop(self):
        self.logger("[Recorder] Stop called", level="debug")
        self.running = False
        if not self.stopped:
            try:
                self.recorder.stop_recording()
            except Exception as e:
                self.logger(f"[Recorder] Error stopping recording (manual): {e}", level="error")
            self.stopped = True
