import subprocess
import threading
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

        self.process = None
        self.is_recording = False

    def start_recording(self):
        self.output_path = str(self.get_unique_filename(self.output_path))
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
            self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            self.is_recording = True
            self.logger(f"[FFmpegRecorder] Recording started -> {self.output_path}", level="info")
        except Exception as e:
            self.logger(f"[FFmpegRecorder] Failed to start ffmpeg: {e}", level="critical")
            self.process = None
            self.is_recording = False

    def stop_recording(self):
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait()
                self.logger(f"[FFmpegRecorder] Recording saved to {self.output_path}", level="info")
            except Exception as e:
                self.logger(f"[FFmpegRecorder] Failed to stop ffmpeg: {e}", level="error")
        else:
            self.logger("[FFmpegRecorder] No process to stop", level="warning")

        self.process = None
        self.is_recording = False


    def write_frame(self, frame: np.ndarray):
        if not self.is_recording or self.process is None or self.process.stdin is None:
            self.logger("[FFmpegRecorder] Cannot write frame: ffmpeg not running", level="error")
            return False
        try:
            self.process.stdin.write(frame.tobytes())
            return True
        except Exception as e:
            self.logger(f"[FFmpegRecorder] Failed to write frame: {e}", level="error")
            return False

    @staticmethod
    def get_unique_filename(input_path: str | Path, max_tries: int = 9) -> Path:

        path = Path(input_path)

        if not path.exists():
            return path

        base = path.stem
        suffix = path.suffix
        parent = path.parent

        for i in range(2, max_tries + 1):
            new_path = parent / f"{base}_{i}{suffix}"
            if not new_path.exists():
                return new_path
        raise FileExistsError(f"No available filename after {max_tries - 1} attempts for base: {path}")
