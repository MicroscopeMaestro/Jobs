import os
import sys

PROJECT_ROOT = "/Users/juanmunoz/Documents/GitHub/Jobs"
_pyside6 = os.path.join(PROJECT_ROOT, ".venv314", "lib", "python3.14", "site-packages", "PySide6")
_qt_plugins = os.path.join(_pyside6, "Qt", "plugins")

# Set the environment variable!
os.environ["QT_PLUGIN_PATH"] = _qt_plugins
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(_qt_plugins, "platforms")

try:
    from PySide6.QtWidgets import QApplication
    print("Environment variables set:")
    print("QT_PLUGIN_PATH:", os.environ.get("QT_PLUGIN_PATH"))
    print("QT_QPA_PLATFORM_PLUGIN_PATH:", os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"))
    
    app = QApplication(["test", "-platform", "offscreen"])
    print("SUCCESS: QApplication initialized in offscreen mode!")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
