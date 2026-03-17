import yaml
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_EN_YAML = os.path.join(PROJECT_ROOT, 'data', 'data_en.yaml')

def fix_ampersands(obj):
    if isinstance(obj, str):
        # Only replace & if not already escaped
        import re
        return re.sub(r'(?<!\\)&', r'\&', obj)
    elif isinstance(obj, list):
        return [fix_ampersands(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: fix_ampersands(v) for k, v in obj.items()}
    return obj

def main():
    if not os.path.exists(DATA_EN_YAML):
        return
        
    with open(DATA_EN_YAML, 'r', encoding='utf-8') as f:
        apps = yaml.safe_load(f) or []
        
    for i, app in enumerate(apps):
        if app.get('recipient_company') == 'Iventim Solutions GmbH':
            apps[i] = fix_ampersands(app)
            
    with open(DATA_EN_YAML, 'w', encoding='utf-8') as f:
        yaml.dump(apps, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        
    print("Fixed ampersands in data_en.yaml")

if __name__ == '__main__':
    main()
