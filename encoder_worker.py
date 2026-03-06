import subprocess
from typing import Optional, Sequence

from PySide6.QtCore import QThread, Signal


class EncoderWorker(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, cmd: Sequence[str], cwd: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.cmd = list(cmd)
        self.cwd = cwd

    def run(self):
        try:
            self.progress.emit(10)
            proc = subprocess.run(
                self.cmd,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if proc.returncode == 0:
                self.progress.emit(100)
                self.finished.emit(True, "")
            else:
                msg = proc.stderr or proc.stdout or "Unknown ffmpeg error"
                self.finished.emit(False, msg)
        except Exception as exc:  # noqa: BLE001
            self.finished.emit(False, str(exc))

