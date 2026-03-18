import yaml
import os

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

def cleanup():
    # Clean EN
    apps_en = load_yaml(DATA_EN_YAML)
    clean_en = [app for app in apps_en if not app.get('subject', '').startswith('[TRANSLATE EN]')]
    save_yaml(DATA_EN_YAML, clean_en)
    print(f"Cleaned {len(apps_en) - len(clean_en)} placeholders from data_en.yaml")

    # Clean DE
    apps_de = load_yaml(DATA_DE_YAML)
    clean_de = [app for app in apps_de if not app.get('subject', '').startswith('[TRANSLATE DE]')]
    save_yaml(DATA_DE_YAML, clean_de)
    print(f"Cleaned {len(apps_de) - len(clean_de)} placeholders from data_de.yaml")

if __name__ == '__main__':
    cleanup()
