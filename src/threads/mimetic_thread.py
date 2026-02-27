from PyQt6.QtCore import QThread, pyqtSignal
from mimetic.mimetic import Mimetic

class MimeticRunnerThread(QThread):

    data_updated = pyqtSignal(dict)

    def __init__(self, mimetic: Mimetic):
        super().__init__()
        self.mimetic = mimetic
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                data = self.mimetic.data if self.mimetic.data is not None else {}
                self.data_updated.emit(data)  # type: ignore
            except Exception:
                pass
            self.msleep(30)


    def stop(self):
        self.is_running = False
        self.wait()