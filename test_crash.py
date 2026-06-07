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

params = {
    "job_description": "Test JD",
    "title": "Engineer",
    "focus": [],
    "examples": [],
    "skills": [],
    "experience": [],
    "attachments": {"professional_experience": [], "education": [], "certificates": [], "others": []},
    "language": "en",
    "salary": "",
    "recipient_company": "Acme",
    "recipient_contact": "",
    "recipient_address": "",
    "page_limit": 2,
    "humanize": False
}
window.on_generation_requested(params)

import time
time.sleep(5) # wait for worker
