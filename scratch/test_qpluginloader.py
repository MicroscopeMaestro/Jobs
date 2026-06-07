import os
import sys

# Set plugin paths first so QPluginLoader knows the search context
PROJECT_ROOT = "/Users/juanmunoz/Documents/GitHub/Jobs"
_pyside6 = os.path.join(PROJECT_ROOT, ".venv314", "lib", "python3.14", "site-packages", "PySide6")
_qt_plugins = os.path.join(_pyside6, "Qt", "plugins")
os.environ["QT_PLUGIN_PATH"] = _qt_plugins

try:
    from PySide6.QtCore import QPluginLoader, QLibraryInfo
    print("Library Paths:", QLibraryInfo.path(QLibraryInfo.PluginsPath))
    
    plugin_path = os.path.join(_qt_plugins, "platforms", "libqcocoa.dylib")
    print(f"Loading plugin from: {plugin_path}")
    
    loader = QPluginLoader(plugin_path)
    loaded = loader.load()
    if not loaded:
        print(f"FAILED to load Qt plugin! Error: {loader.errorString()}")
        sys.exit(1)
    else:
        print("SUCCESS: Loaded Qt plugin successfully via QPluginLoader!")
        sys.exit(0)
except Exception as e:
    print(f"CRITICAL EXCEPTION: {e}")
    sys.exit(1)
