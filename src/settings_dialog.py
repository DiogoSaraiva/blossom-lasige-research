from typing import Literal

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox, QComboBox

from src import utils
from src.settings import Settings
from src.settings_dialog_ui import Ui_SettingsDialog

try:
    from serial.tools import list_ports as list_com_ports
except Exception:
    list_com_ports = None

class SettingsDialog(QDialog, Ui_SettingsDialog):
    settings_applied = pyqtSignal(Settings)

    def __init__(self, current: Settings, parent):

        super().__init__(parent)
        self.setupUi(self)

        # Base
        self.study_id.setText(current.study_id)
        self.blossom_one_device.setCurrentText(current.blossom_one_device)
        self.blossom_two_device.setCurrentText(current.blossom_two_device)
        self.populate_devices_combos(
            current_one=getattr(current, "blossom_one_device", ""),
            current_two=getattr(current, "blossom_two_device", ""),
            current_cam=getattr(current, "cam_device", "")
        )
        self.host.setText(current.host)
        self.blossom_one_port.setText(str(current.blossom_one_port))
        self.blossom_two_port.setText(str(current.blossom_two_port))
        self.mirror_video.setChecked(bool(current.mirror_video))
        self.flip_blossom.setChecked(bool(current.flip_blossoms))
        self.output_directory.setText(current.output_directory)
        self.browse_output_dir_button.clicked.connect(self._browse_output_dir)
        self.get_current_ip.clicked.connect(lambda: self.host.setText(utils.get_local_ip()))

        # Gaze Tracking
        self.left_threshold.setValue(current.left_threshold)
        self.right_threshold.setValue(current.right_threshold)

        # Mimetic
        self.alpha_map_x_value.setValue(current.alpha_map['x'])
        self.alpha_map_y_value.setValue(current.alpha_map['y'])
        self.alpha_map_z_value.setValue(current.alpha_map['z'])
        self.alpha_map_h_value.setValue(current.alpha_map['h'])
        self.alpha_map_e_value.setValue(current.alpha_map['e'])
        self.x_min.setValue(current.limit_map.get("min").get("x"))
        self.x_max.setValue(current.limit_map.get("max").get("x"))
        self.y_min.setValue(current.limit_map.get("min").get("y"))
        self.y_max.setValue(current.limit_map.get("max").get("y"))
        self.z_min.setValue(current.limit_map.get("min").get("z"))
        self.z_max.setValue(current.limit_map.get("max").get("z"))
        self.h_min.setValue(current.limit_map.get("min").get("h"))
        self.h_max.setValue(current.limit_map.get("max").get("h"))
        self.e_min.setValue(current.limit_map.get("min").get("e"))
        self.e_max.setValue(current.limit_map.get("max").get("e"))
        self.multiplier_map_x_value.setValue(current.multiplier_map['x'])
        self.multiplier_map_y_value.setValue(current.multiplier_map['y'])
        self.multiplier_map_z_value.setValue(current.multiplier_map['z'])
        self.multiplier_map_h_value.setValue(current.multiplier_map['h'])
        self.multiplier_map_e_value.setValue(current.multiplier_map['e'])
        self.send_rate.setValue(current.send_rate)
        self.send_threshold.setValue(current.send_threshold)

        # Dancer
        self.dancer_mode.setCurrentText(current.dancer_mode)
        self.music_directory.setText(current.music_directory)
        self.mic_sr.setValue(current.mic_sr)
        self.browse_music_dir_button.clicked.connect(self._browse_music_dir)



        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

    def showEvent(self, event):
        super().showEvent(event)
        self.populate_devices_combos(
            current_one=self._current_combo_value(self.blossom_one_device) if hasattr(self,
                                                                                      "blossom_one_device") else "",
            current_two=self._current_combo_value(self.blossom_two_device) if hasattr(self,
                                                                                      "blossom_two_device") else "",
            current_cam=self._current_combo_value(self.cam_device) if hasattr(self, "cam_device") else "",
        )
    def _browse_music_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Music Directory", self.music_directory.text())
        if path:
            self.music_directory.setText(path)


    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Output Directory", self.output_directory.text())
        if path:
            self.output_directory.setText(path)

    def _on_accept(self):
        try:
            new = Settings(
                # Base
                study_id=self.study_id.text(),
                blossom_one_device=self.blossom_one_device.currentText(),
                blossom_two_device=self.blossom_two_device.currentText(),
                blossom_one_port=int(self.blossom_one_port.text()),
                blossom_two_port=int(self.blossom_two_port.text()),
                mirror_video=self.mirror_video.isChecked(),
                flip_blossoms=self.flip_blossom.isChecked(),
                output_directory=self.output_directory.text().strip(),
                # Gaze Tracking
                left_threshold=float(self.left_threshold.text()),
                right_threshold=float(self.right_threshold.text()),
                # Mimetic
                alpha_map={"x": self.alpha_map_x_value.value(), "y": self.alpha_map_y_value.value(), "z": self.alpha_map_z_value.value(),
                           "h": self.alpha_map_h_value.value(), "e": self.alpha_map_e_value.value()},
                multiplier_map={"x": self.multiplier_map_x_value.value(), "y": self.multiplier_map_y_value.value(),
                                "z": self.multiplier_map_z_value.value(), "h": self.multiplier_map_h_value.value(),
                                "e": self.multiplier_map_e_value.value()},
                limit_map={"min": {"x": self.x_min.value(), "y": self.y_min.value(), "z": self.z_min.value(), "h": self.h_min.value(), "e": self.e_min.value()},
                           "max": {"x": self.x_max.value(), "y": self.y_max.value(), "z": self.z_max.value(), "h": self.h_max.value(), "e": self.e_max.value()}},
                send_rate=int(self.send_rate.text()),
                send_threshold=float(self.send_threshold.text()),
                target_fps=int(self.target_fps.text()),
                cam_device=self.cam_device.currentText(),
                # Dancer
                music_directory=self.music_directory.text().strip(),
                dancer_mode=self.dancer_mode.currentText(),
                analysis_interval=float(self.analysis_interval.text()),
            )

            for p in (new.blossom_one_port, new.blossom_two_port):
                if not (1024 <= p <= 65535):
                    raise ValueError("Ports must be between 1024 and 65535.")
            if new.blossom_one_port == new.blossom_two_port:
                raise ValueError("Ports must be different.")
            if new.left_threshold >= new.right_threshold:
                raise ValueError("Left threshold must be < Right threshold.")

        except Exception as e:
            QMessageBox.critical(self, "Invalid settings", str(e))
            return

        self.settings_applied.emit(new) # type: ignore
        self.accept()

    @staticmethod
    def _current_combo_value(combo: QComboBox) -> str:
        if combo is None:
            return ""
        txt = combo.currentText().strip().removesuffix(" (current)")
        return "" if txt.startswith("(") else txt


    def populate_devices_combos(self, current_one: str = "", current_two: str = "", current_cam: str = ""):
        import re
        import glob
        import struct
        import fcntl
        from serial.tools import list_ports

        def key(dev: str) -> int:
            m = re.search(r'(\d+)$', dev)
            return int(m.group(1)) if m else 9999

        def _list_capture_devices(current: str = "") -> list[str]:
            """Return one /dev/videoX per physical camera.
            Filters by V4L2_CAP_VIDEO_CAPTURE and deduplicates by bus_info.
            The currently configured device skips the cv2 read test (may already be in use)."""
            import cv2
            V4L2_CAP_VIDEO_CAPTURE = 0x00000001
            VIDIOC_QUERYCAP = 0x80685600
            seen_buses: set[str] = set()
            result = []
            for path in sorted(glob.glob("/dev/video*"), key=key):
                try:
                    with open(path, 'rb') as f:
                        buf = bytearray(104)
                        fcntl.ioctl(f, VIDIOC_QUERYCAP, buf)
                        caps = struct.unpack_from('<I', buf, 84)[0]
                        if not (caps & V4L2_CAP_VIDEO_CAPTURE):
                            continue
                        bus_info = buf[48:80].rstrip(b'\x00').decode('ascii', errors='replace')
                except Exception:
                    continue
                if bus_info in seen_buses:
                    continue
                if path == current:
                    # Already in use by the app — trust V4L2 caps, skip cv2 test
                    seen_buses.add(bus_info)
                    result.append(path)
                    continue
                cap = cv2.VideoCapture(path)
                can_read = cap.isOpened() and cap.read()[0]
                cap.release()
                if can_read:
                    seen_buses.add(bus_info)
                    result.append(path)
            return result

        def list_dev(mode: Literal["acm", "cam"]) -> list[str]:
            if mode == "acm":
                devs = [p.device for p in list_ports.comports() if getattr(p, "device", "").startswith("/dev/ttyACM")]
            else:  # "cam"
                devs = _list_capture_devices(current=current_cam)
            return devs

        def fill(mode: Literal["acm", "cam"], combo: QComboBox, cur: str):
            combo.blockSignals(True)
            combo.clear()

            items = list_dev(mode)
            if not items:
                combo.addItem("(no devs. found)" if mode == "acm" else "(no cams found)")
                combo.setEnabled(False)
            else:
                combo.addItems(items)
                combo.setEnabled(True)
                if cur and cur in items:
                    combo.setCurrentText(cur)

            combo.blockSignals(False)

        fill("acm", self.blossom_one_device, current_one or "")
        fill("acm", self.blossom_two_device, current_two or "")
        fill("cam", self.cam_device, current_cam or "")




def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}