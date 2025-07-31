import subprocess
from pathlib import Path

import numpy as np

from mimetic.src.config import VIDEO_WIDTH, VIDEO_HEIGHT
from src.logging_utils import Logger

class FFmpegRecorder:
    def __init__(self, logger: Logger, output_path: str, fps: int = 30, resolution=(VIDEO_WIDTH, VIDEO_HEIGHT)):
        self.output_path = output_path
        self.fps = fps
        self.resolution = resolution
        self.logger = logger
        self.proc = None
        self.is_recording = False

    def start_recording(self):
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)

        width, height = self.resolution
        # noinspection SpellCheckingInspection
        cmd = [
            "ffmpeg",
            "-loglevel", "quiet",
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{width}x{height}",
            "-r", str(self.fps),
            "-i", "-",
            "-an",
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            self.output_path
        ]

        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            self.is_recording = True
            self.logger(f"[FFmpegRecorder] Recording started -> {self.output_path}", level="info")
        except Exception as e:
            self.logger(f"[FFmpegRecorder] Failed to start ffmpeg: {e}", level="critical")
            self.proc = None
            self.is_recording = False

    def write_frame(self, frame: np.ndarray):
        if not self.is_recording or self.proc is None or self.proc.stdin is None:
            self.logger("[FFmpegRecorder] Cannot write frame: ffmpeg not running", level="error")
            return False
        try:
            self.proc.stdin.write(frame.tobytes())
            return True
        except Exception as e:
            self.logger(f"[FFmpegRecorder] Failed to write frame: {e}", level="error")
            return False

    def stop_recording(self):
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.wait()
                self.logger(f"[FFmpegRecorder] Recording saved to {self.output_path}", level="info")
            except Exception as e:
                self.logger(f"[FFmpegRecorder] Failed to stop ffmpeg: {e}", level="error")
        else:
            self.logger("[FFmpegRecorder] No process to stop", level="warning")

        self.proc = None
        self.is_recording = False
