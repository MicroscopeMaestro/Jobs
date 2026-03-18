import yaml
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_YAML = os.path.join(PROJECT_ROOT, 'data', 'data.yaml')
DATA_EN_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_en.yaml')
DATA_DE_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_de.yaml')

def is_german(app):
    salutation = app.get('salutation', '').lower()
    subject = app.get('subject', '').lower()
    if 'sehr geehrte' in salutation or 'bewerbung' in subject or 'bewerbung' in salutation:
        return True
    return False

def main():
    with open(DATA_YAML, 'r', encoding='utf-8') as f:
        docs = yaml.safe_load(f)
        
    apps_en = []
    apps_de = []
    
    for app in docs:
        if is_german(app):
            apps_de.append(app)
        else:
            apps_en.append(app)
            
    with open(DATA_EN_YAML, 'w', encoding='utf-8') as f:
        yaml.dump(apps_en, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
    with open(DATA_DE_YAML, 'w', encoding='utf-8') as f:
        yaml.dump(apps_de, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
    print(f"Split {len(docs)} applications into {len(apps_en)} English and {len(apps_de)} German applications.")

if __name__ == '__main__':
    main()
