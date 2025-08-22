from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox, QComboBox
from PyQt6.QtCore import pyqtSignal
from src.settings import Settings
from src.settings_dialog_ui import Ui_SettingsDialog
from src.utils import get_local_ip, compact_timestamp

try:
    from serial.tools import list_ports
except Exception:
    list_ports = None

class SettingsDialog(QDialog, Ui_SettingsDialog):
    settings_applied = pyqtSignal(Settings)

    def __init__(self, current: Settings, parent):

        super().__init__(parent)
        self.setupUi(self)

        self.study_id.setText(compact_timestamp())

        self.host.setText(current.host)
        self.blossom_one_port.setText(str(current.blossom_one_port))
        self.blossom_two_port.setText(str(current.blossom_two_port))
        self.mirror_video.setChecked(_as_bool(current.mirror_video))
        self.flip_blossom.setChecked(_as_bool(current.flip_blossom))
        self.output_directory.setText(current.output_directory)
        self.music_directory.setText(current.music_directory)

        self.left_threshold.setText(str(current.left_threshold))
        self.right_threshold.setText(str(current.right_threshold))

        self.browse_output_dir_button.clicked.connect(self._browse_output_dir)
        self.browse_music_dir_button.clicked.connect(self._browse_music_dir)

        self.alpha_map_x_value.setValue(current.alpha_map['x'])
        self.alpha_map_y_value.setValue(current.alpha_map['y'])
        self.alpha_map_z_value.setValue(current.alpha_map['z'])
        self.alpha_map_h_value.setValue(current.alpha_map['h'])
        self.alpha_map_e_value.setValue(current.alpha_map['e'])

        self.send_rate.setValue(current.send_rate)

        self._populate_serial_combos(
            current_one=getattr(current, "blossom_one_device", ""),
            current_two=getattr(current, "blossom_two_device", "")
        )

        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

    def showEvent(self, event):
        super().showEvent(event)
        self._populate_serial_combos(
            current_one=self._current_combo_value(self.blossom_one_device) if hasattr(self,
                                                                                      "blossom_one_device") else "",
            current_two=self._current_combo_value(self.blossom_two_device) if hasattr(self,
                                                                                      "blossom_two_device") else "",
        )
    def _browse_music_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Music Directory", self.music_directory.text())
        if path:
            self.output_directory.setText(path)


    def _browse_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Output Directory", self.output_directory.text())
        if path:
            self.output_directory.setText(path)

    def _on_accept(self):
        try:
            new = Settings(
                study_id=self.study_id.text(),
                blossom_one_port=int(self.blossom_one_port.text()),
                blossom_two_port=int(self.blossom_two_port.text()),
                blossom_one_device=self.blossom_one_device.currentText(),
                blossom_two_device=self.blossom_two_device.currentText(),
                mirror_video=self.mirror_video.isChecked(),
                flip_blossom=self.flip_blossom.isChecked(),
                output_directory=self.output_directory.text().strip(),
                left_threshold=float(self.left_threshold.text()),
                right_threshold=float(self.right_threshold.text()),
                alpha_map={"x": float(self.alpha_map_x_value.text()), "y": float(self.alpha_map_y_value.text()),
                           "z": float(self.alpha_map_z_value.text()), "h": float(self.alpha_map_h_value.text()),
                           "e": float(self.alpha_map_e_value.text())},
                send_rate=int(self.send_rate.text()),
                send_threshold=float(self.send_threshold.text()),
                target_fps=int(self.target_fps.text()),
                music_directory=self.music_directory.text().strip(),
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

    def _current_combo_value(self, combo: QComboBox) -> str:
        if combo is None:
            return ""
        txt = combo.currentText().strip()
        return "" if txt.startswith("(") and "ttyACM" in txt else txt

    def _list_acm_ports(self) -> list[str]:
        if list_ports is None:
            return []
        ports = []
        for p in list_ports.comports():
            dev = getattr(p, "device", "") or ""
            if dev.startswith("/dev/ttyACM"):
                ports.append(dev)

        def acm_key(d: str):
            try:
                return int(d.replace("/dev/ttyACM", ""))
            except ValueError:
                return 9999

        return sorted(ports, key=acm_key)

    def _populate_serial_combos(self, current_one: str = "", current_two: str = ""):
        def fill(combo: QComboBox, cur: str):
            combo.clear()
            ports = self._list_acm_ports()
            if not ports:
                combo.addItem("(no /dev/ttyACM found)")
                combo.setEnabled(False)
                return
            combo.addItems(ports)
            combo.setEnabled(True)
            if cur and cur in ports:
                combo.setCurrentText(cur)
            elif cur and cur not in ports:
                combo.insertItem(0, f"{cur} (current)")
                combo.setCurrentIndex(0)

        if hasattr(self, "blossom_one_device"):
            fill(self.blossom_one_device, current_one or "")
        if hasattr(self, "blossom_two_device"):
            fill(self.blossom_two_device, current_two or "")

def _as_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}