import os
import json

class PresetManager:
    def __init__(self, project_root):
        self.project_root = project_root
        self.presets_path = os.path.join(project_root, "data", "presets.json")
        os.makedirs(os.path.dirname(self.presets_path), exist_ok=True)
        self.presets = self.load_presets()

    def load_presets(self):
        if os.path.exists(self.presets_path):
            try:
                with open(self.presets_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading presets: {e}")
        return {}

    def save_presets(self):
        try:
            with open(self.presets_path, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def save_preset(self, name, param_dict):
        """Saves a preset under a unique name."""
        self.presets[name] = param_dict
        self.save_presets()

    def get_preset(self, name):
        """Retrieves a preset dictionary by name."""
        return self.presets.get(name)

    def list_presets(self):
        """Returns a sorted list of all available preset names."""
        return sorted(list(self.presets.keys()))

    def delete_preset(self, name):
        """Removes a preset by name."""
        if name in self.presets:
            del self.presets[name]
            self.save_presets()
            return True
        return False
