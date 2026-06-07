import sys
import time
from PyQt6.QtWidgets import QApplication, QProgressDialog, QMainWindow
from PyQt6.QtCore import Qt, QTimer

app = QApplication(sys.argv)
win = QMainWindow()
win.show()

dlg = QProgressDialog("Generating...", None, 0, 0, win)
dlg.setWindowTitle("Testing")
dlg.setWindowModality(Qt.WindowModality.WindowModal)
dlg.show()

# Quit after 2 seconds
QTimer.singleShot(2000, app.quit)

app.exec()
print("Clean exit!")
