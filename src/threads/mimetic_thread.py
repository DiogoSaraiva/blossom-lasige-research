from PyQt6.QtCore import QThread, pyqtSignal
from mimetic.start_no_ui import Mimetic

class MimeticRunnerThread(QThread):

    data_updated = pyqtSignal(dict)

    def __init__(self, mimetic: Mimetic):
        super().__init__()
        self.mimetic = mimetic
        self.running = True

    def run(self):
        while self.running:
            data = self.mimetic.data
            if data:
                self.data_updated.emit(data) #type: ignore
            self.msleep(30)


    def stop(self):
        self.running = False
        self.wait()