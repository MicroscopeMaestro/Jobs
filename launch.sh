#!/bin/bash
# Job Application GUI Launcher
# Explicitly sets all dyld resolution paths so libqcocoa.dylib loads on macOS 26

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv_gui"

# Ensure latex is in path
export PATH="/Library/TeX/texbin:/usr/local/bin:/usr/local/texlive/2025/bin/universal-darwin:$PATH"

# macOS High-DPI support
export QT_AUTO_SCREEN_SCALE_FACTOR=1

echo "Launching Job Application GUI..."
echo "Python: $VENV_DIR/bin/python"

"$VENV_DIR/bin/python" "$SCRIPT_DIR/app.py" 2>&1 | tee "$SCRIPT_DIR/startup.log"
