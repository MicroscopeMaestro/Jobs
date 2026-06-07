import os
import sys
import warnings
# Suppress deprecation warnings from google.generativeai at startup
warnings.filterwarnings("ignore", category=FutureWarning, module="google")

from dotenv import load_dotenv

# Ensure the root workspace is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Load environment variables (.env file in workspace root)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Import PySide6
import PySide6
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFont
from src.gui import MainWindow
def apply_premium_stylesheet(app):
    # Sleek High-End HSL-Tailored Dark QSS Theme
    qss = """
    /* Main Window styling */
    QMainWindow {
        background-color: #121212;
    }
    
    /* Global widget defaults */
    QWidget {
        color: #e2e8f0;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 13px;
        background-color: transparent;
    }
    
    /* Scroll Areas */
    QScrollArea {
        border: none;
        background-color: #121212;
    }
    
    /* Custom Group Boxes styled as premium cards */
    QGroupBox {
        border: 1px solid #2d3748;
        border-radius: 6px;
        margin-top: 15px;
        font-weight: bold;
        background-color: #1a202c;
        padding-top: 15px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        color: #ff9100; /* Warm Accent Orange */
        background-color: #1a202c;
        left: 10px;
        border-radius: 3px;
    }
    
    /* Line Inputs & Text editors */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 6px;
        color: #f7fafc;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #ff9100;
        background-color: #334155;
    }
    
    /* Combobox arrow customization */
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 22px;
        border-left-width: 1px;
        border-left-color: #4a5568;
        border-left-style: solid;
    }
    
    /* Tab Widget & Bar */
    QTabWidget::pane {
        border: 1px solid #2d3748;
        background-color: #121212;
    }
    QTabBar::tab {
        background-color: #1a202c;
        border: 1px solid #2d3748;
        border-bottom-color: transparent;
        padding: 8px 16px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        color: #a0aec0;
        font-weight: bold;
    }
    QTabBar::tab:selected {
        background-color: #121212;
        color: #ff9100;
        border-bottom: 2px solid #ff9100;
    }
    QTabBar::tab:hover:!selected {
        background-color: #2d3748;
        color: #f7fafc;
    }
    
    /* Push Buttons styling */
    QPushButton {
        background-color: #2d3748;
        border: 1px solid #4a5568;
        border-radius: 4px;
        padding: 6px 14px;
        color: #e2e8f0;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #4a5568;
        border-color: #ff9100;
    }
    QPushButton:pressed {
        background-color: #1a202c;
    }
    
    /* Status & Progress bars */
    QStatusBar {
        background-color: #1a202c;
        border-top: 1px solid #2d3748;
        color: #a0aec0;
    }
    QProgressBar {
        border: 1px solid #4a5568;
        border-radius: 4px;
        text-align: center;
        background-color: #1a202c;
    }
    QProgressBar::chunk {
        background-color: #ff9100;
        width: 10px;
    }
    
    /* Scrollbars customization */
    QScrollBar:vertical {
        border: none;
        background: #1a202c;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #4a5568;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #ff9100;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    QScrollBar:horizontal {
        border: none;
        background: #1a202c;
        height: 10px;
        margin: 0px;
    }
    QScrollBar::handle:horizontal {
        background: #4a5568;
        min-width: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:horizontal:hover {
        background: #ff9100;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        border: none;
        background: none;
    }
    
    /* Sliders styling */
    QSlider::groove:horizontal {
        border: 1px solid #4a5568;
        height: 6px;
        background: #1a202c;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #ff9100;
        border: 1px solid #ff9100;
        width: 14px;
        height: 14px;
        margin: -4px 0;
        border-radius: 7px;
    }
    QSlider::handle:horizontal:hover {
        background: #ffb74d;
        border-color: #ffb74d;
    }
    
    /* List Widgets */
    QListWidget {
        background-color: #1a202c;
        border: 1px solid #2d3748;
        border-radius: 4px;
        padding: 5px;
    }
    
    /* Tooltips */
    QToolTip {
        background-color: #2d3748;
        border: 1px solid #ff9100;
        border-radius: 3px;
        color: #f7fafc;
        padding: 4px;
    }
    """
    app.setStyleSheet(qss)

def main():
    # Enable High-DPI scaling support for high-res screens
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    
    # Configure beautiful typography (use system fonts available on macOS)
    font = QFont(".AppleSystemUIFont", 10)
    if not font.exactMatch():
        font = QFont("Helvetica Neue", 10)
    app.setFont(font)
    
    # Apply modern design QSS stylesheet
    apply_premium_stylesheet(app)
    
    # Run GUI
    window = MainWindow(PROJECT_ROOT)
    window.show()
    
    # Force the window to the foreground
    window.raise_()
    window.activateWindow()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
