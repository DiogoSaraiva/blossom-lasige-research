import json
import sys
import time

# noinspection PyPackageRequirements
import cv2
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow

from mimetic.start_no_ui import Mimetic
from src.config import OUTPUT_FOLDER, MIMETIC_PORT, DANCER_PORT, MIRROR_VIDEO, FLIP_BLOSSOM
from src.logging_utils import Logger
from src.main_window_ui import Ui_MainWindow
from src.threads.blossom_server_launcher import BlossomServerLauncher
from src.threads.calibrate_thread import CalibrateThread
from src.threads.frame_capture import FrameCaptureThread
from src.threads.mimetic_thread import MimeticRunnerThread
from src.threads.recorder_thread import RecorderThread
from src.utils import compact_timestamp, get_local_ip


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.mimetic_server_process = None
        self.setupUi(self)
        self.setWindowTitle("Blossom LASIGE Research")
        self.timer = QTimer()

        self.output_folder = OUTPUT_FOLDER
        self.study_id = compact_timestamp()
        self.logger = Logger(f"{self.output_folder}/{self.study_id}/system_log.json", mode="system")
        self.host = get_local_ip()
        self.mimetic_port = MIMETIC_PORT
        self.dance_port = DANCER_PORT
        self.mirror_video = MIRROR_VIDEO
        self.flip_blossom = FLIP_BLOSSOM

        self.capture_thread = FrameCaptureThread(logger=self.logger)
        self.capture_thread.start()

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.load_logs_to_textedit) # type: ignore
        self.log_timer.start(200)
        self.last_log_index = 0

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
            output_folder=self.output_folder,
            capture_thread=self.capture_thread,
            logger={
                "system": self.logger,
                "pose": None
            }
        )
        self.mimetic_thread = None
        self.calib_thread = None
        self.main()
        self.recorder_thread = None

    def main(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_frame) # type: ignore
        self.timer.start(30)



        self.pose_button.clicked.connect(self.toggle_pose_recognition)
        self.calibrate_pose_button.clicked.connect(self.calibrate_pose)
        self.recording_button.clicked.connect(self.toggle_recording)
        self.mimetic_button.clicked.connect(self.start_mimetic_blossom)
        self.reset_mimetic.clicked.connect(self.reset_mimetic_blossom)
        self.dancer_button.clicked.connect(self.start_dancer_blossom)
        self.reset_dancer.clicked.connect(self.reset_dancer_blossom)

    def update_video_frame(self):
        frame = self.capture_thread.get_frame(mirror_video=True)
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
        if not self.mimetic.running:
            self.start_pose_recognition()
        else:
            self.stop_pose_recognition()

    def start_pose_recognition(self):
        self.mimetic_thread = MimeticRunnerThread(self.mimetic)
        self.mimetic_thread.data_updated.connect(self.update_mimetic_data)
        if self.mimetic.running:
            self.logger("Pose recognition already running", level="warning")
            return
        self.logger("Starting Pose Recognition...", level="info")
        self.mimetic.start()
        self.mimetic_thread.start()
        self.pose_button.setText("Stop Pose Recognition")

    def stop_pose_recognition(self):
        if not self.mimetic.running:
            self.logger("Pose recognition already stopped", level="warning")
            return
        self.logger("Stopping Pose Recognition...", level="info")
        if self.mimetic.is_sending:
            self.mimetic.stop_sending()
        self.mimetic.stop()
        self.mimetic_thread.stop()
        self.pose_button.setText("Start Pose Recognition")

    def update_mimetic_data(self, data: dict):
        def format_val(val: float, suffix: str = '') -> str:
            return f"{val:.2f}{suffix}" if val is not None else "--"

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

        launcher = BlossomServerLauncher(logger=self.logger, blossom_type=blossom_type)
        setattr(self, attr, launcher)

        def on_ready():
            if launcher.success:
                self.logger(f"{blossom_type.capitalize()} Blossom server started successfully.")
                setattr(self, proc_attr, launcher.server_proc)

                # lógica extra se for o mimetic
                if blossom_type == "mimetic":
                    self.logger("Mimetic Blossom server is ready. Starting sender thread.", level="info")
                    self.mimetic.start_sending()

            else:
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

    def start_mimetic_blossom(self):
        self.launch_blossom("mimetic")

    def reset_mimetic_blossom(self):
        if self.mimetic.is_sending:
            self.mimetic.stop_sending()
            self.send_blossom_command("mimetic", "reset")
            QTimer.singleShot(100, lambda: self.send_blossom_command("mimetic", "q"))
        else:
            self.logger("Mimetic is already stopped.", level="warning")

    def start_dancer_blossom(self):
        self.launch_blossom("dancer")

    def reset_dancer_blossom(self):
        self.send_blossom_command("dancer", "reset")
        QTimer.singleShot(100, lambda: self.send_blossom_command("dancer", "q"))

    def toggle_recording(self):
        if self.recorder_thread and self.recorder_thread.running:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.logger("Starting recording...", level="info")
        self.recording_button.setEnabled(False)
        self.recorder_thread = RecorderThread(output_path=f"{self.output_folder}/{self.study_id}/recording.mp4",
                                              resolution=(self.frame_width, self.frame_height), fps=30,
                                              mirror=self.mirror_video, logger=self.logger,
                                              capture_thread=self.capture_thread)

        self.recorder_thread.start()
        if self.recorder_thread.wait_until_ready(timeout=2):
            self.recording_button.setText("Stop Rec.")
            self.recording_button.setEnabled(True)


    def stop_recording(self):
        if not self.recorder_thread.running:
            self.logger("Recording is already stopped.", level="warning")
            return
        self.logger("Stopping recording...", level="info")
        self.recorder_thread.stop()
        self.recorder_thread.join()
        self.recording_button.setText("Start Rec.")
        self.recorder_thread = None

    def load_logs_to_textedit(self):
        try:
            with open(self.logger.output_path, "r") as file:
                log_data = json.load(file)
        except Exception as e:
            import traceback
            self.logger(f"Failed to load logs: {e}\n" + traceback.format_exc(), level="error")
            return

        if self.last_log_index >= len(log_data):
            return

        scrollbar = self.terminal_output.verticalScrollBar()
        at_bottom = scrollbar.value() == scrollbar.maximum()

        for entry in log_data[self.last_log_index:]:
            timestamp = entry.get("timestamp", "")
            level = entry.get("level", "INFO").upper()
            msg = str(entry.get("data", ""))

            msg = msg.replace("\n", "<br>")

            color = {
                "INFO": "#50fa7b",
                "WARNING": "#f1fa8c",
                "ERROR": "#ff5555",
                "DEBUG": "#8be9fd",
                "CRITICAL": "#ff4444"
            }.get(level, "#ffffff")

            html_line = f'<span style="color:{color};">[{timestamp}] [{level}]</span> {msg}'
            self.terminal_output.append(html_line)

        if at_bottom:
            self.terminal_output.moveCursor(self.terminal_output.textCursor().MoveOperation.End)
            self.terminal_output.ensureCursorVisible()

        self.last_log_index = len(log_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())