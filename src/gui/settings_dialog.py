import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QSlider, QSpinBox, QPushButton, 
                             QLineEdit, QMessageBox, QGroupBox, QFormLayout,
                             QStackedWidget, QWidget)
from PySide6.QtCore import Qt

PROVIDER_GEMINI = "gemini"
PROVIDER_KIMI = "kimi"
PROVIDER_CLAUDE = "claude"
PROVIDER_OLLAMA = "ollama"

_PROVIDERS = [
    ("Gemini 2.0 Flash  (free)", PROVIDER_GEMINI),
    ("Kimi / Moonshot  (free tier)", PROVIDER_KIMI),
    ("Ollama  (local AI model)", PROVIDER_OLLAMA),
    ("Claude  (paid — Anthropic)", PROVIDER_CLAUDE),
]

class SettingsDialog(QDialog):
    def __init__(self, parent=None, project_root=""):
        super().__init__(parent)
        self.project_root = project_root
        
        personal_settings = os.path.join(project_root, "personal", "data", "gui_settings.json")
        if os.path.exists(personal_settings) or os.path.exists(os.path.join(project_root, "personal")):
            self.settings_path = personal_settings
        else:
            self.settings_path = os.path.join(project_root, "data", "gui_settings.json")
            
        self.env_path = os.path.join(project_root, ".env")
        
        self.setWindowTitle("Settings & Tuning")
        self.setMinimumWidth(480)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. AI Provider Selection Group
        provider_group = QGroupBox("AI Provider Selection")
        provider_layout = QFormLayout(provider_group)
        
        self.provider_combo = QComboBox()
        for label, _ in _PROVIDERS:
            self.provider_combo.addItem(label)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        
        # Stacked widget for provider-specific credentials/options
        self.provider_stack = QStackedWidget()
        
        # Page 0: Gemini
        gemini_page = QWidget()
        gemini_layout = QFormLayout(gemini_page)
        gemini_layout.setContentsMargins(0, 0, 0, 0)
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setPlaceholderText("GEMINI_API_KEY  (aistudio.google.com/apikey)")
        gemini_layout.addRow("Gemini Key:", self.gemini_key_input)
        
        # Page 1: Kimi
        kimi_page = QWidget()
        kimi_layout = QFormLayout(kimi_page)
        kimi_layout.setContentsMargins(0, 0, 0, 0)
        self.kimi_key_input = QLineEdit()
        self.kimi_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.kimi_key_input.setPlaceholderText("KIMI_API_KEY  (platform.moonshot.cn)")
        kimi_layout.addRow("Kimi Key:", self.kimi_key_input)
        
        # Page 2: Ollama
        ollama_page = QWidget()
        ollama_layout = QFormLayout(ollama_page)
        ollama_layout.setContentsMargins(0, 0, 0, 0)
        self.ollama_model_input = QLineEdit()
        self.ollama_model_input.setPlaceholderText("e.g. qwen2.5:7b, gemma2:9b")
        self.ollama_model_input.setText("qwen2.5:7b")
        ollama_layout.addRow("Model Tag:", self.ollama_model_input)
        
        # Page 3: Claude
        claude_page = QWidget()
        claude_layout = QFormLayout(claude_page)
        claude_layout.setContentsMargins(0, 0, 0, 0)
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Paste ANTHROPIC_API_KEY (sk-ant-...) here...")
        self.key_status_label = QLabel("Loading status...")
        self.key_status_label.setStyleSheet("font-style: italic;")
        claude_layout.addRow("Claude Key:", self.api_key_input)
        claude_layout.addRow("", self.key_status_label)
        
        self.provider_stack.addWidget(gemini_page)
        self.provider_stack.addWidget(kimi_page)
        self.provider_stack.addWidget(ollama_page)
        self.provider_stack.addWidget(claude_page)
        
        provider_layout.addRow("AI Provider:", self.provider_combo)
        provider_layout.addRow("", self.provider_stack)
        layout.addWidget(provider_group)
        
        # 2. Generation Tuning Group (Defaults/Claude parameters)
        tuning_group = QGroupBox("Generation Parameters")
        tuning_layout = QFormLayout(tuning_group)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "claude-opus-4-8",
            "claude-sonnet-4-6",
            "claude-haiku-4-5"
        ])
        
        # Temperature Slider
        temp_layout = QHBoxLayout()
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setSingleStep(5)
        self.temp_val_label = QLabel("0.2")
        self.temp_slider.valueChanged.connect(lambda v: self.temp_val_label.setText(f"{v/100:.2f}"))
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_val_label)
        
        # Max Tokens
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(1000, 16000)
        self.tokens_spin.setSingleStep(500)
        self.tokens_spin.setValue(4000)
        
        tuning_layout.addRow("Claude Model:", self.model_combo)
        tuning_layout.addRow("Temperature:", temp_layout)
        tuning_layout.addRow("Max Tokens:", self.tokens_spin)
        layout.addWidget(tuning_group)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white; padding: 6px;")
        save_btn.clicked.connect(self.save_settings)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _on_provider_changed(self, index):
        self.provider_stack.setCurrentIndex(index)

    def _provider_key(self):
        return _PROVIDERS[self.provider_combo.currentIndex()][1]

    def load_settings(self):
        # 1. Load stored API keys from environment or .env
        env_keys = {
            "ANTHROPIC_API_KEY": "",
            "GEMINI_API_KEY": "",
            "KIMI_API_KEY": "",
        }
        
        for k in env_keys:
            env_keys[k] = os.environ.get(k, "")

        if os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        for k in env_keys:
                            if clean_line.startswith(f"{k}="):
                                env_keys[k] = clean_line.split("=", 1)[1].strip().strip('"').strip("'")
            except Exception as e:
                print(f"Error reading .env: {e}")

        # Set key inputs
        self.api_key_input.setText(env_keys["ANTHROPIC_API_KEY"])
        self.gemini_key_input.setText(env_keys["GEMINI_API_KEY"])
        self.kimi_key_input.setText(env_keys["KIMI_API_KEY"])

        if env_keys["ANTHROPIC_API_KEY"]:
            self.key_status_label.setText("✓ Anthropic API key loaded.")
            self.key_status_label.setStyleSheet("color: #4caf50; font-style: normal; font-weight: bold;")
        else:
            self.key_status_label.setText("⚠ No Claude API key found.")
            self.key_status_label.setStyleSheet("color: #f44336; font-style: normal; font-weight: bold;")

        # 2. Load settings from JSON
        model = "claude-opus-4-8"
        temp = 0.2
        tokens = 4000
        provider = PROVIDER_GEMINI
        ollama_model = "qwen2.5:7b"
        
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    model = data.get("model", model)
                    temp = data.get("temperature", temp)
                    tokens = data.get("max_tokens", tokens)
                    provider = data.get("ai_provider", provider)
                    ollama_model = data.get("ollama_model", ollama_model)
            except Exception as e:
                print(f"Error loading gui settings: {e}")
                
        # Apply to controls
        idx = self.model_combo.findText(model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        else:
            self.model_combo.setEditText(model)
            
        self.temp_slider.setValue(int(temp * 100))
        self.temp_val_label.setText(f"{temp:.2f}")
        self.tokens_spin.setValue(tokens)
        self.ollama_model_input.setText(ollama_model)
        
        provider_idx = next((i for i, (_, k) in enumerate(_PROVIDERS) if k == provider), 0)
        self.provider_combo.setCurrentIndex(provider_idx)
        self._on_provider_changed(provider_idx)

    def save_settings(self):
        # 1. Save API Keys to .env
        api_keys = {
            "ANTHROPIC_API_KEY": self.api_key_input.text().strip(),
            "GEMINI_API_KEY": self.gemini_key_input.text().strip(),
            "KIMI_API_KEY": self.kimi_key_input.text().strip(),
        }
        
        # Read existing .env lines to preserve other vars
        env_lines = []
        replaced = set()
        if os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        matched = False
                        for var, val in api_keys.items():
                            if line.strip().startswith(f"{var}="):
                                env_lines.append(f"{var}={val}\n")
                                replaced.add(var)
                                matched = True
                                break
                        if not matched:
                            env_lines.append(line)
            except Exception as e:
                print(f"Error scanning .env before save: {e}")

        for var, val in api_keys.items():
            if var not in replaced and val:
                env_lines.append(f"{var}={val}\n")

        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            # Set to current environment
            for var, val in api_keys.items():
                os.environ[var] = val
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write .env file:\n{e}")
            return
            
        # 2. Save settings to JSON
        existing = {}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
                
        existing.update({
            "model": self.model_combo.currentText().strip(),
            "temperature": self.temp_slider.value() / 100.0,
            "max_tokens": self.tokens_spin.value(),
            "ai_provider": self._provider_key(),
            "ollama_model": self.ollama_model_input.text().strip()
        })
        
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save JSON settings:\n{e}")
            return
            
        QMessageBox.information(self, "Success", "Settings and tuning parameters saved successfully!")
        self.accept()

    @staticmethod
    def get_tuning_params(project_root):
        """Helper to load tuning settings statically."""
        personal_settings = os.path.join(project_root, "personal", "data", "gui_settings.json")
        settings_path = personal_settings if os.path.exists(personal_settings) else os.path.join(project_root, "data", "gui_settings.json")
        params = {
            "model": "claude-opus-4-8",
            "temperature": 0.2,
            "max_tokens": 4000,
            "ai_provider": PROVIDER_GEMINI,
            "ollama_model": "qwen2.5:7b"
        }
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    params["model"] = data.get("model", params["model"])
                    params["temperature"] = data.get("temperature", params["temperature"])
                    params["max_tokens"] = data.get("max_tokens", params["max_tokens"])
                    params["ai_provider"] = data.get("ai_provider", params["ai_provider"])
                    params["ollama_model"] = data.get("ollama_model", params["ollama_model"])
            except:
                pass
        return params
