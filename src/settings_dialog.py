from PyQt6.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt6.QtCore import pyqtSignal
from src.settings import Settings
from src.settings_dialog_ui import Ui_SettingsDialog
from src.utils import get_local_ip


class SettingsDialog(QDialog, Ui_SettingsDialog):
    settings_applied = pyqtSignal(Settings)

    def __init__(self, current: Settings, parent):

        super().__init__(parent)
        self.setupUi(self)
        self.host.setText(current.host)
        self.mimetic_port.setText(str(current.mimetic_port))
        self.dancer_port.setText(str(current.dancer_port))
        self.mirror_video.setChecked(_as_bool(current.mirror_video))
        self.flip_blossom.setChecked(_as_bool(current.flip_blossom))
        self.output_directory.setText(current.output_directory)
        self.left_threshold.setText(str(current.left_threshold))
        self.right_threshold.setText(str(current.right_threshold))

        self.browse_button.clicked.connect(self._browse_output)
        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "Choose Output Folder", self.output_directory.text())
        if path:
            self.output_directory.setText(path)

    def _on_accept(self):
        try:
            new = Settings(
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