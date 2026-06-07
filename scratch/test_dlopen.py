import os
import sys
import ctypes

lib_path = "/Users/juanmunoz/Documents/GitHub/Jobs/.venv314/lib/python3.14/site-packages/PySide6/Qt/plugins/platforms/libqoffscreen.dylib"

try:
    print(f"Attempting to load {lib_path} via ctypes...")
    handle = ctypes.CDLL(lib_path)
    print("SUCCESS: Loaded libqoffscreen.dylib successfully via ctypes!")
    sys.exit(0)
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
