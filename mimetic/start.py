import time
from datetime import datetime

import cv2

from mimetic.src.motion_limiter import MotionLimiter
from mimetic.src.stream_buffer import ResultBuffer
from mimetic.src.threads.AutonomousRecorderThread import AutonomousRecorderThread
from mimetic.src.threads.blossom_sender import BlossomSenderThread
from mimetic.src.threads.frame_capture import FrameCaptureThread
from mimetic.src.threads.mediapipe_thread import MediaPipeThread
from mimetic.src.visual_utils import Visualization
from src.logging_utils import Logger
from src.recording_tools import Recorder


class Mimetic:
    def __init__(self, output_folder: str, study_id: str or int, host: str, port: int, mirror_video: bool = True):
        study_timestamp = self.compact_timestamp()
        self.study_id = study_id or study_timestamp
        self.host = host
        self.port = port
        self.mirror_video = mirror_video

        self.logger = Logger(f"{output_folder}/{self.study_id}_log.json")
        self.recorder = Recorder(f"{output_folder}/{self.study_id}_recording.mp4")
        self.limiter = MotionLimiter()
        self.visualization = Visualization()
        self.buffer = ResultBuffer()

        self.cam_view_title = "Pose Estimation " + " (Mirrored)" if mirror_video else ""
        self.running = True

    def main(self):
        capture_thread = FrameCaptureThread()
        capture_thread.start()

        timeout_sec = 5
        interval_sec = 0.01
        max_attempts = int(timeout_sec / interval_sec)

        for _ in range(max_attempts):
            frame_display = capture_thread.get_frame(mirror_video=True)
            if frame_display is not None and frame_display.size > 0:
                break
            time.sleep(interval_sec)
        else:
            raise RuntimeError("Failed to capture initial frame within timeout.")

        height, width = frame_display.shape[:2]
        print(f"[INFO] Detected resolution: {width}x{height}")
        blossom_sender = BlossomSenderThread(host=self.host, port=self.port)
        mp_thread = MediaPipeThread(result_buffer=self.buffer)

        blossom_sender.start()
        mp_thread.start()

        recorder_thread = AutonomousRecorderThread(self.recorder, capture_thread, resolution=(width, height), fps=30, mirror=self.mirror_video)
        recorder_thread.start()

        last_pose_data = None

        prev_time = time.time()

        try:
            while self.running:
                frame_display = capture_thread.get_frame(mirror_video=True)

                # Full resolution for display/recording
                if frame_display is not None:
                    height, width = frame_display.shape[:2]

                # Reduced resolution for MediaPipe
                frame_mp = capture_thread.get_frame(mirror_video=self.mirror_video,  width=min(320, width), height=min(180, height))
                if frame_mp is None:
                    continue
                mp_thread.send(frame_mp)

                # Read results
                pose_data, _ = self.buffer.get_latest_pose_data()
                if pose_data is not None:
                    last_pose_data = pose_data

                if last_pose_data is None:
                    continue  # wait until first pose is available

                pitch = last_pose_data["pitch"]
                roll = last_pose_data["roll"]
                yaw = last_pose_data["yaw"]
                height = last_pose_data["height"]

                current_time = time.time()
                fps = 1.0 / (current_time - prev_time)
                prev_time = current_time

                x = self.limiter.smooth('x', pitch)
                y = self.limiter.smooth('y', roll)
                z = self.limiter.smooth('z', yaw)
                h = self.limiter.smooth('h', height)
                e = self.limiter.smooth('e', height)

                axis = {'pitch': pitch, 'roll': roll, 'yaw': yaw}
                should_send, duration = self.limiter.should_send(["x", "y", "z", "h"])

                payload = {
                    "x": x,
                    "y": y,
                    "z": z,
                    "h": h,
                    "ears": e,
                    "ax": 0,
                    "ay": 0,
                    "az": -1,
                    "duration_ms": int(duration * 1000) if duration else 500
                }

                if should_send:
                    sent_data = payload
                    data = {
                        "axis": axis,
                        "blossom_data": {
                            "calc_data": {"x": x, "y": y, "z": z, "h": h},
                            "sent_data": sent_data
                        },
                        "height": height,
                        "fps": fps
                    }
                else:
                    data = {
                        "axis": axis,
                        "height": height,
                        "fps": fps
                    }

                self.visualization.update(frame_display, None, None, data)  # face/pose_results não usados
                self.visualization.add_overlay()
                cv2.imshow(self.cam_view_title, frame_display)
                if cv2.waitKey(1) & 0xFF == 27:
                    print("[Main] ESC pressed")
                    self.running = False
                    break
                try:
                    if cv2.getWindowProperty(self.cam_view_title, cv2.WND_PROP_VISIBLE) < 1:
                        print("[Main] Window Closed")
                        break
                except cv2.error:
                    break
                # Optional logging
                self.logger.log(data)

                if should_send:
                    try:
                        blossom_sender.send(payload)
                    except Exception as e:
                        print("Error sending to Blossom:", e)

        except KeyboardInterrupt:
            print("[INFO] Ctrl+C detected.")
            self.running = False

        finally:
            print("[INFO] Shutting down...")
            capture_thread.stop()
            capture_thread.join()
            blossom_sender.stop()
            blossom_sender.join()
            recorder_thread.stop()
            recorder_thread.join()
            mp_thread.stop()
            mp_thread.join()
            self.recorder.stop_recording()
            self.logger.save_log()
            cv2.destroyAllWindows()

    @staticmethod
    def compact_timestamp() -> str:
        now = datetime.now()
        return now.strftime("%Y%m%d%H%M%S") + f"{int(now.microsecond / 1000):03d}"


if __name__ == "__main__":
    mimetic = Mimetic(
        output_folder="tests",
        study_id=1,
        host="localhost",
        port=8000,
        mirror_video=True
    )
    mimetic.main()
