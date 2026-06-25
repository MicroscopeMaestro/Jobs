import os
import requests
import re
import glob
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTabWidget, QTextEdit,
                             QSplitter, QComboBox, QMessageBox, QScrollArea)
from PySide6.QtGui import (QPixmap, QImage, QSyntaxHighlighter, QTextCharFormat, QColor)
from PySide6.QtCore import Qt, Signal as Signal, QThread, QTimer
import fitz  # PyMuPDF

def get_user_name(project_root):
    personal_dir = os.path.join(project_root, "personal")
    if os.path.exists(personal_dir):
        return "Juan_Munoz"
    return "John_Doe"

class GrammarCheckWorker(QThread):
    # NOTE: do NOT name this "finished" — that shadows QThread.finished, which
    # fires only after run() returns. A custom "finished" emits from inside run()
    # (thread still running); dropping the worker's last ref on it lets Python GC
    # destroy a live QThread -> Qt qFatal("QThread: Destroyed while running").
    results_ready = Signal(list)

    def __init__(self, text, language="auto"):
        super().__init__()
        self.text = text
        self.language = language
        
    def run(self):
        try:
            # Mask LaTeX commands so they are ignored by LanguageTool, 
            # keeping exact string length so offsets match!
            masked_text = re.sub(r'\\[a-zA-Z]+', lambda m: ' ' * len(m.group(0)), self.text)
            masked_text = masked_text.replace('{', ' ').replace('}', ' ')
            masked_text = masked_text.replace('&', ' ').replace('|', ' ')
            masked_text = re.sub(r'%.*', lambda m: ' ' * len(m.group(0)), masked_text)
            
            response = requests.post(
                "https://api.languagetool.org/v2/check",
                data={
                    "text": masked_text,
                    "language": self.language
                },
                timeout=4
            )
            if response.status_code == 200:
                data = response.json()
                errors = []
                for match in data.get("matches", []):
                    rule_type = match.get("rule", {}).get("issueType", "grammar")
                    errors.append({
                        "offset": match["offset"],
                        "length": match["length"],
                        "type": rule_type,
                        "message": match["message"],
                        "replacements": match.get("replacements", [])
                    })
                self.results_ready.emit(errors)
            else:
                self.results_ready.emit([])
        except Exception:
            # Silently fail if offline or API is down
            self.results_ready.emit([])

class LatexAndGrammarHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.errors = []
        
        # Define LaTeX highlighting rules
        self.rules = []
        
        # 1. Commands (e.g., \section, \textbf, \entry)
        cmd_format = QTextCharFormat()
        cmd_format.setForeground(QColor("#7dd3fc")) # Light Blue
        self.rules.append((re.compile(r'\\[a-zA-Z]+'), cmd_format))
        
        # 2. Braces {}
        brace_format = QTextCharFormat()
        brace_format.setForeground(QColor("#f472b6")) # Pink
        self.rules.append((re.compile(r'[{}]'), brace_format))
        
        # 3. Comments %
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#94a3b8")) # Gray
        self.rules.append((re.compile(r'%.*'), comment_format))
        
    def update_errors(self, errors):
        self.errors = errors
        self.rehighlight()
        
    def highlightBlock(self, text):
        # Apply LaTeX syntax rules first
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
                
        # Apply Grammar/Spelling overlays
        block_pos = self.currentBlock().position()
        block_length = self.currentBlock().length()
        
        for err in self.errors:
            err_start = err['offset']
            err_end = err_start + err['length']
            
            # Check intersection
            if err_start < block_pos + block_length and err_end > block_pos:
                local_start = max(0, err_start - block_pos)
                local_length = min(block_length - local_start, err_end - (block_pos + local_start))
                
                # Fetch existing format to preserve foreground color if it was LaTeX
                fmt = self.format(local_start)
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
                
                if err['type'] == 'misspelling':
                    fmt.setUnderlineColor(QColor("#ef4444")) # Red
                else:
                    fmt.setUnderlineColor(QColor("#3b82f6")) # Blue
                    
                fmt.setToolTip(err['message'])
                self.setFormat(local_start, local_length, fmt)

class RichTextEditor(QTextEdit):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.grammar_lang = "auto"
        self.font_size = 15
        
        self.apply_typography()
        
    def apply_typography(self):
        self.setStyleSheet(f"font-family: 'Courier New', Courier, monospace; font-size: {self.font_size}px; background-color: #0f172a; color: #f8fafc; padding: 25px; border: none; border-radius: 4px;")
        
        self.highlighter = LatexAndGrammarHighlighter(self.document())
        
        # Debounced grammar checking
        self.check_timer = QTimer(self)
        self.check_timer.setInterval(1500) # Wait 1.5s after typing
        self.check_timer.setSingleShot(True)
        self.check_timer.timeout.connect(self.run_grammar_check)
        
        self.textChanged.connect(self.on_text_changed)
        self.worker = None
        self._old_workers = set()

    def on_text_changed(self):
        self.check_timer.start()
        
    def run_grammar_check(self):
        text = self.toPlainText()
        if not text.strip():
            return

        # Keep a strong reference to every worker until the OS thread has fully
        # stopped. Pruning only non-running workers (on the main thread) means a
        # reference is never dropped while run() is mid-flight, so Python GC can
        # never destroy a live QThread.
        if self.worker is not None:
            self._old_workers.add(self.worker)
        self._old_workers = {w for w in self._old_workers if w.isRunning()}

        self.worker = GrammarCheckWorker(text, self.grammar_lang)
        self.worker.results_ready.connect(self.highlighter.update_errors)
        self.worker.start()

    def set_font_size(self, size):
        self.font_size = size
        self.apply_typography()
        
    def set_language(self, lang):
        self.grammar_lang = lang
        self.run_grammar_check()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        
        active_err = None
        for err in self.highlighter.errors:
            if err['offset'] <= pos <= err['offset'] + err['length']:
                active_err = err
                break
                
        if active_err:
            msg_action = menu.addAction(f"ℹ {active_err['message']}")
            msg_action.setEnabled(False)
            
            if active_err['replacements']:
                menu.insertSeparator(menu.actions()[0])
                for rep in active_err['replacements'][:5]:
                    val = rep['value']
                    action = menu.addAction(f"✨ {val}")
                    action.triggered.connect(lambda checked, v=val, e=active_err: self.apply_correction(e, v))
                menu.insertSeparator(menu.actions()[0])
                
        menu.exec(event.globalPos())

    def apply_correction(self, err, value):
        cursor = self.textCursor()
        cursor.setPosition(err['offset'])
        cursor.setPosition(err['offset'] + err['length'], cursor.MoveMode.KeepAnchor)
        cursor.insertText(value)
        self.save_to_disk()

    def load_from_disk(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.setPlainText(content)
            
            # Apply comfortable line height and paragraph spacing
            cursor = self.textCursor()
            cursor.select(cursor.SelectionType.Document)
            block_fmt = cursor.blockFormat()
            block_fmt.setLineHeight(150, 1) # 1 corresponds to QTextBlockFormat.LineHeightTypes.ProportionalHeight
            block_fmt.setBottomMargin(10)
            cursor.setBlockFormat(block_fmt)
            cursor.clearSelection()
            self.setTextCursor(cursor)
            
            self.document().setModified(False)
            self.run_grammar_check()

    def save_to_disk(self):
        content = self.toPlainText()
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.document().setModified(False)


class EditorTab(QWidget):
    recompile_requested = Signal(dict)
    ai_check_requested = Signal()

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.output_dir = os.path.join(project_root, "generated")
        # Exact path of the last full bundle compiled this session, so the
        # preview shows what was just built rather than the newest file on disk
        # (old/broken bundles from earlier runs would otherwise win by mtime).
        self.last_bundle_path = None

        self.pdf_doc = None
        self.current_page_index = 0
        self.zoom_factor = 1.0
        
        # Setup editable sections
        self.sections = [
            {"title": "ML Subject", "path": "templates/sections/ml/subject.tex", "key": "ml_subject"},
            {"title": "ML Recipient", "path": "templates/sections/ml/recipient.tex", "key": "ml_recipient"},
            {"title": "ML Body", "path": "templates/sections/ml/body.tex", "key": "ml_body"},
            {"title": "ML Closing", "path": "templates/sections/ml/closing.tex", "key": "ml_closing"},
            {"title": "Header", "path": "templates/sections/resume/header.tex", "key": "resume_header"},
            {"title": "Summary", "path": "templates/sections/resume/summary.tex", "key": "resume_summary"},
            {"title": "Experience", "path": "templates/sections/resume/experience.tex", "key": "resume_experience"},
            {"title": "Competencies", "path": "templates/sections/resume/technical_competencies.tex", "key": "resume_competencies"},
            {"title": "Education", "path": "templates/sections/resume/education.tex", "key": "resume_education"},
            {"title": "Soft Skills", "path": "templates/sections/resume/soft_skills.tex", "key": "resume_soft_skills"},
            {"title": "Languages", "path": "templates/sections/resume/languages.tex", "key": "resume_languages"},
        ]
        
        self.editors = {}
        self.generated_cache = {}
        
        self.init_ui()
        self.load_all_files()
        self.load_selected_pdf()

    def init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT PANE ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        
        top_bar = QHBoxLayout()
        title_label = QLabel("<b>Raw LaTeX Editor</b> (Syntax Highlighting & Grammar):")
        title_label.setStyleSheet("font-size: 14px;")
        
        self.font_size_cb = QComboBox()
        self.font_size_cb.addItems(["10", "12", "14", "16", "18", "20", "24"])
        self.font_size_cb.setCurrentText("14")
        self.font_size_cb.currentTextChanged.connect(self.on_font_size_changed)
        
        self.lang_cb = QComboBox()
        self.lang_cb.addItems(["Auto", "English", "German"])
        self.lang_cb.currentTextChanged.connect(self.on_language_changed)
        
        top_bar.addWidget(title_label)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Font Size:"))
        top_bar.addWidget(self.font_size_cb)
        top_bar.addWidget(QLabel("Language:"))
        top_bar.addWidget(self.lang_cb)
        
        left_layout.addLayout(top_bar)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                background: #e0e0e0;
                color: #333;
                padding: 8px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #fcfcfc;
                border: 1px solid #ccc;
                border-bottom-color: #fcfcfc;
                color: #0056b3;
            }
            QTabWidget::pane {
                border: 1px solid #ccc;
                background: #fcfcfc;
                border-radius: 4px;
            }
        """)
        self.tabs.setUsesScrollButtons(True)
        
        personal_dir = os.path.join(self.project_root, "personal")
        use_personal = os.path.exists(personal_dir)
        
        for i, sec in enumerate(self.sections):
            if use_personal:
                abs_path = os.path.join(personal_dir, sec["path"])
            else:
                abs_path = os.path.join(self.project_root, sec["path"])
            editor = RichTextEditor(abs_path)
            self.editors[sec["key"]] = editor
            self.tabs.addTab(editor, sec["title"])
            
            # Change text color for resume sections to distinguish them from ML sections
            if sec["key"].startswith("resume_"):
                self.tabs.tabBar().setTabTextColor(i, QColor("#16a34a")) # Green color for resume tabs
            else:
                self.tabs.tabBar().setTabTextColor(i, QColor("#2563eb")) # Blue color for ML tabs
            
        left_layout.addWidget(self.tabs)
        
        bottom_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset current tab to generated AI text")
        reset_btn.setStyleSheet("color: #d32f2f; font-size: 12px;")
        reset_btn.clicked.connect(self.on_reset_to_generated)
        bottom_layout.addWidget(reset_btn)
        bottom_layout.addStretch()
        
        recompile_layout = QHBoxLayout()
        recompile_layout.addWidget(QLabel("Document:"))
        self.pdf_selector = QComboBox()
        # label -> (compile target key, output filename | None for the bundle glob)
        user_name = get_user_name(self.project_root)
        self.PDF_TARGETS = [
            ("Resume", "resume", "resume.pdf"),
            ("Motivation Letter", "motivation_letter", "motivation_letter.pdf"),
            ("Motivation Letter & Resume", "motivation_letter_and_resume", "motivation_letter_and_resume.pdf"),
            ("Experience", "professional_experience", "professional_experience.pdf"),
            ("Education", "education", "education.pdf"),
            ("Certificates", "certificates", "certificates.pdf"),
            ("Other Documents", "others", "others.pdf"),
            ("All Attachments", "all_attachments", "all_attachments.pdf"),
            ("Personal Documents", "personal_documents", f"Passport_and_Resident_Permit_{user_name}.pdf"),
            ("Full Application Bundle", "full_bundle", None),
        ]
        self.pdf_selector.addItems([label for label, _, _ in self.PDF_TARGETS])
        self.pdf_selector.currentIndexChanged.connect(self.load_selected_pdf)
        recompile_layout.addWidget(self.pdf_selector)

        self.recompile_btn = QPushButton("Save & Compile")
        self.recompile_btn.setToolTip("Compile the document selected in the dropdown")
        self.recompile_btn.setStyleSheet("font-weight: bold; background-color: #0060df; color: white; padding: 6px 12px; border-radius: 4px;")
        self.recompile_btn.clicked.connect(self.on_recompile_clicked)
        recompile_layout.addWidget(self.recompile_btn)

        # On-demand AI proofreading (no longer runs automatically after compile)
        self.ai_check_btn = QPushButton("🤖 AI Check")
        self.ai_check_btn.setToolTip("Run an AI proofreading pass over the current document")
        self.ai_check_btn.setStyleSheet("font-weight: bold; background-color: #6d28d9; color: white; padding: 6px 12px; border-radius: 4px;")
        self.ai_check_btn.clicked.connect(self.on_ai_check_clicked)
        recompile_layout.addWidget(self.ai_check_btn)

        left_layout.addLayout(bottom_layout)
        left_layout.addLayout(recompile_layout)
        
        # --- RIGHT PANE ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        preview_tools = QHBoxLayout()
        self.prev_page_btn = QPushButton("◀ Prev")
        self.prev_page_btn.clicked.connect(self.on_prev_page)
        self.next_page_btn = QPushButton("Next ▶")
        self.next_page_btn.clicked.connect(self.on_next_page)
        
        self.page_nav_label = QLabel("Page 0 of 0")
        
        self.zoom_in_btn = QPushButton("Zoom +")
        self.zoom_in_btn.clicked.connect(self.on_zoom_in)
        self.zoom_out_btn = QPushButton("Zoom -")
        self.zoom_out_btn.clicked.connect(self.on_zoom_out)
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.clicked.connect(self.on_zoom_fit)
        
        preview_tools.addWidget(self.prev_page_btn)
        preview_tools.addWidget(self.page_nav_label)
        preview_tools.addWidget(self.next_page_btn)
        preview_tools.addStretch(1)
        preview_tools.addWidget(self.zoom_out_btn)
        preview_tools.addWidget(self.zoom_fit_btn)
        preview_tools.addWidget(self.zoom_in_btn)
        
        right_layout.addLayout(preview_tools)
        
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("background-color: #525659;")
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_scroll.setWidget(self.preview_label)
        
        right_layout.addWidget(self.preview_scroll)
        
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

    def on_font_size_changed(self, size_str):
        size = int(size_str)
        for editor in self.editors.values():
            editor.set_font_size(size)

    def on_language_changed(self, lang_name):
        lang_code = "auto"
        if lang_name == "English": lang_code = "en-US"
        elif lang_name == "German": lang_code = "de-DE"
        
        for editor in self.editors.values():
            editor.set_language(lang_code)

    # --- EDITOR MANAGEMENT ---
    def load_all_files(self):
        for editor in self.editors.values():
            editor.load_from_disk()
            
    def save_all_files(self):
        for editor in self.editors.values():
            editor.save_to_disk()

    def get_current_editor_contents(self):
        contents = {}
        for key, editor in self.editors.items():
            contents[key] = editor.toPlainText()
        return contents

    def load_generated_sections(self, sections):
        self.generated_cache = sections.copy()
        for key, text in sections.items():
            if key in self.editors:
                self.editors[key].setPlainText(text)
                self.editors[key].save_to_disk()
                self.editors[key].run_grammar_check()

    def on_reset_to_generated(self):
        idx = self.tabs.currentIndex()
        if idx < 0: return
        key = self.sections[idx]["key"]
        
        if key in self.generated_cache:
            self.editors[key].setPlainText(self.generated_cache[key])
            self.editors[key].save_to_disk()
            self.editors[key].run_grammar_check()
            QMessageBox.information(self, "Reset Completed", "Successfully reset to original generated AI text!")
        else:
            QMessageBox.warning(self, "Not Found", "No original AI generation cached for this session yet.")

    def _selected_entry(self):
        label = self.pdf_selector.currentText()
        for entry in self.PDF_TARGETS:
            if entry[0] == label:
                return entry
        return self.PDF_TARGETS[0]

    def selected_target(self):
        """The compile-target key for the document selected in the dropdown."""
        return self._selected_entry()[1]

    def on_recompile_clicked(self):
        self.save_all_files()
        contents = self.get_current_editor_contents()
        self.recompile_requested.emit(contents)

    def on_ai_check_clicked(self):
        self.ai_check_requested.emit()

    # --- PDF MANAGEMENT ---
    def resolve_pdf_path(self):
        _, target, filename = self._selected_entry()
        if filename is not None:
            return os.path.join(self.output_dir, filename)
        # Full Application Bundle: prefer the exact file just compiled this
        # session; otherwise fall back to the newest bundle on disk.
        if self.last_bundle_path and os.path.exists(self.last_bundle_path):
            return self.last_bundle_path
        user_name = get_user_name(self.project_root)
        pdf_files = glob.glob(os.path.join(self.output_dir, "Compressed_*.pdf"))
        if not pdf_files:
            pdf_files = glob.glob(os.path.join(self.output_dir, f"{user_name}_*.pdf"))
        if pdf_files:
            return max(pdf_files, key=os.path.getmtime)
        return ""

    def load_selected_pdf(self):
        path = self.resolve_pdf_path()
        if not path or not os.path.exists(path):
            self.preview_label.setText("Compiled PDF not found. Generate or Recompile first.")
            self.preview_label.setPixmap(QPixmap())
            self.page_nav_label.setText("Page 0 of 0")
            if self.pdf_doc:
                self.pdf_doc.close()
                self.pdf_doc = None
            return

        try:
            if self.pdf_doc:
                self.pdf_doc.close()
            self.pdf_doc = fitz.open(path)
            self.current_page_index = min(self.current_page_index, len(self.pdf_doc) - 1)
            if self.current_page_index < 0:
                self.current_page_index = 0
            self.render_pdf_page()
        except Exception as e:
            self.preview_label.setText(f"Error loading PDF: {e}")
            self.preview_label.setPixmap(QPixmap())

    def render_pdf_page(self):
        if not self.pdf_doc: return
        try:
            page = self.pdf_doc.load_page(self.current_page_index)
            dpi = 150 * self.zoom_factor
            matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
            pix = page.get_pixmap(matrix=matrix)
            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            self.preview_label.setPixmap(QPixmap.fromImage(qimage))
            self.page_nav_label.setText(f"Page {self.current_page_index + 1} of {len(self.pdf_doc)}")
        except Exception:
            pass

    def on_prev_page(self):
        if self.pdf_doc and self.current_page_index > 0:
            self.current_page_index -= 1
            self.render_pdf_page()

    def on_next_page(self):
        if self.pdf_doc and self.current_page_index < len(self.pdf_doc) - 1:
            self.current_page_index += 1
            self.render_pdf_page()

    def on_zoom_in(self):
        if self.zoom_factor < 3.0:
            self.zoom_factor += 0.2
            self.render_pdf_page()

    def on_zoom_out(self):
        if self.zoom_factor > 0.4:
            self.zoom_factor -= 0.2
            self.render_pdf_page()

    def on_zoom_fit(self):
        self.zoom_factor = 1.0
        self.render_pdf_page()
