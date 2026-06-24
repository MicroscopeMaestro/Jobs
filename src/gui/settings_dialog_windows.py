import os
import json
from PySide6.QtWidgets import (QGroupBox, QFormLayout, QComboBox, QLineEdit,
                               QLabel, QStackedWidget, QWidget, QVBoxLayout)
from .settings_dialog import SettingsDialog

PROVIDER_GEMINI = "gemini"
PROVIDER_KIMI = "kimi"
PROVIDER_CLAUDE = "claude"

_PROVIDERS = [
    ("Gemini 2.0 Flash  (free)", PROVIDER_GEMINI),
    ("Kimi / Moonshot  (free tier)", PROVIDER_KIMI),
    ("Claude  (paid — Anthropic)", PROVIDER_CLAUDE),
]


class SettingsDialogWindows(SettingsDialog):
    """Extends SettingsDialog with a unified AI provider selector for all operations."""

    def __init__(self, parent=None, project_root=""):
        super().__init__(parent, project_root)
        self.setWindowTitle("Settings & Tuning")

    # --- UI ---

    def init_ui(self):
        super().init_ui()

        provider_group = QGroupBox("AI Provider  (Generation, Chat & AI Check)")
        provider_layout = QFormLayout(provider_group)

        self.provider_combo = QComboBox()
        for label, _ in _PROVIDERS:
            self.provider_combo.addItem(label)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # Key fields stacked — show only the relevant one
        self.key_stack = QStackedWidget()

        # Page 0: Gemini
        gemini_page = QWidget()
        gemini_layout = QVBoxLayout(gemini_page)
        gemini_layout.setContentsMargins(0, 0, 0, 0)
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setPlaceholderText("GEMINI_API_KEY  (aistudio.google.com/apikey)")
        gemini_layout.addWidget(self.gemini_key_input)

        # Page 1: Kimi
        kimi_page = QWidget()
        kimi_layout = QVBoxLayout(kimi_page)
        kimi_layout.setContentsMargins(0, 0, 0, 0)
        self.kimi_key_input = QLineEdit()
        self.kimi_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.kimi_key_input.setPlaceholderText("KIMI_API_KEY  (platform.moonshot.cn)")
        kimi_layout.addWidget(self.kimi_key_input)

        # Page 2: Claude (no extra key needed — uses Anthropic key above)
        claude_page = QWidget()
        claude_layout = QVBoxLayout(claude_page)
        claude_layout.setContentsMargins(0, 0, 0, 0)
        claude_note = QLabel("Uses the Anthropic API key configured above.")
        claude_note.setStyleSheet("color: #a0aec0; font-style: italic;")
        claude_layout.addWidget(claude_note)

        self.key_stack.addWidget(gemini_page)
        self.key_stack.addWidget(kimi_page)
        self.key_stack.addWidget(claude_page)

        provider_layout.addRow("Provider:", self.provider_combo)
        provider_layout.addRow("API Key:", self.key_stack)

        layout = self.layout()
        layout.insertWidget(layout.count() - 1, provider_group)

    def _on_provider_changed(self, index):
        self.key_stack.setCurrentIndex(index)

    def _provider_key(self):
        return _PROVIDERS[self.provider_combo.currentIndex()][1]

    # --- Load / Save ---

    def load_settings(self):
        super().load_settings()

        provider = PROVIDER_GEMINI
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    provider = json.load(f).get("ai_provider", PROVIDER_GEMINI)
            except Exception:
                pass

        # Map provider key → combo index
        idx = next((i for i, (_, k) in enumerate(_PROVIDERS) if k == provider), 0)
        self.provider_combo.setCurrentIndex(idx)
        self._on_provider_changed(idx)

        # Load stored API keys from .env
        if os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("GEMINI_API_KEY="):
                            self.gemini_key_input.setText(
                                stripped.split("=", 1)[1].strip().strip('"').strip("'"))
                        elif stripped.startswith("KIMI_API_KEY="):
                            self.kimi_key_input.setText(
                                stripped.split("=", 1)[1].strip().strip('"').strip("'"))
            except Exception:
                pass

    def save_settings(self):
        # 1. Write GEMINI_API_KEY and KIMI_API_KEY to .env, preserving other lines
        extra_keys = {
            "GEMINI_API_KEY": self.gemini_key_input.text().strip(),
            "KIMI_API_KEY": self.kimi_key_input.text().strip(),
        }
        env_lines = []
        replaced = set()
        if os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        matched = False
                        for var, val in extra_keys.items():
                            if line.strip().startswith(f"{var}="):
                                env_lines.append(f"{var}={val}\n")
                                replaced.add(var)
                                matched = True
                                break
                        if not matched:
                            env_lines.append(line)
            except Exception:
                pass
        for var, val in extra_keys.items():
            if var not in replaced:
                env_lines.append(f"{var}={val}\n")
        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            for var, val in extra_keys.items():
                os.environ[var] = val
        except Exception as e:
            print(f"Could not write API keys to .env: {e}")

        # 2. Persist provider to JSON (merge with existing data)
        existing = {}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["ai_provider"] = self._provider_key()
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not save ai_provider: {e}")

        # 3. Parent handles Anthropic key + model params + closes dialog
        super().save_settings()

    @staticmethod
    def get_tuning_params(project_root):
        params = SettingsDialog.get_tuning_params(project_root)
        settings_path = os.path.join(project_root, "data", "gui_settings.json")
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                params["ai_provider"] = json.load(f).get("ai_provider", PROVIDER_GEMINI)
        except Exception:
            params["ai_provider"] = PROVIDER_GEMINI
        return params
