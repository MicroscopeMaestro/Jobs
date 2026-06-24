import time
import os
import subprocess
import sys
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'src', 'main.py')
POLL_INTERVAL = 0.5


def setup_latex_path():
    """Adds common Windows TeX distribution paths to the environment PATH."""
    tex_paths = [
        r"C:\Program Files\MiKTeX\miktex\bin\x64",
        r"C:\Program Files\MiKTeX 2.9\miktex\bin\x64",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"),
        r"C:\texlive\2025\bin\windows",
        r"C:\texlive\2024\bin\windows",
    ]
    current_path = os.environ.get("PATH", "")
    for path in tex_paths:
        if os.path.exists(path) and path not in current_path:
            current_path = path + ";" + current_path
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
    print(f"\n[Watcher] CHANGE DETECTED: {os.path.basename(changed_file)}", flush=True)
    print(f"[Watcher] Triggering build...", flush=True)
    try:
        result = subprocess.run([sys.executable, MAIN_SCRIPT], cwd=PROJECT_ROOT)
        if result.returncode == 0:
            print("[Watcher] BUILD SUCCESSFUL. (Awaiting next change...)\n", flush=True)
        else:
            print(f"[Watcher] BUILD FAILED (Exit Code: {result.returncode}).\n", flush=True)
    except Exception as e:
        print(f"[Watcher] Error triggering build: {e}\n", flush=True)


if __name__ == "__main__":
    print("="*60, flush=True)
    print("TEX WATCHER STARTING (Windows)...", flush=True)
    print(f"Watching: {TEMPLATES_DIR}", flush=True)
    print(f"Method:   Custom mtime polling every {POLL_INTERVAL}s", flush=True)
    print("="*60, flush=True)
    print("Keep this terminal open. Press Ctrl+C to stop.\n", flush=True)

    last_snapshot = get_tex_mtimes(TEMPLATES_DIR)
    last_build = 0
    cooldown = 2.0

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            current_snapshot = get_tex_mtimes(TEMPLATES_DIR)

            changed = None
            for path, mtime in current_snapshot.items():
                if last_snapshot.get(path) != mtime:
                    changed = path
                    break

            if changed:
                if (time.time() - last_build) > cooldown:
                    last_build = time.time()
                    last_snapshot = current_snapshot
                    trigger_build(changed)
            else:
                last_snapshot = current_snapshot

    except KeyboardInterrupt:
        print("\nWatcher stopped.")
