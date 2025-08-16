import json
import subprocess
import time
from pathlib import Path
from typing import Literal

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
from src.threads.blossom_server_launcher import BlossomServerLauncher
from src.threads.calibrate_thread import CalibrateThread
from src.threads.frame_capture import FrameCaptureThread
from src.threads.mimetic_thread import MimeticRunnerThread
from src.threads.recorder_thread import RecorderThread
from src.utils import compact_timestamp, get_local_ip


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()

        self._last_gaze_label = None
        self.mimetic_server_process = None
        self.setupUi(self)
        self.setWindowTitle("Blossom LASIGE Research")
        self.timer = QTimer()

        self.settings_mgr = SettingManager()
        self.settings = self.settings_mgr.load()

        self.output_directory = self.settings.output_directory
        self.study_id = self.settings.study_id or compact_timestamp()
        self.logger = Logger(f"{self.output_directory}/{self.study_id}/system_log.json", mode="system")
        self.host = self.settings.host or get_local_ip()
        self.mimetic_port = self.settings.mimetic_port
        self.dancer_port = self.settings.dancer_port
        self.mirror_video = self.settings.mirror_video
        self.flip_blossom = self.settings.flip_blossom

        self.capture_thread = FrameCaptureThread(logger=self.logger)
        self.capture_thread.start()

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.load_logs_to_textedit) # type: ignore
        self.log_timer.start(200)
        self._last_log_index = 0

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

        self.mimetic = Mimetic(
            study_id=self.study_id,
            host=self.host,
            port=self.mimetic_port,
            mirror_video=self.mirror_video,
            output_directory=self.output_directory,
            capture_thread=self.capture_thread,
            logger={
                "system": self.logger,
                "pose": None
            },
            left_threshold=self.settings.left_threshold, right_threshold=self.settings.right_threshold,
        )
        self.mimetic_thread = None
        self.calib_thread = None
        self.main()
        self.recorder_thread = None

        self._log_pos = 0

        self.dancer = Dancer()
        self.is_dancing = False
        self.is_mimicking = False
        self.logger.set_system_log_level("debug")

    def main(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_frame) # type: ignore
        self.timer.start(30)

        self.pose_button.clicked.connect(self.toggle_pose_recognition)
        self.calibrate_pose_button.clicked.connect(self.calibrate_pose)
        self.recording_button.clicked.connect(self.toggle_recording)
        self.mimetic_button.clicked.connect(self.toggle_mimetic_blossom)
        self.reset_mimetic.clicked.connect(lambda: self.toggle_mimetic_blossom(action="reset"))
        self.dancer_button.clicked.connect(self.toggle_dancer_blossom)
        self.reset_dancer.clicked.connect(lambda: self.toggle_dancer_blossom(action="reset"))
        self.menu_settings_button.triggered.connect(self.open_settings)
        self.menu_exit_button.triggered.connect(self.close)

    def open_settings(self):
        if self.mimetic.running or (self.recorder_thread and self.recorder_thread.running):
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

        self.mirror_video = new.mirror_video
        self.flip_blossom = new.flip_blossom
        changed_output_directory = (old.output_directory != new.output_directory)

        try:
            self.mimetic.update_threshold(new.left_threshold, new.right_threshold)
        except Exception as e:
            self.logger(f"Failed to apply thresholds: {e}", level="error")

        self.host = new.host
        self.mimetic_port = new.mimetic_port
        self.mimetic.port = new.mimetic_port
        self.mimetic.host = new.host

        self.dancer_port = new.dancer_port
        self.dancer.port = new.dancer_port
        self.dancer.host = new.host

        if changed_output_directory:
            self.logger("Reconfiguring output directory...", level="info")
            self.logger(f"creating output directory at {new.output_directory}", level="debug")
            subprocess.run(["mkdir", "-p", new.output_directory])
            self.logger(f"Moving... 'mv {self.output_directory}/{self.study_id} {new.output_directory}'", level="debug")
            subprocess.run(["mv", f"{self.output_directory}/{self.study_id}", new.output_directory])
            self.output_directory = new.output_directory
            self.logger("Updating pose logging directory...", level="debug")
            self.mimetic.update_output_directory(new.output_directory)
            self.logger(f"Output directory successfully changed to {self.output_directory}/{self.study_id}", level="info")
            self.logger.output_path = f"{self.output_directory}/{self.study_id}/system_log.json"


        if self.recorder_thread and self.recorder_thread.running:
            self.logger("Output folder changed; will apply to the next recording.", level="warning")

        self.logger("Settings applied.", level="info")

    def update_video_frame(self):
        frame = self.capture_thread.get_frame(mirror_video=self.settings.mirror_video)
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
        if self.capture_thread:
            self.capture_thread.stop()
            self.capture_thread.join()
        if self.mimetic.running:
            self.mimetic.stop()
            self.mimetic_thread.stop()
            self.mimetic_thread.wait()

        if self.recorder_thread and self.recorder_thread.running:
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
        self.logger(f"Calibration failed: {error_msg}", level="error")
        self.calibrate_pose_button.setEnabled(True)
        self.calibrate_pose_button.setText("Calibrate")

    def toggle_pose_recognition(self):
        def start_pose_recognition():
            self.mimetic_thread = MimeticRunnerThread(self.mimetic)
            self.mimetic_thread.data_updated.connect(self.update_mimetic_data)
            if self.mimetic.running:
                self.logger("Pose recognition already running", level="warning")
                return
            self.logger("Starting Pose Recognition...", level="info")
            self.mimetic.start()
            self.mimetic_thread.start()
            self.pose_button.setText("Stop Pose Recognition")

        def stop_pose_recognition():
            if not self.mimetic.running:
                self.logger("Pose recognition already stopped", level="warning")
                return
            self.logger("Stopping Pose Recognition...", level="info")
            if self.mimetic.is_sending:
                self.mimetic.stop_sending()
            self.mimetic.stop()
            self.mimetic_thread.stop()
            self.pose_button.setText("Start Pose Recognition")


        if not self.mimetic.running:
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

        if gaze and self.mimetic.running:

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
        self.data_sent.setChecked(bool(data_sent))

    def launch_blossom(self, blossom_type: str):
        attr = f"{blossom_type}_launcher"
        proc_attr = f"{blossom_type}_server_process"

        if hasattr(self, attr) and getattr(self, attr).isRunning():
            self.logger(f"{blossom_type.capitalize()} Blossom server is already starting or running.", level="warning")
            return

        launcher = BlossomServerLauncher(host=self.host, ports={"mimetic": self.mimetic_port, "dancer": self.dancer_port},
                                         logger=self.logger, blossom_type=blossom_type)
        setattr(self, attr, launcher)

        def on_ready():
            if launcher.success:
                self.logger(f"{blossom_type.capitalize()} Blossom server started successfully.")
                setattr(self, proc_attr, launcher.server_proc)
                if blossom_type == "mimetic":
                    self.logger("Mimetic Blossom server is ready. Starting sender thread.", level="info")
                    self.mimetic.start_sending()

            else:
                if hasattr(self, "mimetic_launcher") and self.mimetic_launcher.init_allowed:
                    self.logger(f"Failed to start {blossom_type.capitalize()} Blossom server.", level="error")

        launcher.finished.connect(on_ready)
        launcher.start()

    def send_blossom_command(self, blossom_type: str, command: str):
        proc = getattr(self, f"{blossom_type}_server_process", None)

        if proc is None or proc.stdin is None or proc.poll() is not None:
            self.logger(f"Cannot send command: {blossom_type.capitalize()} server not running or stdin closed.",
                        level="error")
            return

        try:
            proc.stdin.write((command + "\n").encode())
            proc.stdin.flush()
            self.logger(f"Sent '{command}' to {blossom_type.capitalize()} Blossom server.")
        except Exception as e:
            self.logger(f"Failed to send '{command}' to {blossom_type.capitalize()}: {e}", level="error")

    def toggle_mimetic_blossom(self, action: Literal["start", "stop", "reset"] = None):

        m = self.mimetic

        def start():
            self.is_mimicking = True
            self.launch_blossom("mimetic")
            self.mimetic_button.setText("Stop Mimetic")

        def stop():
            self.is_mimicking = False

            if hasattr(self, "mimetic_launcher") and self.mimetic_launcher.isRunning():
                self.logger("Cancelling Mimetic Blossom server initialization...", level="info")
                self.mimetic_launcher.init_allowed = False
                if self.mimetic_launcher.success:
                    m.stop_sending()
                    self.send_blossom_command("mimetic", "q")

            if self.mimetic_server_process:
                self.mimetic_server_process.terminate()
                self.mimetic_server_process = None

            self.mimetic_button.setText("Start Mimetic")

        def reset():
            if self.is_mimicking:
                self.logger(f"Resetting Mimetic Blossom server...", level="debug")
                if self.mimetic.is_sending:
                    self.logger("Sending reset command and stopping blossom sending process", level="debug")
                    self.send_blossom_command("mimetic", "reset")
                    m.stop_sending()
                QTimer.singleShot(100, stop)

        if action == "start":
            start()
        elif action == "stop":
            stop()
        elif action == "reset":
            reset()
        else:
            (stop if self.is_mimicking else start)()

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
            if not self.recorder_thread or not self.recorder_thread.running:
                self.logger("Recording is already stopped.", level="warning")
                return
            self.logger("Stopping recording...", level="info")
            self.recorder_thread.stop()
            self.recorder_thread.join()
            self.recording_button.setText("Start Rec.")
            self.recorder_thread = None

        if self.recorder_thread and self.recorder_thread.running:
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
            self.logger(f"Failed to read logs: {e}", level="error")
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
            self.terminal_output.append(html_line)

        if at_bottom:
            self.terminal_output.moveCursor(self.terminal_output.textCursor().MoveOperation.End)
            self.terminal_output.ensureCursorVisible()

    def toggle_dancer_blossom(self, action: Literal["start", "stop", "reset"] = None):
        def start():
            self.logger("Starting dancer...", level="info")
            QTimer.singleShot(100, lambda: self.launch_blossom("dancer"))
            self.dancer.start()
            self.is_dancing = True
            self.dancer_button.setText("Stop Dancer")

        def stop():
            if not self.dancer.running:
                self.logger("Dancer already stopped", level="warning")
                return
            self.logger("Stopping Dancer...", level="info")

            self.dancer.stop()
            self.is_dancing = False
            self.dancer_button.setText("Start Dancer")
            self.send_blossom_command("dancer", "q")

        def reset():
            self.send_blossom_command("dancer", "reset")
            QTimer.singleShot(100, lambda: stop())

        if action == "start":
            start()
        elif action == "stop":
            stop()
        elif action == "reset":
            reset()
        else:
            (stop if self.is_dancing else start)()