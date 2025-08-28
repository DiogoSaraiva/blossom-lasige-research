import json
import subprocess
import time
from pathlib import Path
from typing import Literal, Optional

# noinspection PyPackageRequirements
import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from dancer.dancer import Dancer
from mimetic.mimetic import Mimetic
from src.logging_utils import Logger
from src.main_window_ui import Ui_MainWindow
from src.settings import Settings, SettingManager
from src.settings_dialog import SettingsDialog
from src.threads.blossom_sender import BlossomSenderThread
from src.threads.blossom_server_launcher import BlossomServerLauncher
from src.threads.calibrate_thread import CalibrateThread
from src.threads.frame_capture import FrameCaptureThread
from src.threads.mimetic_thread import MimeticRunnerThread
from src.threads.recorder_thread import RecorderThread
from src.utils import compact_timestamp, get_local_ip

LOG_LEVEL = "debug"

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self._last_log_msg = None
        self.setupUi(self)
        self.blossom_one_type.currentTextChanged.connect(lambda: self.on_blossom_type_changed("one"))
        self.blossom_two_type.currentTextChanged.connect(lambda: self.on_blossom_type_changed("two"))

        self._last_gaze_label = None

        self.blossom_one_active = False
        self.blossom_two_active = False
        self.blossom_one_server_process = None
        self.blossom_two_server_process = None
        self.blossom_one_launcher = None
        self.blossom_two_launcher = None

        self.setWindowTitle("Blossom LASIGE Research")
        self.timer = QTimer()

        self.settings_mgr = SettingManager()
        self.settings = self.settings_mgr.load()

        self.output_directory = self.settings.output_directory

        self.study_id = self.settings.study_id or compact_timestamp()
        self.logger = Logger(f"{self.output_directory}/{self.study_id}/system_log.json", mode="system")
        self.host = self.settings.host or get_local_ip()
        self.mirror_video = self.settings.mirror_video
        self.flip_blossoms = self.settings.flip_blossoms

        self.capture_thread = FrameCaptureThread(logger=self.logger)
        self.capture_thread.start()

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.load_logs_to_textedit) # type: ignore
        self.log_timer.start(200)
        self._last_log_index = 0

        self.blossom_one_port = self.settings.blossom_one_port
        self.blossom_two_port = self.settings.blossom_two_port

        self.alpha_map = self.settings.alpha_map
        self.multiplier_map = self.settings.multiplier_map
        self.limit_map = self.settings.limit_map
        self.send_rate = self.settings.send_rate
        self.send_threshold = self.settings.send_threshold


        max_wait = 5
        start_time = time.time()
        while time.time() - start_time < max_wait:
            frame = self.capture_thread.get_frame(mirror_video=self.mirror_video)
            if frame is not None:
                self.frame_height, self.frame_width = frame.shape[:2]
                break
        else:
            self.logger("Failed to retrieve frame resolution in time.", level="error")
            self.frame_height, self.frame_width = 480, 640  # fallback default

        self.blossom_one_sender = None
        self.blossom_two_sender = None

        self.mimetic_thread = None
        self.calib_thread = None

        self.timer.timeout.connect(self.update_video_frame)  # type: ignore
        self.timer.start(30)

        self.pose_button.clicked.connect(self.toggle_pose_recognition)
        self.calibrate_pose_button.clicked.connect(self.calibrate_pose)
        self.recording_button.clicked.connect(self.toggle_recording)
        self.blossom_one_button.clicked.connect(lambda: self.toggle_blossom(number="one"))
        self.blossom_two_button.clicked.connect(lambda: self.toggle_blossom(number="two"))
        self.reset_blossom_one.clicked.connect(lambda: self.toggle_blossom(number="one", action="reset"))
        self.reset_blossom_two.clicked.connect(lambda: self.toggle_blossom(number="two", action="reset"))
        self.menu_settings_button.triggered.connect(self.open_settings)
        self.menu_exit_button.triggered.connect(self.close)

        self.recorder_thread = None

        self._log_pos = 0

        self.logger.set_system_log_level(LOG_LEVEL)

        self.mimetic = Mimetic(
            study_id=self.study_id,
            mirror_video=self.mirror_video,
            output_directory=self.output_directory,
            capture_thread=self.capture_thread,
            logger={
                "system": self.logger,
                "pose": None
            },
            left_threshold=self.settings.left_threshold, right_threshold=self.settings.right_threshold,
            alpha_map=self.alpha_map,
            multiplier_map=self.multiplier_map,
            limit_map=self.limit_map,
            send_rate=self.send_rate,
            send_threshold=self.send_threshold,
            flip_blossom=self.flip_blossoms,
        )

        self.dancer_mode = self.settings.dancer_mode
        self.analysis_interval = self.settings.analysis_interval
        self.mic_sr = self.settings.mic_sr
        self.music_directory = self.settings.music_directory

        self.dancer = Dancer(
            logger=self.logger,
            mode="mic" if self.dancer_mode == "mic" else "audio",
            analysis_interval=self.analysis_interval,
            mic_sr=self.mic_sr,
            music_dir=self.music_directory,
        )
        self.mimetic.update_sender("one", self.blossom_one_sender)

    def on_blossom_type_changed(self, number: Literal["one", "two"]):
        new_type = self.get_blossom_type(number)
        sender = getattr(self, f"blossom_{number}_sender", None)
        if sender:
            sender.mode = new_type
        self.logger(f"[Main] Blossom {number} type set to '{new_type}'.", level="debug")
        sender = getattr(self, f"blossom_{number}_sender", None)
        if new_type == "mimetic":
            self.mimetic.update_sender(number, sender)
        else :
            self.mimetic.update_sender(number, None)

    def get_blossom_type(self, number: Literal["one", "two"]) -> Literal["mimetic", "dancer"]:
        combo = getattr(self, f"blossom_{number}_type", None)
        value = combo.currentText().strip().lower() if combo else None
        if value in ("mimetic", "dancer"):
            return value
        raise ValueError(f"Invalid Blossom Type: '{value}'")

    def get_controller_for_mode(self, mode: Literal["mimetic", "dancer"]) -> Optional[Mimetic | Dancer]:
        if mode == "mimetic":
            return self.mimetic
        if mode == "dancer":
            return self.dancer

    def open_settings(self):
        if (self.mimetic.is_running or self.blossom_one_active or self.blossom_two_active or
                (self.recorder_thread and self.recorder_thread.is_running)):
            QMessageBox.warning(
                self,
                "Settings Locked",
                "Cannot apply settings while any tools are running.\n"
                "Please stop them first."
            )
            self.logger("Attempted to change settings while tools were running. Ignored.", level="warning")
            return
        dlg = SettingsDialog(self.settings, self)
        dlg.settings_applied.connect(self.apply_settings)
        dlg.exec()

    def apply_settings(self, new: Settings):
        old = self.settings
        self.settings = new
        self.settings_mgr.save(new)

        changed_study_id = (old.study_id != new.study_id)
        changed_output_directory = (old.output_directory != new.output_directory)
        changed_thresholds = old.left_threshold != new.left_threshold or old.right_threshold != new.right_threshold
        changed_alpha_map = old.alpha_map != new.alpha_map
        changed_multiplier_map = old.multiplier_map != new.multiplier_map
        changed_limit_map = old.limit_map != new.limit_map
        changed_send_rate = old.send_rate != new.send_rate
        changed_send_threshold = old.send_threshold != new.send_threshold
        changed_mirror_video = old.mirror_video != new.mirror_video
        changed_flip_blossoms = old.flip_blossoms != new.flip_blossoms
        changed_host = (old.host != new.host)
        changed_blossom_one_port = (old.blossom_one_port != new.blossom_one_port)
        changed_blossom_two_port = (old.blossom_two_port != new.blossom_two_port)
        changed_blossom_one_endpoint = changed_host or changed_blossom_one_port
        changed_blossom_two_endpoint = changed_host or changed_blossom_two_port
        changed_music_directory = (old.music_directory != new.music_directory)

        if changed_thresholds:
            try:
                self.mimetic.update_threshold(new.left_threshold, new.right_threshold)
                self.logger(f"[Main] Updated for new thresholds: {new.left_threshold}, {new.right_threshold}", level="info")
            except Exception as e:
                self.logger(f"[Main] Failed to apply thresholds: {e}", level="error")

        if changed_alpha_map or changed_multiplier_map or changed_limit_map or changed_send_rate or changed_send_threshold:
            self.mimetic.limiter.alpha_map = new.alpha_map
            self.mimetic.limiter.send_rate = new.send_rate
            self.mimetic.limiter.send_threshold = new.send_threshold
            self.mimetic.limiter.multiplier_map = new.multiplier_map
            self.mimetic.limiter.limit_map = new.limit_map
            self.logger(f"[Main] Updated for new mimetic motion limiter values.", level="info")


        if changed_music_directory:
            self.mimetic.music_directory = new.music_directory

        if changed_study_id:
            self.study_id = new.study_id
            self.terminal_output.clear()
            self._log_pos = 0
            self._last_log_msg = None
            self.logger = Logger(output_path=f"{self.output_directory}/{self.study_id}/system_log.json", mode="system", level=LOG_LEVEL)
            self.capture_thread.logger = self.logger

        if changed_host:
            self.host = new.host
            self.logger(f"[Main] Updated for new host: {new.host}", level="info")

        one_type = self.get_blossom_type("one")
        two_type = self.get_blossom_type("two")
        blossom_one_attr = self.get_controller_for_mode(one_type)
        blossom_two_attr = self.get_controller_for_mode(two_type)

        if changed_blossom_one_endpoint:
            self.blossom_one_port = new.blossom_one_port
            if blossom_one_attr and hasattr(blossom_one_attr, "port"):
                blossom_one_attr.port = new.blossom_one_port
            self.logger(f"[Main] Changed to new {one_type} endpoint: {new.host}:{new.blossom_one_port}", level="info")

        if changed_blossom_two_endpoint:
            self.blossom_two_port = new.blossom_two_port
            if blossom_two_attr and hasattr(blossom_two_attr, "port"):
                blossom_two_attr.port = new.blossom_two_port
            self.logger(f"[Main] Changed to new {two_type} endpoint: {new.host}:{new.blossom_two_port}", level="info")

        if changed_output_directory:
            subprocess.run(["mkdir", "-p", new.output_directory])
            self.logger(f"[Main] created output directory at {new.output_directory}", level="debug")
            subprocess.run(["mv", f"{self.output_directory}/{self.study_id}", new.output_directory])
            self.logger(f"[Main] Moved.. 'mv {self.output_directory}/{self.study_id} {new.output_directory}'", level="debug")
            self.output_directory = new.output_directory
            self.mimetic.update_output_directory(new.output_directory)
            self.logger("[Main] Updated pose logging directory...", level="debug")
            self.logger(f"[Main] Output directory successfully changed to {self.output_directory}/{self.study_id}", level="info")
            self.logger.output_path = f"{self.output_directory}/{self.study_id}/system_log.json"

        if changed_flip_blossoms:
            self.flip_blossoms = new.flip_blossoms
            self.mimetic.flip_blossoms = new.flip_blossoms
            self.logger(f"[Main] Updated for new flip_blossoms setting: {new.flip_blossoms}", level="info")

        if changed_mirror_video:
            self.mirror_video = new.mirror_video
            self.logger(f"[Main] Changed to new mirror_video setting: {new.mirror_video}", level="info")

        if (changed_blossom_one_endpoint or changed_blossom_two_endpoint or changed_output_directory or changed_flip_blossoms or
            changed_mirror_video or changed_thresholds or changed_alpha_map or changed_send_threshold or changed_send_rate or
            changed_study_id or changed_music_directory or changed_multiplier_map or changed_limit_map):
            self.logger("[Main] Settings applied.", level="info")
        else:
            self.logger("[Main] No changes to be applied.", level="info")

    def update_video_frame(self):
        frame = self.capture_thread.get_frame(mirror_video=self.mirror_video)
        if frame is None:
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(
            self.cam_feed.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.cam_feed.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        if self.blossom_one_sender:
            self.toggle_blossom(action="reset", number="one")
        if self.blossom_two_sender:
            self.toggle_blossom(action="reset", number="two")
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.join()
        if self.mimetic and self.mimetic.is_running:
            self.mimetic.stop()
        if self.mimetic_thread:
            self.mimetic_thread.stop()
            self.mimetic_thread.wait()
        if self.dancer and self.dancer.is_running:
            self.dancer.stop()

        if self.recorder_thread and self.recorder_thread.is_running:
            self.recorder_thread.stop()
            self.recorder_thread.join()
        event.accept()

    def calibrate_pose(self):
        self.calib_thread = CalibrateThread(self.mimetic)
        self.calibrate_pose_button.setEnabled(False)
        self.calibrate_pose_button.setText("Calibrating")

        self.calib_thread.start()
        self.calib_thread.finished_ok.connect(self.calibration_success)
        self.calib_thread.failed.connect(self.calibration_failed)

    def calibration_success(self):
        self.calibrate_pose_button.setEnabled(True)
        self.calibrate_pose_button.setText("Calibrate")

    def calibration_failed(self, error_msg: str):
        self.logger(f"[Main] Calibration failed: {error_msg}", level="error")
        self.calibrate_pose_button.setEnabled(True)
        self.calibrate_pose_button.setText("Calibrate")

    def toggle_pose_recognition(self):
        def start_pose_recognition():
            self.mimetic_thread = MimeticRunnerThread(self.mimetic)
            self.mimetic_thread.data_updated.connect(self.update_mimetic_data)
            if self.mimetic.is_running:
                self.logger("Pose recognition already running", level="warning")
                return
            self.logger("[Main] Starting Pose Recognition...", level="info")
            self.mimetic.start()
            self.mimetic_thread.start()
            self.pose_button.setText("Stop Pose Recognition")

        def stop_pose_recognition():
            if not self.mimetic.is_running:
                self.logger("[Main] Pose recognition already stopped", level="warning")
                return
            self.logger("[Main] Stopping Pose Recognition...", level="info")
            if self.mimetic.is_sending_one or self.mimetic.is_sending_two:
                if self.get_blossom_type("one") == "mimetic":
                    self.mimetic.stop_sending(blossom_sender=self.blossom_one_sender, number="one")

                if self.get_blossom_type("two") == "mimetic":
                    self.mimetic.stop_sending(blossom_sender=self.blossom_two_sender, number="two")
            self.mimetic.stop()
            self.mimetic_thread.stop()
            self.mimetic_thread.wait()
            self.pose_button.setText("Start Pose Recognition")


        if not self.mimetic.is_running:
            start_pose_recognition()
        else:
            stop_pose_recognition()

    def update_mimetic_data(self, data: dict):
        indicators = {
            "left": self.left_indicator,
            "center": self.center_indicator,
            "right": self.right_indicator
        }

        def update_gaze_indicator(label: str = None):

            clear_gaze_indicator()

            if label in indicators:
                indicators[label].setChecked(True)

            self._last_gaze_label = label

        def clear_gaze_indicator():
            for indicator in indicators.values():
                indicator.setChecked(False)

        def format_val(val: float, suffix: str = '') -> str:
            return f"{val:.2f}{suffix}" if val is not None else "--"

        gaze = data.get('gaze')

        if gaze and self.mimetic.is_running:

            gaze_label = gaze.get("label", None)

            gaze_ratio = gaze.get("ratio", None)

            if gaze_label != self._last_gaze_label:
                update_gaze_indicator(gaze_label)
        else:
            clear_gaze_indicator()
            self._last_gaze_label = None

        axis = data.get("axis")
        if axis is not None:
            pitch, roll, yaw = axis.get("pitch"), axis.get("roll"), axis.get("yaw")
        else:
            pitch = roll = yaw = None

        self.pose_pitch_value.setText(format_val(pitch, 'º'))
        self.pose_roll_value.setText(format_val(roll, 'º'))
        self.pose_yaw_value.setText(format_val(yaw, 'º'))

        self.pose_height_value.setText(format_val(data.get("height")))

        blossom_data = data.get("blossom_data")

        if blossom_data is not None:
            x = blossom_data.get("x")
            y = blossom_data.get("y")
            z = blossom_data.get("z")
            h = blossom_data.get("h")
            e = blossom_data.get("e")

        else:
            x = y = z = h = e = None
        data_sent = data.get("data_sent", False)

        self.blossom_pitch_value.setText(format_val(x, 'rad'))
        self.blossom_roll_value.setText(format_val(y, 'rad'))
        self.blossom_yaw_value.setText(format_val(z, 'rad'))
        self.blossom_height_value.setText(format_val(h))
        self.blossom_ears_value.setText(format_val(e))
        self.data_sent.setChecked(bool(data_sent) if (self.mimetic.is_sending_one or self.mimetic.is_sending_two) else False)

    def launch_blossom(self, mode: Literal["mimetic", "dancer"], number: Literal["one", "two"]):
        attr = f"blossom_{number}_launcher"
        proc_attr = f"blossom_{number}_server_process"

        if getattr(self, attr) is not None and getattr(self, attr).isRunning():
            self.logger(f"[Main] {mode.capitalize()} Blossom {number.capitalize()} server is already starting or running.", level="warning")
            return
        port = getattr(self.settings, f"blossom_{number}_port")
        device = getattr(self.settings, f"blossom_{number}_device")

        launcher = BlossomServerLauncher(host=self.host, port=port, usb=device,
                                         logger=self.logger, number=number)

        setattr(self, attr, launcher)

        def on_ready():
            blossom_attr = getattr(self, mode, None)
            if launcher.success:
                self.logger(f"[Main] {mode.capitalize()} Blossom server started successfully.")
                setattr(self, proc_attr, launcher.server_proc)
                self.logger(f"[Main] {str(mode).upper()} Blossom {number.capitalize()} server is ready. Starting sender thread.", level="info")
                if blossom_attr: # and hasattr(blossom_attr, "start_sending"):
                    setattr(self, f"blossom_{number}_sender", BlossomSenderThread(host=self.host, port=port, logger=self.logger,
                                        mode=self.get_blossom_type(number)))
                    sender = getattr(self, f"blossom_{number}_sender")
                    blossom_attr.update_sender(blossom_sender=sender, number=number)
                    blossom_attr.start_sending(blossom_sender=sender, number=number)
                else:
                    self.logger(f"[Main] {mode.capitalize()} controller not available to start sending.",
                                level="warning")

            else:
                if hasattr(self, attr) and getattr(self, attr).init_allowed:
                    self.logger(f"[Main] Failed to start {mode.capitalize()} Blossom server.", level="error")

        launcher.finished.connect(on_ready)
        launcher.start()


    def send_blossom_command(self, number: Literal["one", "two"], command: str):
        proc = getattr(self, f"blossom_{number}_server_process")

        if proc is None or proc.stdin is None or proc.poll() is not None:
            self.logger(f"[Main] Cannot send command: Blossom {number.capitalize()} server not running or stdin closed.",
                        level="error")
            return

        try:
            proc.stdin.write((command + "\n").encode())
            proc.stdin.flush()
            self.logger(f"[Main] Sent '{command}' to {number.capitalize()} Blossom server.")
        except Exception as e:
            self.logger(f"[Main] Failed to send '{command}' to {number.capitalize()}: {e}", level="error")

    def toggle_blossom(self, number: Literal["one", "two"], action: Literal["start", "stop", "reset"] = None):
        # Attribute names
        active_attr = f"blossom_{number}_active"
        type_name = self.get_blossom_type(number)
        launcher_attr = f"blossom_{number}_launcher"
        server_proc_attr = f"blossom_{number}_server_process"
        sender_attr = f"blossom_{number}_sender"

        # Objects
        button = getattr(self, f"blossom_{number}_button")
        controller = self.get_controller_for_mode(mode=type_name)
        combo = getattr(self, f"blossom_{number}_type")

        def start():
            combo.setEnabled(False)
            setattr(self, active_attr, True)
            self.launch_blossom(type_name, number)
            button.setText("Stop")  # type: ignore

        def stop():
            setattr(self, active_attr, False)
            if hasattr(self, launcher_attr):
                launcher = getattr(self, launcher_attr)
                if launcher and launcher.isRunning():
                    launcher.init_allowed = False
                    self.logger(f"[Main] Canceled Blossom {number.capitalize()} server initialization....", level="info")
                if getattr(launcher, "success") and controller:
                    sender =  getattr(self, sender_attr)
                    if getattr(controller, f"is_sending_{number}"):
                        controller.stop_sending(blossom_sender=sender, number=number)
                        self.logger(f"[Main] {type_name.capitalize()} sending stopped.", level="info")
                    self.send_blossom_command(number, "q")

                    sender.stop()
                    sender.join()

            self.logger(f"[Main] Blossom {number.capitalize()} server stopped...", level="info")
            setattr(self, sender_attr, None)
            combo.setEnabled(True)

            if hasattr(self, server_proc_attr):
                proc = getattr(self, server_proc_attr)
                if proc:
                    proc.terminate()
                    setattr(self, server_proc_attr, None)

            button.setText("Start")

        def reset():
            if getattr(self, active_attr, False) and controller:
                self.logger(f"[Main] Resetting Blossom {number.capitalize()}...", level="warning")
                # if getattr(controller, "is_sending"):
                self.logger(
                    f"[Main] Sending reset command and stopping blossom {type_name.capitalize()} sending process",
                    level="info"
                )
                self.send_blossom_command(number, "reset")
                QTimer.singleShot(50, stop)
            else:
                self.logger(f"[Main] Blossom {number.capitalize()} server is not active.", level="warning")

        if action == "start":
            start()
        elif action == "stop":
            stop()
        elif action == "reset":
            reset()
        else:
            (stop if getattr(self, active_attr, False) else start)()

    def toggle_recording(self):
        def start_recording():
            self.logger("Starting recording...", level="info")
            self.recording_button.setEnabled(False)
            self.recorder_thread = RecorderThread(output_path=f"{self.output_directory}/{self.study_id}/recording.mp4",
                                                  resolution=(self.frame_width, self.frame_height), fps=30,
                                                  mirror=self.mirror_video, logger=self.logger,
                                                  capture_thread=self.capture_thread)

            self.recorder_thread.start()
            if self.recorder_thread.wait_until_ready(timeout=2):
                self.recording_button.setText("Stop Rec.")
                self.recording_button.setEnabled(True)

        def stop_recording():
            if not self.recorder_thread or not self.recorder_thread.is_running:
                self.logger("Recording is already stopped.", level="warning")
                return
            self.logger("Stopping recording...", level="info")
            self.recorder_thread.stop()
            self.recorder_thread.join()
            self.recording_button.setText("Start Rec.")
            self.recorder_thread = None

        if self.recorder_thread and self.recorder_thread.is_running:
            stop_recording()
        else:
            start_recording()

    def load_logs_to_textedit(self):
        path = Path(self.logger.output_path)
        if not path.exists():
            return

        try:
            size = path.stat().st_size
            if size < self._log_pos:
                self._log_pos = 0

            with open(path, "r", encoding="utf-8") as f:
                f.seek(self._log_pos)
                chunk = f.read()
                self._log_pos = f.tell()
        except Exception as e:
            self.logger(f"[Main] Failed to read logs: {e}", level="error")
            return

        if not chunk:
            return

        lines = chunk.splitlines()
        if not lines:
            return

        scrollbar = self.terminal_output.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        for line in lines:
            try:
                entry = json.loads(line)
            except Exception:
                continue

            timestamp = entry.get("timestamp", "")
            level = str(entry.get("level", "INFO")).upper()
            data = entry.get("data", "")

            msg = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
            msg = msg.replace("\n", "<br>")

            color = {
                "INFO": "#50fa7b",
                "WARNING": "#f1fa8c",
                "ERROR": "#ff5555",
                "DEBUG": "#8be9fd",
                "CRITICAL": "#ff4444",
            }.get(level, "#ffffff")

            html_line = f'<span style="color:{color};">[{timestamp}] [{level}]</span> {msg}'
            if msg != self._last_log_msg:
                self.terminal_output.append(html_line)
                self._last_log_msg = msg

        if at_bottom:
            self.terminal_output.moveCursor(self.terminal_output.textCursor().MoveOperation.End)
            self.terminal_output.ensureCursorVisible()