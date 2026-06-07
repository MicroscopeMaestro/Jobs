import os
import sys
from PyQt6.QtWidgets import QApplication

PROJECT_ROOT = "/Users/juanmunoz/Documents/GitHub/Jobs"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.gui.main_window import MainWindow

app = QApplication(sys.argv)
window = MainWindow(project_root=PROJECT_ROOT)

try:
    window.form_tab.job_desc_input.setPlainText("Test job description")
    window.form_tab.generate_btn.click()
    print("Clicked successfully!")
except Exception as e:
    print(f"Error during click: {e}")
