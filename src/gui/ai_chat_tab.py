import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                             QTextBrowser, QTextEdit, QPushButton, QLabel, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal as Signal

class AIChatTab(QWidget):
    # Emits dict with keys: 'section_key', 'user_prompt', 'current_text'
    chat_requested = Signal(dict)

    def __init__(self, project_root, editor_tab, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.editor_tab = editor_tab
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. Top Bar: Target Selection
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Target Section to Edit:"))
        self.section_combo = QComboBox()
        
        # Populate with available sections from the editor tab
        for section in self.editor_tab.sections:
            self.section_combo.addItem(section["title"], section["key"])
            
        top_bar.addWidget(self.section_combo)
        top_bar.addStretch()
        main_layout.addLayout(top_bar)

        # 2. Chat History Area
        history_label = QLabel("<b>AI Assistant Conversation</b>")
        main_layout.addWidget(history_label)
        
        self.chat_history = QTextBrowser()
        self.chat_history.setOpenExternalLinks(True)
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Inter', sans-serif;
                font-size: 14px;
            }
        """)
        self.append_message("System", "Ready to edit. Select a section above and tell me what you want to change.", "#8ab4f8")
        main_layout.addWidget(self.chat_history, stretch=3)

        # 3. Input Area
        input_label = QLabel("<b>Your Instruction</b>")
        main_layout.addWidget(input_label)
        
        input_layout = QHBoxLayout()
        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText("e.g. Rewrite this section to sound more confident...")
        self.prompt_input.setMaximumHeight(80)
        self.prompt_input.setStyleSheet("font-size: 14px; padding: 5px;")
        input_layout.addWidget(self.prompt_input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setMinimumHeight(80)
        self.send_btn.setMinimumWidth(100)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #8ab4f8;
                color: #121212;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #aecbfa;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.send_btn.clicked.connect(self.on_send_clicked)
        input_layout.addWidget(self.send_btn)
        
        main_layout.addLayout(input_layout)

    def append_message(self, sender, message, color="#ffffff"):
        html = f"<div style='margin-bottom: 10px;'><b><font color='{color}'>{sender}:</font></b><br>{message}</div>"
        self.chat_history.append(html)
        
        # Scroll to bottom
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def on_send_clicked(self):
        user_prompt = self.prompt_input.toPlainText().strip()
        if not user_prompt:
            return

        section_key = self.section_combo.currentData()
        
        # Get the current text from the editor cache/disk
        if section_key not in self.editor_tab.editors:
            QMessageBox.warning(self, "Error", "Selected section is not loaded in the Editor Tab.")
            return
            
        current_text = self.editor_tab.editors[section_key].toPlainText()
        if not current_text.strip():
            QMessageBox.warning(self, "Error", "The selected section is currently empty. Please generate it first.")
            return

        self.append_message("You", user_prompt, "#ffffff")
        self.prompt_input.clear()
        self.send_btn.setEnabled(False)
        self.append_message("System", "<i>Sending request to Gemini...</i>", "#aaaaaa")

        self.chat_requested.emit({
            'section_key': section_key,
            'user_prompt': user_prompt,
            'current_text': current_text
        })

    def on_chat_finished(self, success, section_key, error_msg=""):
        self.send_btn.setEnabled(True)
        if success:
            section_title = [s["title"] for s in self.editor_tab.sections if s["key"] == section_key][0]
            self.append_message("Gemini", f"Successfully updated <b>{section_title}</b>. The changes have been applied and the PDF is recompiling.", "#81c995")
        else:
            self.append_message("Error", f"Failed to update section: {error_msg}", "#f28b82")
