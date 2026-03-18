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
        self.last_triggered = 0.0
        self.debounce_seconds = 1.0 # Prevent double triggers from IDE saves

    def on_any_event(self, event):
        if event.is_directory:
            return
        
        # Some editors use atomic saves (creating a temp file and renaming it)
        # We need to check both src_path and dest_path (if it's a move event)
        src_path = getattr(event, 'src_path', '')
        dest_path = getattr(event, 'dest_path', '')
        
        # Check if either path matches our target extensions
        is_target_file = False
        if src_path and src_path.endswith(('.yaml', '.json', '.tex')):
            is_target_file = True
        if dest_path and dest_path.endswith(('.yaml', '.json', '.tex')):
            is_target_file = True
            
        if not is_target_file:
            return

        # Figure out which path to print
        path = dest_path if dest_path else src_path

        current_time = time.time()
        if current_time - self.last_triggered < self.debounce_seconds:
            return
        
        self.last_triggered = current_time
        print(f"\n--- File changed: {os.path.basename(path)} ---")
        self.rebuild()

    def rebuild(self):
        print("Regenerating application...")
        try:
            # First sync the language YAML files
            sync_script = os.path.join(os.getcwd(), 'src', 'sync_data.py')
            if os.path.exists(sync_script):
                print("Running data synchronization...")
                subprocess.run([sys.executable, sync_script], check=True)
                
            # Run the main script
            subprocess.run([sys.executable, MAIN_SCRIPT], check=True)
            # Run the split script
            subprocess.run([sys.executable, os.path.join(os.getcwd(), 'src', 'split_docs.py')], check=True)
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
