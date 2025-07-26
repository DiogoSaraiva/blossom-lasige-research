import cv2
from .config import VIDEO_WIDTH, VIDEO_HEIGHT
from pathlib import Path

class Recorder:
    def __init__(self, output_path, fps=30.0):
        self.video_writer = None
        self.fps = fps
        self.output_path = output_path


    @staticmethod
    def str2bool(value):
        if isinstance(value, bool):
            return value
        value = value.lower()
        if value in ("yes", "true", "t", "1"):
            return True
        elif value in ("no", "false", "f", "0"):
            return False
        else:
            raise ValueError("Expected a boolean value (true/false)")

    def start_recording(self, frame_size=(1280, 720)):
        Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # type: ignore[attr-defined]
            temp_writer = cv2.VideoWriter(self.output_path, fourcc, self.fps, frame_size)
            if not temp_writer.isOpened():
                temp_writer.release()
                raise IOError(f"cv2.VideoWriter failed to open file: {self.output_path}")
            self.video_writer = temp_writer
            print(f"[INFO] Recording enabled. Saving to: {self.output_path}")
        except Exception as e:
            self.video_writer = None
            print(f"[ERROR] Failed to open video writer: {e}")
            import traceback
            traceback.print_exc()

    def write_frame(self, frame):
        if self.video_writer:
            self.video_writer.write(frame)

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            print(f"[INFO] Recording saved to: {self.output_path}")
            self.video_writer = None