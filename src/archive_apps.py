import yaml
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_EN_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_en.yaml')
DATA_DE_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_de.yaml')
ARCHIVE_YAML = os.path.join(PROJECT_ROOT, 'data', 'archive.yaml')

def load_yaml(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or []

def save_yaml(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

def archive():
    archive_data = load_yaml(ARCHIVE_YAML)
    
    # Process EN
    apps_en = load_yaml(DATA_EN_YAML)
    if len(apps_en) > 1:
        to_archive = apps_en[:-1]
        current_en = [apps_en[-1]]
        archive_data.extend(to_archive)
        save_yaml(DATA_EN_YAML, current_en)
        print(f"Moved {len(to_archive)} English applications to archive. Remaining: 1")
    else:
        print("data_en.yaml already has 1 or 0 applications.")

    # Process DE
    apps_de = load_yaml(DATA_DE_YAML)
    if len(apps_de) > 1:
        to_archive = apps_de[:-1]
        current_de = [apps_de[-1]]
        archive_data.extend(to_archive)
        save_yaml(DATA_DE_YAML, current_de)
        print(f"Moved {len(to_archive)} German applications to archive. Remaining: 1")
    else:
        print("data_de.yaml already has 1 or 0 applications.")

    if len(archive_data) > 0:
        save_yaml(ARCHIVE_YAML, archive_data)
        print(f"Total applications in archive: {len(archive_data)}")

if __name__ == '__main__':
    archive()
