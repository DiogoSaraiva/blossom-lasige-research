import time
from datetime import datetime
import cv2

from mimetic.src.motion_limiter import MotionLimiter
from mimetic.src.stream_buffer import ResultBuffer
from mimetic.src.threads.recorder_thread import AutonomousRecorderThread
from mimetic.src.threads.blossom_sender import BlossomSenderThread
from mimetic.src.threads.frame_capture import FrameCaptureThread
from mimetic.src.threads.mediapipe_thread import MediaPipeThread
from mimetic.src.visual_utils import Visualization
from mimetic.src.logging_utils import Logger, print_logger
from mimetic.src.recording_tools import Recorder


class Mimetic:
    def __init__(self, output_folder: str, study_id: str or int, host: str, port: int, mirror_video: bool = True,
                 print_to_terminal: bool = True):
        study_timestamp = self.compact_timestamp()
        self.study_id = study_id or study_timestamp
        self.host = host
        self.port = port
        self.mirror_video = mirror_video
        self.debug_mode = print_to_terminal
        self.pose_logger = Logger(f"{output_folder}/{self.study_id}/pose_log.json", mode="pose")
        self.system_logger = Logger(f"{output_folder}/{self.study_id}/system_log.json", mode="system") if (
                    print_to_terminal == False) else print_logger
        self.recorder = Recorder(f"{output_folder}/{self.study_id}/recording.avi", logger=self.system_logger)
        self.limiter = MotionLimiter()
        self.visualization = Visualization()
        self.buffer = ResultBuffer()
        self.cam_view_title = "Pose Estimation " + " (Mirrored)" if mirror_video else ""
        self.running = True

    def main(self):
        capture_thread = FrameCaptureThread(logger=self.system_logger)
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

        frame_height, frame_width = frame_display.shape[:2]
        self.system_logger(f"[INFO] Detected resolution: {frame_width}x{frame_height}")
        blossom_sender_thread = BlossomSenderThread(host=self.host, port=self.port, logger=self.system_logger)
        mp_thread = MediaPipeThread(result_buffer=self.buffer, logger=self.system_logger)

        blossom_sender_thread.start()
        mp_thread.start()

        recorder_thread = AutonomousRecorderThread(self.recorder, capture_thread,
                                                   resolution=(frame_width, frame_height), fps=30,
                                                   mirror=self.mirror_video, logger=self.system_logger)
        recorder_thread.start()

        last_pose_data = None

        prev_time = time.time()

        target_fps = 30
        frame_duration = 1.0 / target_fps

        try:
            while self.running:
                frame_start_time = time.time()
                frame_display = capture_thread.get_frame(mirror_video=True)

                # Full resolution for display/recording
                if frame_display is not None:
                    frame_height, frame_width = frame_display.shape[:2]

                # Reduced resolution for MediaPipe
                frame_mp = capture_thread.get_frame(mirror_video=self.mirror_video, width=min(320, frame_width),
                                                    height=min(180, frame_height))
                if frame_mp is None:
                    continue
                mp_thread.send(frame_mp)

                # Read results
                pose_data, _ = self.buffer.get_latest_pose_data()
                if pose_data is not None:
                    last_pose_data = pose_data

                if last_pose_data is None:
                    continue  # wait until for the first pose is available
                pitch = last_pose_data["pitch"]
                roll = last_pose_data["roll"]
                yaw = last_pose_data["yaw"]
                height = last_pose_data["height"]

                current_time = time.time()
                fps = 1.0 / (current_time - prev_time)
                prev_time = current_time

                if None in (pitch, roll, yaw, height):
                    continue

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
                data = {
                    "data_sent": False,
                    "axis": axis,
                    "blossom_data": {"x": x, "y": y, "z": z, "h": h},
                    "height": height,
                    "fps": fps
                }
                if should_send:
                    data['data_sent'] = True

                self.visualization.update(frame_display, None, None, data)  # face/pose_results não usados
                self.visualization.add_overlay()
                cv2.imshow(self.cam_view_title, frame_display)
                if cv2.waitKey(1) & 0xFF == 27:
                    self.system_logger("[Mimetic] ESC pressed")
                    self.running = False
                    break
                try:
                    if cv2.getWindowProperty(self.cam_view_title, cv2.WND_PROP_VISIBLE) < 1:
                        self.system_logger("[Mimetic] Window Closed")
                        break
                except cv2.error:
                    break
                # Optional logging
                self.pose_logger(data)

                if should_send:
                    try:
                        blossom_sender_thread.send(payload)
                    except Exception as e:
                        self.system_logger(f"[Mimetic] Error sending to Blossom: {e}", level="error")
                frame_elapsed_time = time.time() - frame_start_time
                sleep_time = max(0.0, frame_duration - frame_elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            self.system_logger("[Mimetic] Ctrl+C detected.", level="info")
            self.running = False

        finally:
            self.system_logger("[Mimetic] Shutting down...", level="info")
            capture_thread.stop()
            capture_thread.join(timeout=2)
            blossom_sender_thread.stop()
            blossom_sender_thread.join(timeout=2)
            recorder_thread.stop()
            recorder_thread.join(timeout=2)
            mp_thread.stop()
            mp_thread.join(timeout=2)
            self.recorder.stop_recording()
            self.pose_logger.save_log()
            if isinstance(self.system_logger, Logger):
                self.system_logger.save_log()
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass

    @staticmethod
    def compact_timestamp() -> str:
        now = datetime.now()
        return now.strftime("%Y%m%d-%H%M%S") + f"{int(now.microsecond / 1000):03d}"


import argparse


def parse_args():
    """
    Parses command line arguments for the Mimetic application.
    :return: Parsed arguments as a Namespace object.
    :rtype: argparse.Namespace
    """
    parser = argparse.ArgumentParser(description="Mimetic Pose Estimation and Recording Tool")
    parser.add_argument("--output_folder", type=str, default="recordings", help="Folder to save recordings")
    parser.add_argument("--study_id", type=str, default=None, help="Study ID for the recording")
    parser.add_argument("--host", type=str, default="localhost", help="Blossom server host")
    parser.add_argument("--port", type=int, default=8000, help="Blossom server port")
    parser.add_argument("--mirror_video", type=str, default="true", help="Mirror video (true/false)")
    parser.add_argument("--print_to_terminal", type=str, default="true", help="Print logs to terminal (true/false)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    mimetic = Mimetic(
        output_folder=args.output_folder,
        study_id=args.study_id,
        host=args.host,
        port=args.port,
        mirror_video=(args.mirror_video.lower() == "true"),
        print_to_terminal=(args.print_to_terminal.lower() == "true")
    )
    mimetic.main()
    print("[Mimetic] Application finished.")
    print("[Mimetic] All threads stopped and resources released.")
    print("[Mimetic] Data saved to:", f"{args.output_folder}/{mimetic.study_id}/")