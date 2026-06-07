import os
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

PROJECT_ROOT = "/Users/juanmunoz/Documents/GitHub/Jobs"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.gui.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow(project_root=PROJECT_ROOT)

def on_success():
    print("End-to-end Generation and Compilation successful!")
    app.quit()

def on_failure(err_msg):
    print(f"End-to-end failed: {err_msg}")
    app.quit()

def wait_for_completion():
    # If compile worker is running, connect to it
    if hasattr(window, 'compile_worker') and window.compile_worker:
        window.compile_worker.finished.connect(on_success)
        window.compile_worker.error.connect(on_failure)
    else:
        # Check if generation failed
        if hasattr(window, 'gen_worker') and window.gen_worker:
            # We already connected inside MainWindow, but we can hook in to quit
            window.gen_worker.error.connect(on_failure)
            QTimer.singleShot(1000, wait_for_completion) # check again later for compile worker
        else:
            QTimer.singleShot(1000, wait_for_completion)

try:
    window.form_tab.job_desc_input.setPlainText("Optical Systems Engineer focusing on lasers and precision instrumentation.")
    window.form_tab.generate_btn.click()
    print("Clicked Generate. Waiting for tasks to complete...")
    wait_for_completion()
    
    # Failsafe timeout
    QTimer.singleShot(45000, lambda: [print("Timeout waiting for completion!"), app.quit()])
except Exception as e:
    print(f"Error starting: {e}")
    app.quit()

app.exec()
print("Test script finished.")
