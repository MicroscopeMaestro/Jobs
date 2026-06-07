import os
import re
import requests
import html2text
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QComboBox, QCheckBox, 
                             QPushButton, QScrollArea, QGroupBox, QGridLayout,
                             QRadioButton, QButtonGroup, QSpinBox, QMessageBox,
                             QListWidget, QProgressBar, QFormLayout, QFrame, QDialog, QFileDialog)
from PySide6.QtCore import Qt, QThread, Signal as Signal

# --- Worker for fetching URL and extracting recipient block asynchronously ---
class FetchWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, url, text_input, generator, api_key, model):
        super().__init__()
        self.url = url
        self.text_input = text_input
        self.generator = generator
        self.api_key = api_key
        self.model = model

    def run(self):
        job_text = self.text_input
        
        # 1. Fetch from URL if provided
        if self.url:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; AppGenerator/1.0)"}
                resp = requests.get(url=self.url, headers=headers, timeout=15)
                resp.raise_for_status()
                converter = html2text.HTML2Text()
                converter.ignore_links = True
                converter.ignore_images = True
                job_text = converter.handle(resp.text)
            except Exception as e:
                self.error.emit(f"Failed to fetch job description URL:\n{e}")
                return
                
        if not job_text.strip():
            self.error.emit("Job description text is empty.")
            return
            
        # 2. Extract recipient details using Gemini if API key is provided
        result = {
            "job_text": job_text,
            "company": "",
            "contact_person": "Recruiting Team",
            "address": "",
            "job_title": ""
        }
        
        if self.api_key:
            try:
                extracted = self.generator.extract_recipient_details(self.api_key, job_text, self.model)
                result.update(extracted)
            except Exception as e:
                print(f"Error in recipient extraction thread: {e}")
                
        self.finished.emit(result)

class EditSkillsDialog(QDialog):
    def __init__(self, raw_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Skills Bank")
        self.resize(600, 450)
        self.init_ui(raw_text)

    def init_ui(self, raw_text):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "<b>Edit the Raw Skills Bank below:</b><br>"
            "Format: <code>**Category Name**: Skill 1 · Skill 2 · Skill 3</code><br>"
            "Use middle dots (·) as separators to keep the design clean and consistent."
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_label)
        
        self.editor = QTextEdit()
        self.editor.setPlainText(raw_text)
        self.editor.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #0f172a; color: #f8fafc;")
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save & Update Checklist")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; 
                color: white; 
                font-weight: bold; 
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #475569; 
                color: white; 
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.editor.toPlainText().strip()

class EditExamplesDialog(QDialog):
    def __init__(self, raw_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Professional Examples Bank")
        self.resize(650, 500)
        self.init_ui(raw_text)

    def init_ui(self, raw_text):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "<b>Edit the Raw Professional Examples Bank below:</b><br>"
            "Format:<br>"
            "<code>### EX-X · Example Title</code><br>"
            "<code>- **Where:** Institution/Company Name</code><br>"
            "<code>- **What:** What you achieved and how</code><br>"
            "<code>- **Skills demonstrated:** Skill 1, Skill 2, ...</code>"
        )
        info_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info_label)
        
        self.editor = QTextEdit()
        self.editor.setPlainText(raw_text)
        self.editor.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #0f172a; color: #f8fafc;")
        layout.addWidget(self.editor)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save & Update Checklist")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb; 
                color: white; 
                font-weight: bold; 
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #475569; 
                color: white; 
                padding: 6px 14px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.editor.toPlainText().strip()

class FormTab(QWidget):
    generation_requested = Signal(dict)

    def __init__(self, project_root, generator, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.generator = generator
        self.prompt_path = os.path.join(project_root, "data", "ai_application_prompt.md")
        self.assets_dir = os.path.join(project_root, "assets")
        
        self.example_checkboxes = []
        self.skills_list = []
        
        self.init_ui()
        self.load_data_from_prompt()
        self.scan_assets()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Scroll area for form controls to handle small screens
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 1. Job Description & Source URL
        job_group = QGroupBox("Job Information")
        job_layout = QVBoxLayout(job_group)
        
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Job URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/careers/job-posting-id")
        url_layout.addWidget(self.url_input)
        
        self.fetch_btn = QPushButton("Fetch & Parse Info")
        self.fetch_btn.setStyleSheet("font-weight: bold; background-color: #0d47a1; color: white;")
        self.fetch_btn.clicked.connect(self.on_fetch_clicked)
        url_layout.addWidget(self.fetch_btn)
        job_layout.addLayout(url_layout)
        
        desc_header_layout = QHBoxLayout()
        desc_header_layout.addWidget(QLabel("Job Description (Paste raw text or fetched contents):"))
        self.extract_btn = QPushButton("✨ Auto-Extract Details")
        self.extract_btn.setStyleSheet("font-weight: bold; background-color: #6d28d9; color: white;")
        desc_header_layout.addStretch()
        desc_header_layout.addWidget(self.extract_btn)
        job_layout.addLayout(desc_header_layout)
        
        self.job_desc_input = QTextEdit()
        self.job_desc_input.setMinimumHeight(150)
        self.job_desc_input.setPlaceholderText("Paste the job description or requirements here...")
        job_layout.addWidget(self.job_desc_input)
        
        # Progress bar for extraction
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        job_layout.addWidget(self.progress_bar)
        
        scroll_layout.addWidget(job_group)
        
        # 2. Target Profile (Title & Focus)
        profile_group = QGroupBox("Target Profile Tuning")
        profile_layout = QGridLayout(profile_group)
        
        profile_layout.addWidget(QLabel("Professional Title:"), 0, 0)
        self.title_combo = QComboBox()
        self.title_combo.setEditable(True)
        self.title_combo.addItems([
            "Optical Systems Engineer",
            "System Engineer",
            "Junior System Engineer",
            "Implementation Engineer",
            "Verification Engineer",
            "Machine Vision Engineer",
            "Quality Engineer Messtechnik"
        ])
        profile_layout.addWidget(self.title_combo, 0, 1)
        
        profile_layout.addWidget(QLabel("Motivation Letter Focus:"), 1, 0, Qt.AlignmentFlag.AlignTop)
        
        # Focus list (Flow layout modeled with Grid)
        self.focus_grid = QGridLayout()
        foci = ["Semiconductor", "Machine Vision", "System Engineering", 
                "Metrology", "Photonics/Laser", "Maintenance/Service", "R&D"]
        self.focus_checkboxes = []
        for i, focus in enumerate(foci):
            cb = QCheckBox(focus)
            self.focus_grid.addWidget(cb, i // 4, i % 4)
            self.focus_checkboxes.append(cb)
            
        profile_layout.addLayout(self.focus_grid, 1, 1)
        scroll_layout.addWidget(profile_group)
        
        # 3. Dynamic Examples Checklist
        self.examples_group = QGroupBox("Feature Professional Examples (Select 2-3)")
        self.examples_layout = QVBoxLayout(self.examples_group)
        
        # Dynamic Examples Adder (New Input for iterations)
        add_ex_widget = QWidget()
        add_ex_layout = QHBoxLayout(add_ex_widget)
        add_ex_layout.setContentsMargins(0, 8, 0, 0)
        
        self.custom_ex_id_input = QLineEdit("EX-12")
        self.custom_ex_id_input.setPlaceholderText("ID")
        self.custom_ex_id_input.setFixedWidth(60)
        
        self.custom_ex_title_input = QLineEdit()
        self.custom_ex_title_input.setPlaceholderText("Example Title...")
        
        self.custom_ex_summary_input = QLineEdit()
        self.custom_ex_summary_input.setPlaceholderText("Brief summary/description of experience...")
        
        add_ex_btn = QPushButton("Add Custom Example")
        add_ex_btn.clicked.connect(self.on_add_custom_example)
        
        edit_ex_bank_btn = QPushButton("✏ Edit Examples Bank")
        edit_ex_bank_btn.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: #f8fafc;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        edit_ex_bank_btn.clicked.connect(self.on_edit_examples_bank_clicked)
        
        add_ex_layout.addWidget(self.custom_ex_id_input)
        add_ex_layout.addWidget(self.custom_ex_title_input, 2)
        add_ex_layout.addWidget(self.custom_ex_summary_input, 4)
        add_ex_layout.addWidget(add_ex_btn, 1)
        add_ex_layout.addWidget(edit_ex_bank_btn, 1)
        
        self.examples_layout.addWidget(add_ex_widget)
        scroll_layout.addWidget(self.examples_group)
        
        # 4. Dynamic Skills Checklist + Custom Add Ribbon Sidebar
        skills_group = QGroupBox("Highlight Specific Skills")
        skills_h_layout = QHBoxLayout(skills_group)
        
        # Left Panel: Main skills checklist container
        self.skills_container = QWidget()
        self.skills_container_layout = QVBoxLayout(self.skills_container)
        self.skills_container_layout.setContentsMargins(0, 0, 0, 0)
        skills_h_layout.addWidget(self.skills_container, 3) # Stretch factor 3
        
        # Right Panel: Optional Ribbon (Sidebar) for adding skills/categories
        ribbon_widget = QFrame()
        ribbon_widget.setFrameShape(QFrame.Shape.StyledPanel)
        ribbon_widget.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 10px;
            }
            QLabel {
                font-weight: bold;
                color: #e2e8f0;
                border: none;
                background: transparent;
            }
            QLineEdit, QComboBox {
                background-color: #0f172a;
                border: 1px solid #475569;
                color: #f8fafc;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        ribbon_layout = QVBoxLayout(ribbon_widget)
        ribbon_layout.setSpacing(8)
        
        ribbon_title = QLabel("Add Skills Ribbon")
        ribbon_title.setStyleSheet("font-size: 13px; color: #3b82f6; font-weight: bold; border: none; background: transparent;")
        ribbon_layout.addWidget(ribbon_title)
        
        # Category Selector
        ribbon_layout.addWidget(QLabel("Skill Category:"))
        self.skill_category_combo = QComboBox()
        self.skill_category_combo.currentIndexChanged.connect(self.on_category_selection_changed)
        ribbon_layout.addWidget(self.skill_category_combo)
        
        # New Category Input
        self.new_cat_label = QLabel("New Category Name:")
        self.new_cat_label.setVisible(False)
        self.new_category_input = QLineEdit()
        self.new_category_input.setPlaceholderText("e.g. Deep Learning")
        self.new_category_input.setVisible(False)
        
        ribbon_layout.addWidget(self.new_cat_label)
        ribbon_layout.addWidget(self.new_category_input)
        
        # Skill Items Input
        ribbon_layout.addWidget(QLabel("Skill Items (comma-separated):"))
        self.skill_items_input = QLineEdit()
        self.skill_items_input.setPlaceholderText("e.g. PyTorch, TensorFlow")
        ribbon_layout.addWidget(self.skill_items_input)
        
        # Add Button
        add_skill_btn = QPushButton("Save & Integrate")
        add_skill_btn.clicked.connect(self.on_add_skill_ribbon_clicked)
        ribbon_layout.addWidget(add_skill_btn)
        
        # Edit Skills Bank Button
        edit_bank_btn = QPushButton("✏ Edit Skills Bank")
        edit_bank_btn.setStyleSheet("""
            QPushButton {
                background-color: #475569;
                color: #f8fafc;
                margin-top: 4px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        edit_bank_btn.clicked.connect(self.on_edit_skills_bank_clicked)
        ribbon_layout.addWidget(edit_bank_btn)
        
        # Spacer to push everything to the top
        ribbon_layout.addStretch()
        
        skills_h_layout.addWidget(ribbon_widget, 1) # Stretch factor 1
        scroll_layout.addWidget(skills_group)
        
        # 5. Experience Entry Customizers
        exp_group = QGroupBox("Resume Experience Section Entries")
        exp_layout = QVBoxLayout(exp_group)
        
        self.exp_entries = [
            {"id": "MUI", "name": "Medical University of Innsbruck (PhD)", "default_title": "Optical Systems Engineer | PhD Researcher"},
            {"id": "IPHT", "name": "Leibniz Institute of Photonic Technology (IPHT Jena)", "default_title": "R&D Research Assistant"},
            {"id": "INTECOL", "name": "INTECOL S.A.S. (Medellín, Colombia)", "default_title": "Junior Machine Vision Engineer (Field Service)"}
        ]
        
        self.exp_widgets = []
        for entry in self.exp_entries:
            row = QHBoxLayout()
            cb = QCheckBox(entry["name"])
            cb.setChecked(True)
            title_input = QLineEdit(entry["default_title"])
            row.addWidget(cb, 2)
            row.addWidget(QLabel("Job Title:"), 1)
            row.addWidget(title_input, 4)
            exp_layout.addLayout(row)
            self.exp_widgets.append((cb, title_input, entry))
            
        scroll_layout.addWidget(exp_group)
        
        # 6. Attachment Selection
        self.attachments_group = QGroupBox("Merge Attachment PDFs (from assets/)")
        attachments_main_layout = QVBoxLayout(self.attachments_group)
        
        btn_layout = QHBoxLayout()
        self.add_pdf_btn = QPushButton("➕ Add PDF Document")
        self.add_pdf_btn.clicked.connect(self.on_add_document)
        self.remove_pdf_btn = QPushButton("➖ Remove Selected")
        self.remove_pdf_btn.clicked.connect(self.on_remove_document)
        btn_layout.addWidget(self.add_pdf_btn)
        btn_layout.addWidget(self.remove_pdf_btn)
        btn_layout.addStretch()
        attachments_main_layout.addLayout(btn_layout)
        
        self.attachments_layout = QGridLayout()
        attachments_main_layout.addLayout(self.attachments_layout)
        
        scroll_layout.addWidget(self.attachments_group)
        
        # 7. Options: Language, Salary, Recipient Block, Page Limits
        options_group = QGroupBox("Application & Language Configuration")
        options_layout = QGridLayout(options_group)
        
        # Language Selection
        options_layout.addWidget(QLabel("Cover Letter Language:"), 0, 0)
        lang_layout = QHBoxLayout()
        self.lang_group = QButtonGroup(self)
        self.lang_de = QRadioButton("German (DE)")
        self.lang_de.setChecked(True)
        self.lang_en = QRadioButton("English (EN)")
        self.lang_auto = QRadioButton("Auto-Detect")
        self.lang_group.addButton(self.lang_de)
        self.lang_group.addButton(self.lang_en)
        self.lang_group.addButton(self.lang_auto)
        lang_layout.addWidget(self.lang_de)
        lang_layout.addWidget(self.lang_en)
        lang_layout.addWidget(self.lang_auto)
        options_layout.addLayout(lang_layout, 0, 1)
        
        # Salary expectation
        options_layout.addWidget(QLabel("Salary line (e.g. €60,000 p.a. or 'omit'):"), 1, 0)
        self.salary_input = QLineEdit("omit")
        options_layout.addWidget(self.salary_input, 1, 1)
        
        # Page Limits
        options_layout.addWidget(QLabel("Target Resume Pages:"), 2, 0)
        self.page_limit_spin = QSpinBox()
        self.page_limit_spin.setRange(1, 4)
        self.page_limit_spin.setValue(2)
        options_layout.addWidget(self.page_limit_spin, 2, 1)
        
        # Humanize Option
        options_layout.addWidget(QLabel("Humanize Output:"), 3, 0)
        self.humanize_cb = QCheckBox("Apply natural human style (varied sentences, active voice, zero LLM jargon)")
        self.humanize_cb.setChecked(True)
        options_layout.addWidget(self.humanize_cb, 3, 1)
        
        scroll_layout.addWidget(options_group)
        
        # 8. Recipient Information Block
        rec_group = QGroupBox("Recipient Block Details")
        rec_layout = QFormLayout(rec_group)
        
        self.rec_company_input = QLineEdit()
        self.rec_contact_input = QLineEdit("Recruiting Team")
        self.rec_address_input = QLineEdit()
        
        rec_layout.addRow("Company Name:", self.rec_company_input)
        rec_layout.addRow("Contact Person:", self.rec_contact_input)
        rec_layout.addRow("Address / Location:", self.rec_address_input)
        scroll_layout.addWidget(rec_group)
        
        # Set up Scroll
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Large Action Button
        self.generate_btn = QPushButton("Generate Tailored Application")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: bold;
                background-color: #2e7d32;
                color: white;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.generate_btn.clicked.connect(self.on_generate_clicked)
        main_layout.addWidget(self.generate_btn)

    def load_data_from_prompt(self):
        """Parses ai_application_prompt.md dynamically to extract examples and skills."""
        self.skills_list = []
        self.examples_list = []
        
        # Clear existing example checkboxes from layout and self.example_checkboxes
        self.example_checkboxes = []
        while self.examples_layout.count() > 1:
            item = self.examples_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        if not os.path.exists(self.prompt_path):
            print(f"ai_application_prompt.md not found at {self.prompt_path}")
            return
            
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # 1. Parse Professional Examples Bank
            matches = re.finditer(r'###\s*(EX-\d+)\s*·?\s*(.*?)\n(.*?)(?=\n###|\n---|\Z)', content, re.DOTALL)
            max_ex_num = 11
            for m in matches:
                ex_id = m.group(1).strip()
                ex_title = m.group(2).strip()
                ex_body = m.group(3).strip()
                
                # Automatically track the maximum EX number to dynamically set the next ID
                ex_num_match = re.match(r'EX-(\d+)', ex_id)
                if ex_num_match:
                    max_ex_num = max(max_ex_num, int(ex_num_match.group(1)))
                
                # Extract first couple lines for the description label
                summary = ""
                for line in ex_body.split("\n"):
                    if line.strip().startswith("- **What:**"):
                        summary = line.replace("- **What:**", "").strip()
                        break
                if not summary:
                    summary = ex_body.split("\n")[0].strip()
                    
                self.examples_list.append((ex_id, ex_title, summary))
                
            # Populate examples checklist with custom layout supporting HTML rich text
            for ex_id, ex_title, summary in self.examples_list:
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 2, 0, 2)
                
                cb = QCheckBox()
                cb.setProperty("ex_id", ex_id)
                
                label = QLabel(f"<b>{ex_id}</b>: {ex_title} <font color='#a0aec0'><i>({summary[:90]}...)</i></font>")
                label.setTextFormat(Qt.TextFormat.RichText)
                
                # Enable click toggling on the label
                label.mousePressEvent = lambda event, checkbox=cb: checkbox.toggle()
                
                row_layout.addWidget(cb)
                row_layout.addWidget(label, 1)
                
                # Insert at the top (before the dynamic input adder layout)
                count = self.examples_layout.count()
                self.examples_layout.insertWidget(count - 1, row_widget)
                self.example_checkboxes.append(cb)
                
            # Set the next ID field dynamically
            if hasattr(self, "custom_ex_id_input"):
                self.custom_ex_id_input.setText(f"EX-{max_ex_num + 1}")
                
            # 2. Parse Skills Section
            self.load_skills_from_prompt()
            
        except Exception as e:
            print(f"Error parsing examples & skills: {e}")

    def load_skills_from_prompt(self):
        """Parses the skills section from ai_application_prompt.md and populates the UI checklist and Ribbon categories."""
        if not os.path.exists(self.prompt_path):
            return
            
        # Clear existing skill groupboxes in self.skills_container_layout
        while self.skills_container_layout.count():
            item = self.skills_container_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        self.skills_list = []
        categories_found = []
        category_map = {} # category_name -> list of skill strings
        
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            skills_match = re.search(r'##\s*MY\s*SKILLS\s*AT\s*A\s*GLANCE(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
            if skills_match:
                skills_block = skills_match.group(1).strip()
                for line in skills_block.split("\n"):
                    line = line.strip()
                    if line.startswith("**") and ":" in line:
                        category_part, skills_part = line.split(":", 1)
                        category = category_part.replace("**", "").strip()
                        
                        # Clean up remaining bold markers ** from the skills list part
                        skills_part_clean = skills_part.replace("**", "").strip()
                        
                        # Parse actual skills, splitting ONLY by middle dots and bullets (never commas!)
                        skills = [s.strip() for s in re.split(r'·|•', skills_part_clean) if s.strip()]
                        
                        if category in category_map:
                            category_map[category].extend(skills)
                        else:
                            category_map[category] = list(skills)
                            categories_found.append(category)
                            
            # Populate UI checklist using the merged categories
            for category in categories_found:
                skills = category_map[category]
                
                # De-duplicate skills while preserving order
                seen = set()
                unique_skills = []
                for s in skills:
                    if s not in seen:
                        seen.add(s)
                        unique_skills.append(s)
                
                # Create dynamic box
                cat_group = QGroupBox(category)
                cat_layout = QGridLayout(cat_group)
                for idx, s in enumerate(unique_skills):
                    widget = QWidget()
                    h_layout = QHBoxLayout(widget)
                    h_layout.setContentsMargins(0, 0, 0, 0)
                    
                    cb = QCheckBox(s)
                    cb.setChecked(True)
                    
                    combo = QComboBox()
                    combo.addItems(["Knowledge", "Expertise"])
                    
                    h_layout.addWidget(cb)
                    h_layout.addWidget(combo)
                    
                    cat_layout.addWidget(widget, idx // 2, idx % 2)
                    self.skills_list.append((cb, category, combo))
                    
                self.skills_container_layout.addWidget(cat_group)
                        
            # Populate the categories combobox in the sidebar ribbon dynamically
            if hasattr(self, "skill_category_combo"):
                # Temporarily block signals to prevent triggering selection changed
                self.skill_category_combo.blockSignals(True)
                self.skill_category_combo.clear()
                self.skill_category_combo.addItems(categories_found)
                self.skill_category_combo.addItem("[Create New Category...]")
                self.skill_category_combo.blockSignals(False)
                # Reset display of custom category input
                self.on_category_selection_changed(self.skill_category_combo.currentIndex())
                
        except Exception as e:
            print(f"Error loading skills dynamically: {e}")

    def on_category_selection_changed(self, index):
        selected = self.skill_category_combo.currentText()
        is_new = (selected == "[Create New Category...]")
        self.new_cat_label.setVisible(is_new)
        self.new_category_input.setVisible(is_new)

    def on_add_skill_ribbon_clicked(self):
        selected_cat = self.skill_category_combo.currentText()
        
        if selected_cat == "[Create New Category...]":
            category_name = self.new_category_input.text().strip()
            if not category_name:
                QMessageBox.warning(self, "Missing Category", "Please enter a name for the new skill category.")
                return
        else:
            category_name = selected_cat
            
        skills_raw = self.skill_items_input.text().strip()
        if not skills_raw:
            QMessageBox.warning(self, "Missing Skills", "Please enter one or more skills to add.")
            return
            
        # Parse comma or bullet separated skills
        new_skills = [s.strip() for s in re.split(r',|·|•', skills_raw) if s.strip()]
        if not new_skills:
            return
            
        # Persist to data/ai_application_prompt.md
        success = self.persist_skill_change(category_name, new_skills)
        if success:
            # Refresh skills list in the UI dynamically
            self.load_skills_from_prompt()
            self.skill_items_input.clear()
            self.new_category_input.clear()
            
            # Select the newly modified/added category
            idx = self.skill_category_combo.findText(category_name)
            if idx >= 0:
                self.skill_category_combo.setCurrentIndex(idx)
                
            QMessageBox.information(self, "Skills Saved", f"Successfully saved and integrated {len(new_skills)} skills under '{category_name}' for future applications!")
        else:
            QMessageBox.critical(self, "Error", "Failed to save the skills to data/ai_application_prompt.md.")

    def on_edit_skills_bank_clicked(self):
        if not os.path.exists(self.prompt_path):
            QMessageBox.warning(self, "Missing Prompt File", f"Career prompt file not found at {self.prompt_path}")
            return
            
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            skills_match = re.search(r'##\s*MY\s*SKILLS\s*AT\s*A\s*GLANCE(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
            if not skills_match:
                QMessageBox.warning(self, "Parsing Error", "Could not locate the 'MY SKILLS AT A GLANCE' section in your prompt file.")
                return
                
            raw_text = skills_match.group(1).strip()
            
            dlg = EditSkillsDialog(raw_text, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_text = dlg.get_text()
                
                # Replace back in the prompt file
                updated_content = content[:skills_match.start(1)] + "\n" + new_text + "\n" + content[skills_match.end(1):]
                
                with open(self.prompt_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                    
                # Reload skills in checklist
                self.load_skills_from_prompt()
                QMessageBox.information(self, "Success", "Skills bank successfully updated and synced!")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit skills bank:\n{e}")

    def on_edit_examples_bank_clicked(self):
        if not os.path.exists(self.prompt_path):
            QMessageBox.warning(self, "Missing Prompt File", f"Career prompt file not found at {self.prompt_path}")
            return
            
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            examples_match = re.search(r'##\s*PERSONAL\s*EXAMPLES\s*BANK(.*?)(?=\n---|\Z)', content, re.DOTALL)
            if not examples_match:
                QMessageBox.warning(self, "Parsing Error", "Could not locate the 'PERSONAL EXAMPLES BANK' section in your prompt file.")
                return
                
            raw_text = examples_match.group(1).strip()
            
            dlg = EditExamplesDialog(raw_text, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                new_text = dlg.get_text()
                
                # Replace back in the prompt file
                updated_content = content[:examples_match.start(1)] + "\n" + new_text + "\n" + content[examples_match.end(1):]
                
                with open(self.prompt_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                    
                # Reload examples bank in checklist
                self.load_data_from_prompt()
                QMessageBox.information(self, "Success", "Professional examples bank successfully updated and synced!")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to edit professional examples bank:\n{e}")

    def persist_skill_change(self, category_name, new_skills_list):
        """Appends new skills to an existing or new category in data/ai_application_prompt.md."""
        if not os.path.exists(self.prompt_path):
            return False
            
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Locate ## MY SKILLS AT A GLANCE section
            skills_section_match = re.search(r'(##\s*MY\s*SKILLS\s*AT\s*A\s*GLANCE\n+)(.*?)(?=\n+---|\Z)', content, re.DOTALL)
            if not skills_section_match:
                return False
                
            section_header = skills_section_match.group(1)
            section_body = skills_section_match.group(2)
            
            # Check if category already exists in the text (allowing colon inside or outside bolding)
            category_pattern = rf'\*\*{re.escape(category_name)}(?::\*\*|\*\*)\s*(?::\s*)?(.*?)(?=\n|\Z)'
            category_match = re.search(category_pattern, section_body)
            
            if category_match:
                # Category exists! Append to the existing skills list cleanly
                matched_line = category_match.group(0)
                existing_skills = category_match.group(1).strip()
                
                # Clean up existing_skills from any closing bold markers or spaces
                existing_skills = existing_skills.replace("**", "").strip()
                
                # Parse existing skills to prevent adding duplicates
                existing_skills_list = [s.strip() for s in re.split(r'·|•', existing_skills) if s.strip()]
                filtered_new_skills = [s for s in new_skills_list if s not in existing_skills_list]
                
                if filtered_new_skills:
                    skills_str_to_add = " · ".join(filtered_new_skills)
                    if existing_skills:
                        updated_line = f"**{category_name}:** {existing_skills} · {skills_str_to_add}"
                    else:
                        updated_line = f"**{category_name}:** {skills_str_to_add}"
                else:
                    updated_line = f"**{category_name}:** {existing_skills}"
                
                # Replace the exact matched line in section_body
                new_section_body = section_body.replace(matched_line, updated_line)
            else:
                # Category does not exist! Append as a new line at the end of the skills list
                skills_str_to_add = " · ".join(new_skills_list)
                cleaned_body = section_body.rstrip()
                new_line = f"\n**{category_name}:** {skills_str_to_add}"
                new_section_body = cleaned_body + new_line
                
            # Replace the old section body with the new one in content
            start_idx = skills_section_match.start(2)
            end_idx = skills_section_match.end(2)
            new_content = content[:start_idx] + new_section_body + content[end_idx:]
            
            with open(self.prompt_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return True
        except Exception as e:
            print(f"Error persisting skills to file: {e}")
            return False

    def persist_custom_example(self, ex_id, title, summary):
        """Saves a new custom example to the personal examples bank in data/ai_application_prompt.md."""
        if not os.path.exists(self.prompt_path):
            return False
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                prompt_content = f.read()
            
            # We want to find the last occurrence of ### EX-XX block, 
            # and insert the new EX block right after its body, before the separator "---".
            # Let's find all "### EX-" blocks to locate the end of the last one.
            ex_matches = list(re.finditer(r'###\s*EX-\d+.*?(?=\n###|\n---)', prompt_content, re.DOTALL))
            if ex_matches:
                last_match = ex_matches[-1]
                insert_pos = last_match.end()
                
                # Construct new block
                new_block = f"\n\n### {ex_id} · {title}\n- **Where:** Custom\n- **What:** {summary}\n- **Skills demonstrated:** Custom\n- **Use when:** Custom"
                
                new_content = prompt_content[:insert_pos] + new_block + prompt_content[insert_pos:]
                
                with open(self.prompt_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                return True
        except Exception as e:
            print(f"Failed to persist custom example to prompt file: {e}")
        return False

    def on_add_custom_example(self):
        ex_id = self.custom_ex_id_input.text().strip()
        title = self.custom_ex_title_input.text().strip()
        summary = self.custom_ex_summary_input.text().strip()
        
        if not ex_id or not title:
            QMessageBox.warning(self, "Input Required", "Example ID and Title are required to add a custom entry.")
            return
            
        # Persist to data/ai_application_prompt.md first
        persisted = self.persist_custom_example(ex_id, title, summary)
        if not persisted:
            QMessageBox.warning(self, "File Save Warning", "Could not persist custom example to data/ai_application_prompt.md, but adding to current session checklist.")
            
        # Create beautiful rich text row
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 2, 0, 2)
        
        cb = QCheckBox()
        cb.setChecked(True) # Auto-checked on add
        cb.setProperty("ex_id", ex_id)
        
        label = QLabel(f"<b>{ex_id}</b>: {title} <font color='#a0aec0'><i>({summary[:90]}...)</i></font>")
        label.setTextFormat(Qt.TextFormat.RichText)
        label.mousePressEvent = lambda event, checkbox=cb: checkbox.toggle()
        
        row_layout.addWidget(cb)
        row_layout.addWidget(label, 1)
        
        # Insert before the adder widget (last item in examples layout)
        count = self.examples_layout.count()
        self.examples_layout.insertWidget(count - 1, row_widget)
        self.example_checkboxes.append(cb)
        
        # Clear fields
        self.custom_ex_title_input.clear()
        self.custom_ex_summary_input.clear()
        
        # Auto-compute next ID
        match = re.match(r'EX-(\d+)', ex_id)
        if match:
            next_num = int(match.group(1)) + 1
            self.custom_ex_id_input.setText(f"EX-{next_num}")
            
        QMessageBox.information(self, "Success", f"Custom example {ex_id} successfully added to the checklist and saved permanently for future applications!")

    def scan_assets(self):
        """Scans the assets directory and populates the attachment PDF checklist."""
        # Clear existing layout
        while self.attachments_layout.count():
            child = self.attachments_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Attachments categorization matching main.py
        self.categories = {
            "professional_experience": ["intecol_english.pdf", "intecol_german.pdf", "intecol_spanish.pdf", "IPHT0.pdf", "IPHT1.pdf"],
            "education": ["Bachelor Diploma.pdf", "master.pdf"],
            "certificates": ["B2.pdf", "Mündliche_test.pdf", "ASML_School.pdf", "Zeiss_Summer_School.pdf", "ASLM_invitation.pdf"],
            "others": ["resident_permit.pdf", "passport.pdf"]
        }
        
        self.attachment_checkboxes = []
        
        # List of actual files in assets directory
        actual_files = []
        if os.path.exists(self.assets_dir):
            try:
                actual_files = [f for f in os.listdir(self.assets_dir) if f.lower().endswith(".pdf")]
            except Exception as e:
                print(f"Error reading assets directory: {e}")
                
        # Group and build checklist
        col = 0
        handled_files = set()
        
        for cat_name, filenames in self.categories.items():
            cat_group = QGroupBox(cat_name.replace("_", " ").title())
            cat_layout = QVBoxLayout(cat_group)
            
            for fname in filenames:
                if fname in actual_files:
                    handled_files.add(fname)
                    cb = QCheckBox(fname)
                    # Check defaults according to main.py
                    if fname in ["intecol_english.pdf", "Bachelor Diploma.pdf", "master.pdf", "B2.pdf", "Mündliche_test.pdf", "resident_permit.pdf"]:
                        cb.setChecked(True)
                    cb.setProperty("category", cat_name)
                    cb.setProperty("filename", fname)
                    cat_layout.addWidget(cb)
                    self.attachment_checkboxes.append(cb)
            
            self.attachments_layout.addWidget(cat_group, 0, col)
            col += 1
            
        uncategorized = [f for f in actual_files if f not in handled_files]
        if uncategorized:
            cat_group = QGroupBox("Uncategorized PDFs")
            cat_layout = QVBoxLayout(cat_group)
            for fname in uncategorized:
                cb = QCheckBox(fname)
                cb.setProperty("category", "others")
                cb.setProperty("filename", fname)
                cat_layout.addWidget(cb)
                self.attachment_checkboxes.append(cb)
            self.attachments_layout.addWidget(cat_group, 0, col)
            col += 1

    def on_add_document(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select PDF Document", "", "PDF Files (*.pdf)")
        if file_path:
            os.makedirs(self.assets_dir, exist_ok=True)
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.assets_dir, filename)
            try:
                shutil.copy2(file_path, dest_path)
                self.scan_assets()
                QMessageBox.information(self, "Success", f"Document '{filename}' added successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add document:\n{e}")

    def on_remove_document(self):
        to_remove = [cb for cb in self.attachment_checkboxes if cb.isChecked()]
        if not to_remove:
            QMessageBox.warning(self, "No Selection", "Please check the documents you want to remove.")
            return
            
        confirm = QMessageBox.question(self, "Confirm Removal", f"Are you sure you want to permanently delete {len(to_remove)} document(s) from the assets directory?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for cb in to_remove:
                filename = cb.property("filename")
                file_path = os.path.join(self.assets_dir, filename)
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")
            self.scan_assets()
            QMessageBox.information(self, "Success", f"Successfully removed {deleted_count} document(s)!")

    def on_fetch_clicked(self):
        url = self.url_input.text().strip()
        job_text = self.job_desc_input.toPlainText().strip()
        
        if not url and not job_text:
            QMessageBox.warning(self, "Input Required", "Please enter a Job URL or paste a Job Description first.")
            return
            
        # Try to read GEMINI_API_KEY from environment to auto-extract recipient block
        from .settings_dialog import SettingsDialog
        tuning = SettingsDialog.get_tuning_params(self.project_root)
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        
        # Start async worker
        self.fetch_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat("Fetching and extracting recipient blocks...")
        
        self.worker = FetchWorker(url, job_text, self.generator, api_key, tuning["model"])
        self.worker.finished.connect(self.on_fetch_finished)
        self.worker.error.connect(self.on_fetch_error)
        self.worker.start()

    def on_fetch_finished(self, result):
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        # Paste job text
        self.job_desc_input.setPlainText(result["job_text"])
        
        # Populate recipient block
        if result["company"]:
            self.rec_company_input.setText(result["company"])
        if result["contact_person"]:
            self.rec_contact_input.setText(result["contact_person"])
        if result["address"]:
            self.rec_address_input.setText(result["address"])
            
        # Try to set Professional Title if matched
        if result["job_title"]:
            title = result["job_title"]
            # Look for exact dropdown matches
            idx = self.title_combo.findText(title)
            if idx >= 0:
                self.title_combo.setCurrentIndex(idx)
            else:
                self.title_combo.setEditText(title)
                
            QMessageBox.information(self, "Success", f"Job posting parsed successfully!\n\nAuto-extracted recipient details for:\n{result['company']} - {title}")

    def on_fetch_error(self, err_msg):
        self.fetch_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Extraction Error", err_msg)

    def on_generate_clicked(self):
        # 1. Validate Job Description
        job_desc = self.job_desc_input.toPlainText().strip()
        if not job_desc:
            QMessageBox.warning(self, "Missing Job Description", "The job description field is required to guide Gemini's generation.")
            return
            
        # 2. Gather Focus Themes
        selected_focus = []
        for cb in self.focus_checkboxes:
            if cb.isChecked():
                selected_focus.append(cb.text())
                
        # 3. Gather selected Examples
        selected_examples = []
        for cb in self.example_checkboxes:
            if cb.isChecked():
                selected_examples.append(cb.property("ex_id"))
                
        # 4. Gather selected Skills
        selected_skills = []
        for cb, cat, combo in self.skills_list:
            if cb.isChecked():
                selected_skills.append({
                    "name": cb.text(),
                    "level": combo.currentText()
                })
                
        # 5. Gather Experience Entries
        exp_entries = []
        for cb, title_input, entry in self.exp_widgets:
            exp_entries.append({
                "id": entry["id"],
                "name": entry["name"],
                "enabled": cb.isChecked(),
                "title": title_input.text().strip()
            })
            
        # 6. Gather selected Attachments mapping
        attachments_map = {
            "professional_experience": [],
            "education": [],
            "certificates": [],
            "others": []
        }
        for cb in self.attachment_checkboxes:
            if cb.isChecked():
                cat = cb.property("category")
                filename = cb.property("filename")
                attachments_map[cat].append(filename)
                
        # 7. Get Lang
        lang = "de"
        if self.lang_en.isChecked():
            lang = "en"
        elif self.lang_auto.isChecked():
            lang = "auto"
            
        # Compile parameter dict
        params = {
            "job_description": job_desc,
            "title": self.title_combo.currentText().strip(),
            "focus": selected_focus,
            "examples": selected_examples,
            "skills": selected_skills,
            "experience": exp_entries,
            "attachments": attachments_map,
            "language": lang,
            "salary": self.salary_input.text().strip(),
            "recipient_company": self.rec_company_input.text().strip(),
            "recipient_contact": self.rec_contact_input.text().strip(),
            "recipient_address": self.rec_address_input.text().strip(),
            "page_limit": self.page_limit_spin.value(),
            "humanize": self.humanize_cb.isChecked()
        }
        
        self.generation_requested.emit(params)
