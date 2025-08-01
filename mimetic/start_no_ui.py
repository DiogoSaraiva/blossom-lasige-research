import threading
import time
from typing import Tuple

import numpy as np

from mimetic.src.motion_limiter import MotionLimiter
from mimetic.src.pose_buffer import PoseBuffer
from mimetic.src.threads.blossom_sender import BlossomSenderThread
from mimetic.src.threads.mediapipe_thread import MediaPipeThread
from src.config import get_local_ip
from src.logging_utils import Logger, print_logger
from src.threads.frame_capture import FrameCaptureThread
from src.utils import compact_timestamp


class Mimetic:
    def __init__(self, output_folder: str, study_id: str or int, host: str, port: int, mirror_video: bool,
                 capture_thread: FrameCaptureThread, logger: {Logger, Logger},
                 blossom_sender: BlossomSenderThread = None):
        self._stop_event = threading.Event()
        self._thread = None
        self.output_folder = output_folder or "./output"
        self.study_id = study_id or compact_timestamp()
        self.logger = logger.get("system") if logger and logger.get("system") is not None else print_logger
        self.pose_logger = (
            logger.get("pose")
            if logger and logger.get("pose") is not None
            else Logger(f"{output_folder}/{self.study_id}/pose_log.json", mode="pose")
        )
        self.host = host or get_local_ip()
        self.port = port
        self.mirror_video = mirror_video or True
        self.capture_thread = capture_thread or FrameCaptureThread(logger=self.logger)
        self.limiter = MotionLimiter(logger=self.logger)
        self.pose_buffer = PoseBuffer(logger=self.logger)
        self.cam_view_title = "Pose Estimation " + " (Mirrored)" if mirror_video else ""
        self.running = False
        self.angle_offset = {"pitch": 0, "roll": 0, "yaw": 0}
        self.blossom_sender_thread = blossom_sender or BlossomSenderThread(host=self.host, port=self.port,
                                                                           logger=self.logger)
        self.mp_thread = None
        self.is_sending = False
        self.data = {}

    def _main_loop(self):
        self.running = True
        last_pose_data = None

        prev_time = time.time()

        target_fps = 30
        frame_duration = 1.0 / target_fps
        frame_width, frame_height = self.initialize()



        try:
            while not self._stop_event.is_set():
                frame_start_time = time.time()

                # Reduced resolution for MediaPipe
                frame_mp = self.capture_thread.get_frame(mirror_video=self.mirror_video, width=min(320, frame_width) ,height=min(180, frame_height))
                if frame_mp is None:
                    continue
                self.mp_thread.send(frame_mp)

                # Read results from buffer
                pose_data, _ = self.pose_buffer.get_latest_pose_data()

                if pose_data is None:
                    self.logger("[Main] No pose data received yet", level="debug")
                    time.sleep(0.01)
                    continue

                if pose_data is not None:
                    last_pose_data = pose_data

                if last_pose_data is None:
                    continue  # wait until the first pose is available

                pitch = last_pose_data["pitch"]
                roll = last_pose_data["roll"]
                yaw = last_pose_data["yaw"]
                height = last_pose_data["height"]

                current_time = time.time()
                fps = 1.0 / (current_time - prev_time)
                prev_time = current_time

                if None in (pitch, roll, yaw, height):
                    continue

                pitch -= self.angle_offset["pitch"]
                roll -= self.angle_offset["roll"]
                yaw -= self.angle_offset["yaw"]

                pitch = np.clip(pitch, -30, 30)
                roll = np.clip(roll, -30, 30)
                yaw = np.clip(yaw, -30, 30)

                # Smooth pose values
                x = np.radians(self.limiter.smooth('x', pitch))
                y = np.radians(self.limiter.smooth('y', roll))
                z = np.radians(self.limiter.smooth('z', yaw))
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
                self.data = {
                    "data_sent": False,
                    "axis": axis,
                    "blossom_data": {"x": x, "y": y, "z": z, "h": h, "e": e},
                    "height": height,
                    "fps": fps
                }
                if should_send:
                    self.data['data_sent'] = True

                self.pose_logger(self.data)

                # Send data to Blossom if needed
                if self.is_sending and should_send:
                    try:
                        self.blossom_sender_thread.send(payload)
                    except Exception as e:
                        self.logger(f"[Mimetic] Error sending to Blossom: {e}", level="error")
                frame_elapsed_time = time.time() - frame_start_time
                sleep_time = max(0.0, frame_duration - frame_elapsed_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            import traceback
            self.logger(f"[Mimetic] Exception in main loop: {e} \n {traceback.format_exc()}", level="critical")

        finally:
            self.running = False


    def start_sending(self):
        if self.is_sending:
            self.logger("[Mimetic] Sending already enabled.", level="warning")
            return
        self.blossom_sender_thread = BlossomSenderThread(host=self.host, port=self.port, logger=self.logger)
        self.blossom_sender_thread.start()
        self.is_sending = True

    def stop_sending(self):
        if not self.is_sending:
            self.logger(f"[Mimetic] Sending not enabled.", level="warning")
            return
        self.is_sending = False
        self.blossom_sender_thread.stop()


    def initialize(self) -> Tuple[int, int]:
        timeout_sec = 5
        interval_sec = 0.01
        max_attempts = int(timeout_sec / interval_sec)

        for _ in range(max_attempts):
            frame_display = self.capture_thread.get_frame(mirror_video=True)
            if frame_display is not None and frame_display.size > 0:
                break
            time.sleep(interval_sec)
        else:
            raise RuntimeError("Failed to capture initial frame within timeout.")

        frame_height, frame_width = frame_display.shape[:2]
        self.logger(f"[INFO] Detected camera with resolution: {frame_width}x{frame_height}")

        self.mp_thread = MediaPipeThread(result_buffer=self.pose_buffer, logger=self.logger)
        self.mp_thread.start()
        return frame_width, frame_height

    def calibrate_pose(self):
        if self.mp_thread is None:
            self.logger("[Mimetic] Cannot calibrate: MediaPipe thread is not initialized.", level="error")
            return

        # --- Angle calibration (pitch, roll, yaw) ---
        calib_frames = []
        calib_duration_sec = 2.0
        start_calib = time.time()
        self.logger("[Mimetic] Calibrating pose... Hold you head neutral and remain still.", level="info")

        while (time.time() - start_calib < calib_duration_sec) and len(calib_frames) < 10:
            frame = self.capture_thread.get_frame(mirror_video=self.mirror_video)
            if frame is None:
                continue
            self.mp_thread.send(frame)
            pose_data, _ = self.pose_buffer.get_latest_pose_data()
            if pose_data is not None:
                calib_frames.append((pose_data["pitch"], pose_data["roll"], pose_data["yaw"]))
            time.sleep(0.01)

        if calib_frames:
            pitches, rolls, yaws = zip(*calib_frames)
            self.angle_offset = {
                "pitch": np.mean(pitches),
                "roll": np.mean(rolls),
                "yaw": np.mean(yaws)
            }
            self.logger(
                f"[Mimetic] Calibration complete:\n"
                f" pitch offset = {self.angle_offset['pitch']:.2f}°\n"
                f" roll  offset = {self.angle_offset['roll']:.2f}°\n"
                f" yaw   offset = {self.angle_offset['yaw']:.2f}°",
                level="info"
            )
        else:
            raise RuntimeError("Failed calibration: No valid frame captured.")

    def start(self):
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._main_loop, daemon=True)
            self._thread.start()
            self.logger("[Mimetic] Thread started.", level="info")
        else:
            self.logger("[Mimetic] Start called, but already running.", level="warning")

    def stop(self):
        self.logger("[Mimetic] Stopping...", level="info")
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join()
        self.running = False
        if self.mp_thread:
            self.mp_thread.stop()
            self.mp_thread.join()
        if self.blossom_sender_thread.is_alive():
            self.blossom_sender_thread.stop()
            self.blossom_sender_thread.join()