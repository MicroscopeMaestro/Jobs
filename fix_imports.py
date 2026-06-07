import os
import glob

def replace_in_file(filepath):
    with open(filepath, 'r') as file:
        content = file.read()
    
    new_content = content.replace('PyQt6', 'PySide6')
    new_content = new_content.replace('pyqtSignal', 'Signal')
    new_content = new_content.replace('pyqtSlot', 'Slot')
    
    if new_content != content:
        with open(filepath, 'w') as file:
            file.write(new_content)
        print(f"Updated {filepath}")

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    py_files = glob.glob(os.path.join(root_dir, 'src', '**', '*.py'), recursive=True)
    
    for filepath in py_files:
        replace_in_file(filepath)
    
    # Also update app.py
    app_py = os.path.join(root_dir, 'app.py')
    if os.path.exists(app_py):
        replace_in_file(app_py)

    # And requirements
    req = os.path.join(root_dir, 'requirements.txt')
    if os.path.exists(req):
        replace_in_file(req)

if __name__ == '__main__':
    main()
