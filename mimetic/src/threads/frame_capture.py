import threading
import cv2

class FrameCaptureThread(threading.Thread):
    def __init__(self, cam_index=0):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[ERROR] Camera failed to open.")
        self.running = True
        self.latest_frame = None
        self.lock = threading.Lock()

    def run(self):
        print("[FrameCaptureThread] Thread started")
        try:
            while self.running and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
            self.cap.release()
        except Exception as e:
            print(f"[FrameCaptureThread] CRASHED: {e}")
            import traceback
            traceback.print_exc()

    def get_frame(self, width: int = None, height: int = None, mirror_video=False):
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
        self.running = False
        if self.cap.isOpened():
            self.cap.release()