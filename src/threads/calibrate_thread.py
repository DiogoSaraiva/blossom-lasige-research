import traceback

from PyQt6.QtCore import QThread, pyqtSignal

class CalibrateThread(QThread):
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, mimetic):
        super().__init__()
        self.mimetic = mimetic

    def run(self):
        try:
            self.mimetic.calibrate_pose()
            self.finished_ok.emit(self.mimetic.angle_offset) # type: ignore
        except Exception as e:
            traceback.print_exc()
            self.failed.emit(str(e)) # type: ignore