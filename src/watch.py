import sys
import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configuration
WATCH_PATHS = [
    os.path.join(os.getcwd(), 'data'),
    os.path.join(os.getcwd(), 'templates')
]
MAIN_SCRIPT = os.path.join(os.getcwd(), 'src', 'main.py')

class RebuildHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_triggered = 0
        self.debounce_seconds = 2 # Prevent double triggers from IDE saves

    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Only watch .yaml and .tex files
        if not event.src_path.endswith(('.yaml', '.tex')):
            return

        current_time = time.time()
        if current_time - self.last_triggered < self.debounce_seconds:
            return
        
        self.last_triggered = current_time
        print(f"\n--- File modified: {os.path.basename(event.src_path)} ---")
        self.rebuild()

    def rebuild(self):
        print("Regenerating application...")
        try:
            # Run the main script
            subprocess.run([sys.executable, MAIN_SCRIPT], check=True)
            print("--- Rebuild complete ---")
        except subprocess.CalledProcessError as e:
            print(f"--- Rebuild failed: {e} ---")

if __name__ == "__main__":
    print(f"Monitoring paths: {WATCH_PATHS}")
    print("Watching for changes in data/ and templates/... (Press Ctrl+C to stop)")
    
    event_handler = RebuildHandler()
    observer = Observer()
    
    for path in WATCH_PATHS:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=False)
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
