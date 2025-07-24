import threading
from queue import Queue, Empty


class RecorderThread(threading.Thread):
    def __init__(self, recorder, resolution, max_queue=32):
        super().__init__()
        self.queue = Queue(maxsize=max_queue)
        self.running = True
        self.recorder = recorder
        self.resolution = resolution

    def run(self):
        print("[RecorderThread] Thread started")
        try:
            self.recorder.start_recording(frame_size=self.resolution)

            while self.running:
                try:
                    frame = self.queue.get(timeout=0.1)
                except Empty:
                    continue

                if frame is None or frame.size == 0:
                    continue

                self.recorder.write_frame(frame)

        except Exception as e:
            print(f"[RecorderThread] CRASHED: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.recorder.stop_recording()
            print("[RecorderThread] Thread stopped")

    def record(self, frame):
        if self.queue.full():
            return
        if frame is not None and frame.size > 0:
            try:
                self.queue.put_nowait(frame)
            except Exception as e:
                print(f"[RecorderThread] CRASHED: {e}")
                import traceback
                traceback.print_exc()

    def stop(self):
        self.running = False
        with self.queue.mutex:
            self.queue.queue.clear()