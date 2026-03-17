import yaml
import os
import copy

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_EN_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_en.yaml')
DATA_DE_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_de.yaml')

def load_yaml(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or []

def save_yaml(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def get_app_id(app):
    company = app.get('recipient_company', '').strip()
    position = app.get('job_position', '').strip()
    return f"{company}::{position}"

def sync_applications():
    # Mirroring has been disabled per user request to prevent file pollution.
    # Individual applications should now be managed only in their target language file.
    print("Mirroring synchronization is currently disabled.")
    pass

if __name__ == '__main__':
    sync_applications()
