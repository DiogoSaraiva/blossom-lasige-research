import threading
import time

class AutonomousRecorderThread(threading.Thread):
    def __init__(self, recorder, capture_thread, resolution=(1280, 720), fps=30, mirror=True):
        super().__init__()
        self.recorder = recorder
        self.capture_thread = capture_thread
        self.resolution = resolution
        self.fps = fps
        self.mirror = mirror
        self.running = True

    def run(self):
        print("[AutonomousRecorder] Started")
        self.recorder.start_recording(frame_size=self.resolution)
        delay = 1.0 / self.fps
        next_frame_time = time.time()

        while self.running:
            now = time.time()
            if now < next_frame_time:
                time.sleep(next_frame_time - now)
            else:
                next_frame_time += delay  # agendar próxima frame, mesmo que atrasado

                frame = self.capture_thread.get_frame(mirror_video=self.mirror)
                if frame is not None and frame.size > 0:
                    self.recorder.write_frame(frame)

        self.recorder.stop_recording()
        print("[AutonomousRecorder] Stopped")

    def stop(self):
        self.running = False
        self.recorder.stop_recording()
