import os
import json
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QSlider, QSpinBox, QPushButton, 
                             QLineEdit, QMessageBox, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None, project_root=""):
        super().__init__(parent)
        self.project_root = project_root
        self.settings_path = os.path.join(project_root, "data", "gui_settings.json")
        self.env_path = os.path.join(project_root, ".env")
        
        self.setWindowTitle("Gemini Settings & Tuning")
        self.setMinimumWidth(450)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. API Configuration Group
        api_group = QGroupBox("Google Gemini API Credentials")
        api_layout = QFormLayout(api_group)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Paste GEMINI_API_KEY here...")
        
        self.key_status_label = QLabel("Loading status...")
        self.key_status_label.setStyleSheet("font-style: italic;")
        
        api_layout.addRow("API Key:", self.api_key_input)
        api_layout.addRow("", self.key_status_label)
        layout.addWidget(api_group)
        
        # 2. Generation Tuning Group
        tuning_group = QGroupBox("Gemini Generation Parameters")
        tuning_layout = QFormLayout(tuning_group)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "gemini-3.5-flash",
            "antigravity-preview-05-2026",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash"
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
        self.tokens_spin.setRange(1000, 8000)
        self.tokens_spin.setSingleStep(500)
        self.tokens_spin.setValue(4000)
        
        tuning_layout.addRow("Gemini Model:", self.model_combo)
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

    def load_settings(self):
        # 1. Load API Key from environment or .env
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        
        if not api_key and os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line.startswith("GEMINI_API_KEY="):
                            api_key = clean_line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
                        elif clean_line.startswith("GOOGLE_API_KEY="):
                            api_key = clean_line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception as e:
                print(f"Error reading .env: {e}")
                
        if api_key:
            self.api_key_input.setText(api_key)
            self.key_status_label.setText("✓ Integrated key loaded (using Antigravity default)")
            self.key_status_label.setStyleSheet("color: #4caf50; font-style: normal; font-weight: bold;")
        else:
            self.key_status_label.setText("⚠ No API key found. Please supply key to generate.")
            self.key_status_label.setStyleSheet("color: #f44336; font-style: normal; font-weight: bold;")

        # 2. Load model params from JSON
        model = "gemini-3.5-flash"
        temp = 0.2
        tokens = 4000
        
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    model = data.get("model", model)
                    temp = data.get("temperature", temp)
                    tokens = data.get("max_tokens", tokens)
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

    def save_settings(self):
        # 1. Save API Key to .env
        api_key = self.api_key_input.text().strip()
        
        # Read existing .env lines to preserve other vars
        env_lines = []
        key_replaced = False
        if os.path.exists(self.env_path):
            try:
                with open(self.env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line.startswith("GEMINI_API_KEY="):
                            env_lines.append(f"GEMINI_API_KEY={api_key}\n")
                            key_replaced = True
                        elif clean_line.startswith("GOOGLE_API_KEY="):
                            env_lines.append(f"GOOGLE_API_KEY={api_key}\n")
                            key_replaced = True
                        else:
                            env_lines.append(line)
            except Exception as e:
                print(f"Error scanning .env before save: {e}")
                
        if not key_replaced and api_key:
            env_lines.append(f"GEMINI_API_KEY={api_key}\n")
            
        try:
            with open(self.env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            # Set to current environment
            os.environ["GEMINI_API_KEY"] = api_key
            os.environ["GOOGLE_API_KEY"] = api_key
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write .env file:\n{e}")
            return
            
        # 2. Save other settings to JSON
        settings_data = {
            "model": self.model_combo.currentText().strip(),
            "temperature": self.temp_slider.value() / 100.0,
            "max_tokens": self.tokens_spin.value()
        }
        
        try:
            os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save JSON settings:\n{e}")
            return
            
        QMessageBox.information(self, "Success", "Settings and tuning parameters saved successfully!")
        self.accept()

    @staticmethod
    def get_tuning_params(project_root):
        """Helper to load tuning settings statically."""
        settings_path = os.path.join(project_root, "data", "gui_settings.json")
        params = {
            "model": "gemini-3.5-flash",
            "temperature": 0.2,
            "max_tokens": 4000
        }
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    params["model"] = data.get("model", params["model"])
                    params["temperature"] = data.get("temperature", params["temperature"])
                    params["max_tokens"] = data.get("max_tokens", params["max_tokens"])
            except:
                pass
        return params
