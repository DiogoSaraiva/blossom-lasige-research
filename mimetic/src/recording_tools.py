import cv2
import time
from .config import VIDEO_WIDTH, VIDEO_HEIGHT


class RecordingTools:
    def __init__(self, fps=30.0):
        self.video_writer = None
        self.fps = fps
        self.filename = f"recording_{int(time.time())}.mp4"

    @staticmethod
    def str2bool(v):
        if isinstance(v, bool):
            return v
        v = v.lower()
        if v in ("yes", "true", "t", "1"):
            return True
        elif v in ("no", "false", "f", "0"):
            return False
        else:
            raise ValueError("Expected a boolean value (true/false)")

    def start_recording(self):
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v') # type: ignore[attr-defined]
        self.video_writer = cv2.VideoWriter(
            self.filename, fourcc, self.fps, (VIDEO_WIDTH, VIDEO_HEIGHT)
        )
        if self.video_writer.isOpened():
            print(f"[INFO] Recording enabled. Saving to: {self.filename}")
        else:
            print("[ERROR] Failed to open video writer.")

    def write_frame(self, frame):
        if self.video_writer:
            self.video_writer.write(frame)

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            print(f"[INFO] Recording saved to: {self.filename}")
            self.video_writer = None