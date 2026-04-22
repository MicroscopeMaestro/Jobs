import time
import os
import subprocess
import sys
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'src', 'main.py')
POLL_INTERVAL = 0.5   # seconds between scans

def setup_latex_path():
    """ Adds common macOS TeX distribution paths to the environment PATH. """
    tex_paths = [
        "/Library/TeX/texbin",
        "/usr/local/bin",
        "/usr/local/texlive/2025/bin/universal-darwin",
        "/usr/local/texlive/2024/bin/universal-darwin"
    ]
    current_path = os.environ.get("PATH", "")
    for path in tex_paths:
        if os.path.exists(path) and path not in current_path:
            current_path = f"{path}:{current_path}"
    os.environ["PATH"] = current_path

setup_latex_path()

def get_tex_mtimes(directory):
    """Returns a dict of {filepath: mtime} for all .tex files under directory."""
    snapshot = {}
    for path in glob.glob(os.path.join(directory, '**', '*.tex'), recursive=True):
        try:
            snapshot[path] = os.path.getmtime(path)
        except OSError:
            pass
    return snapshot

def trigger_build(changed_file):
    print(f"\n[Watcher] CHANGE DETECTED: {os.path.basename(changed_file)}")
    print(f"[Watcher] Triggering build...")
    try:
        result = subprocess.run([sys.executable, MAIN_SCRIPT], cwd=PROJECT_ROOT)
        if result.returncode == 0:
            print("[Watcher] BUILD SUCCESSFUL. (Awaiting next change...)\n")
        else:
            print(f"[Watcher] BUILD FAILED (Exit Code: {result.returncode}).\n")
    except Exception as e:
        print(f"[Watcher] Error triggering build: {e}\n")

if __name__ == "__main__":
    print("="*60)
    print("TEX WATCHER STARTING...")
    print(f"Watching: {TEMPLATES_DIR}")
    print(f"Method:   Custom mtime polling every {POLL_INTERVAL}s")
    print("="*60)
    print("Keep this terminal open. Press Ctrl+C to stop.\n")

    # Take initial snapshot
    last_snapshot = get_tex_mtimes(TEMPLATES_DIR)
    last_build = 0
    cooldown = 2.0  # seconds to wait after build before re-triggering

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            current_snapshot = get_tex_mtimes(TEMPLATES_DIR)

            # Find any file whose mtime changed or that is new
            changed = None
            for path, mtime in current_snapshot.items():
                if last_snapshot.get(path) != mtime:
                    changed = path
                    break

            if changed and (time.time() - last_build) > cooldown:
                last_build = time.time()
                last_snapshot = current_snapshot
                trigger_build(changed)
            else:
                last_snapshot = current_snapshot

    except KeyboardInterrupt:
        print("\nWatcher stopped.")

