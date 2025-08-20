from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
from src.settings import Settings
from src.settings_dialog_ui import Ui_SettingsDialog
from src.utils import get_local_ip, compact_timestamp


class SettingsDialog(QDialog, Ui_SettingsDialog):
    settings_applied = pyqtSignal(Settings)

    def __init__(self, current: Settings, parent):

        super().__init__(parent)
        self.setupUi(self)

        self.study_id.setText(compact_timestamp())

        self.host.setText(current.host)
        self.mimetic_port.setText(str(current.mimetic_port))
        self.dancer_port.setText(str(current.dancer_port))
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
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

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
                host=self.host.text().strip() or get_local_ip(),
                mimetic_port=int(self.mimetic_port.text()),
                dancer_port=int(self.dancer_port.text()),
                mirror_video=self.mirror_video.isChecked(),
                flip_blossom=self.flip_blossom.isChecked(),
                output_directory=self.output_directory.text().strip(),
                left_threshold=float(self.left_threshold.text()),
                right_threshold=float(self.right_threshold.text()),
            )

            for p in (new.mimetic_port, new.dancer_port):
                if not (1024 <= p <= 65535):
                    raise ValueError("Ports must be between 1024 and 65535.")
            if new.mimetic_port == new.dancer_port:
                raise ValueError("Ports must be different.")
            if new.left_threshold >= new.right_threshold:
                raise ValueError("Left threshold must be < Right threshold.")

        except Exception as e:
            QMessageBox.critical(self, "Invalid settings", str(e))
            return

        self.settings_applied.emit(new) # type: ignore
        self.accept()

def _as_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"1", "true", "yes", "on"}