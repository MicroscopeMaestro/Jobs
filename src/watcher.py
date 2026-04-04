import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
MAIN_SCRIPT = os.path.join(PROJECT_ROOT, 'src', 'main.py')

class TexFileWatcher(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0
        self.cooldown = 2.0  # Prevents multiple triggers from a single save action

    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.tex'):
            return

        now = time.time()
        if now - self.last_run > self.cooldown:
            self.last_run = now
            print(f"\\n[Watcher] Detected change in {os.path.basename(event.src_path)}.")
            print("[Watcher] Running main.py to compile and merge documents...")
            try:
                subprocess.run(['python3', MAIN_SCRIPT])
                print("[Watcher] Automatic build complete. Waiting for next change...\\n")
            except Exception as e:
                print(f"[Watcher] Error triggering build: {e}\\n")

if __name__ == "__main__":
    if not os.path.exists(TEMPLATES_DIR):
        print(f"Error: Directory {TEMPLATES_DIR} not found.")
        exit(1)

    event_handler = TexFileWatcher()
    observer = Observer()
    observer.schedule(event_handler, TEMPLATES_DIR, recursive=False)
    
    print(f"Watching for changes to .tex files in '{TEMPLATES_DIR}'...")
    print("Keep this terminal open. Press Ctrl+C to stop.")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
