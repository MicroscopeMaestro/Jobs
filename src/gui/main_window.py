import os
import sys
from PySide6.QtWidgets import (QMainWindow, QTabWidget, QMenu,
                             QMessageBox, QProgressDialog, QInputDialog,
                             QStatusBar, QDialog,
                             QVBoxLayout, QLabel, QTextEdit, QPushButton)
from PySide6.QtCore import Qt, QThread, Signal as Signal

from .form_tab import FormTab
from .editor_tab import EditorTab
from .settings_dialog import SettingsDialog
from .preset_manager import PresetManager
from .style_learner import StyleLearner
from .generator import Generator
from .ai_chat_tab import AIChatTab
from .tracker_tab import TrackerTab

# --- Asynchronous Worker for Claude Application Generation ---
class GenerateWorker(QThread):
    # NOTE: never name a custom signal "finished" — it shadows QThread.finished
    # (which fires only after run() returns). The registry in MainWindow relies
    # on the real QThread.finished to release workers safely.
    done = Signal(dict)
    error = Signal(str)

    def __init__(self, generator, api_key, params, style_profile, career_context, papers_dict, tuning_params):
        super().__init__()
        self.generator = generator
        self.api_key = api_key
        self.params = params
        self.style_profile = style_profile
        self.career_context = career_context
        self.papers_dict = papers_dict
        self.tuning_params = tuning_params

    def run(self):
        try:
            sections = self.generator.generate_application(
                api_key=self.api_key,
                params=self.params,
                style_profile=self.style_profile,
                career_context=self.career_context,
                papers_dict=self.papers_dict,
                model=self.tuning_params["model"],
                temperature=self.tuning_params["temperature"]
            )
            self.done.emit(sections)
        except Exception as e:
            self.error.emit(str(e))

# --- Asynchronous Worker for AI Chat Section Editing ---
class AIChatWorker(QThread):
    # Emits (success: bool, section_key: str, content_or_error: str)
    done = Signal(bool, str, str)

    def __init__(self, generator, api_key, section_key, current_text, user_prompt, tuning_params):
        super().__init__()
        self.generator = generator
        self.api_key = api_key
        self.section_key = section_key
        self.current_text = current_text
        self.user_prompt = user_prompt
        self.tuning_params = tuning_params

    def run(self):
        try:
            updated_text = self.generator.edit_section(
                api_key=self.api_key,
                current_text=self.current_text,
                user_prompt=self.user_prompt,
                model=self.tuning_params["model"],
                temperature=self.tuning_params["temperature"]
            )
            self.done.emit(True, self.section_key, updated_text)
        except Exception as e:
            self.done.emit(False, self.section_key, str(e))

# --- Asynchronous Worker for Auto-Extracting Job Details ---
class ExtractionWorker(QThread):
    # Emits (success: bool, parsed_json: dict, error_msg: str)
    done = Signal(bool, dict, str)

    def __init__(self, generator, api_key, job_description, tuning_params, context_dict):
        super().__init__()
        self.generator = generator
        self.api_key = api_key
        self.job_description = job_description
        self.tuning_params = tuning_params
        self.context_dict = context_dict

    def run(self):
        try:
            parsed_json = self.generator.extract_job_details(
                api_key=self.api_key,
                job_description=self.job_description,
                context_dict=self.context_dict,
                model=self.tuning_params["model"],
                temperature=0.1 # Enforce low temp for extraction
            )
            self.done.emit(True, parsed_json, "")
        except Exception as e:
            self.done.emit(False, {}, str(e))

# --- Asynchronous Worker for AI Sanity Check ---
class SanityCheckWorker(QThread):
    done = Signal(bool, str)

    def __init__(self, generator, api_key, document_text, tuning_params):
        super().__init__()
        self.generator = generator
        self.api_key = api_key
        self.document_text = document_text
        self.tuning_params = tuning_params

    def run(self):
        try:
            result = self.generator.run_sanity_check(
                api_key=self.api_key,
                document_text=self.document_text,
                model=self.tuning_params["model"]
            )
            self.done.emit(True, result)
        except Exception as e:
            self.done.emit(False, str(e))

# --- Asynchronous Worker for LaTeX Compilation (wraps src/main.py) ---
class CompileWorker(QThread):
    done = Signal(str)
    error = Signal(str)

    def __init__(self, project_root, attachments_map, target="full_bundle"):
        super().__init__()
        self.project_root = project_root
        self.attachments_map = attachments_map
        self.target = target

    def run(self):
        try:
            # Add project root to sys.path to allow imports
            if self.project_root not in sys.path:
                sys.path.append(self.project_root)

            # Import main pipeline dynamically
            from src import main as main_pipeline

            # Setup latex path in environment
            main_pipeline.setup_latex_path()

            # Build only the requested target (full_bundle == whole pipeline)
            final_path = main_pipeline.compile_target(self.target, self.attachments_map)

            self.done.emit(final_path if final_path else "")
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self, project_root):
        super().__init__()
        self.project_root = project_root
        self.setWindowTitle("Job Application LaTeX GUI Generator")
        self.resize(1100, 750)

        # Strong references to every background worker, held until its OS thread
        # has actually finished. Reassigning self.gen_worker/compile_worker/etc.
        # while the previous one is still running would otherwise drop its last
        # reference and let Python GC destroy a live QThread (Qt then aborts the
        # whole process with "QThread: Destroyed while thread is still running").
        self._workers = set()

        # Instantiate logical components
        self.generator = Generator(project_root)
        self.preset_manager = PresetManager(project_root)
        self.style_learner = StyleLearner(project_root)
        
        # Setup UI
        self.init_ui()
        self.setup_menu()
        self.update_style_status()

    def _track(self, worker):
        """Hold a strong ref to a worker until its thread truly finishes.

        Uses the real QThread.finished (fires after run() returns), so the
        reference is only released once the OS thread has stopped — never while
        run() is still executing.
        """
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.finished.connect(worker.deleteLater)
        return worker

    def init_ui(self):
        # Tabs container
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Tab 1: Configuration Form
        self.form_tab = FormTab(self.project_root, self.generator)
        self.form_tab.generation_requested.connect(self.on_generation_requested)
        self.form_tab.extract_btn.clicked.connect(self.on_extraction_requested)
        self.tabs.addTab(self.form_tab, "1. Configure Parameters")
        
        # Tab 2: Manual Revisions & Preview
        self.editor_tab = EditorTab(self.project_root)
        self.editor_tab.recompile_requested.connect(self.on_recompile_requested)
        self.editor_tab.ai_check_requested.connect(self.on_ai_check_requested)
        self.tabs.addTab(self.editor_tab, "2. Revise LaTeX & Preview")
        
        # Tab 3: AI Chat Assistant
        self.ai_chat_tab = AIChatTab(self.project_root, self.editor_tab)
        self.ai_chat_tab.chat_requested.connect(self.on_chat_requested)
        self.tabs.addTab(self.ai_chat_tab, "3. AI Chat Assistant")
        
        # Tab 4: Application Tracker
        self.tracker_tab = TrackerTab(self.project_root)
        self.tabs.addTab(self.tracker_tab, "4. Application Tracker")
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def setup_menu(self):
        menu_bar = self.menuBar()
        
        # 1. Preset Menu
        self.presets_menu = QMenu("Presets", self)
        menu_bar.addMenu(self.presets_menu)
        self.rebuild_presets_menu()
        
        # 2. Tools Menu
        tools_menu = QMenu("Tools", self)
        
        relearn_act = tools_menu.addAction("Re-learn Voice Profile")
        relearn_act.triggered.connect(self.on_relearn_triggered)
        
        settings_act = tools_menu.addAction("API & Tuning Settings")
        settings_act.triggered.connect(self.on_settings_triggered)
        
        menu_bar.addMenu(tools_menu)

    def rebuild_presets_menu(self):
        self.presets_menu.clear()
        
        save_act = self.presets_menu.addAction("Save Current Config as Preset...")
        save_act.triggered.connect(self.on_save_preset)
        self.presets_menu.addSeparator()
        
        # Load Presets submenu
        load_menu = self.presets_menu.addMenu("Load Preset")
        preset_names = self.preset_manager.list_presets()
        
        if not preset_names:
            no_presets_act = load_menu.addAction("No saved presets")
            no_presets_act.setEnabled(False)
        else:
            for name in preset_names:
                act = load_menu.addAction(name)
                # Use a closure or lambda with default arg to bind name
                act.triggered.connect(lambda checked=False, n=name: self.on_load_preset(n))
                
        # Delete Presets submenu
        delete_menu = self.presets_menu.addMenu("Delete Preset")
        if not preset_names:
            no_del_act = delete_menu.addAction("No saved presets")
            no_del_act.setEnabled(False)
        else:
            for name in preset_names:
                act = delete_menu.addAction(name)
                act.triggered.connect(lambda checked=False, n=name: self.on_delete_preset(n))

    def update_style_status(self):
        # Scan and update style profile details in status bar
        ingested = self.style_learner.scan_past_applications()
        self.status_bar.showMessage(f"Voice profile learned from {ingested} past application PDFs.")

    # --- ACTION HANDLERS ---
    
    def on_relearn_triggered(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            QMessageBox.warning(self, "API Key Missing", "Re-learning voice requires an Anthropic API Key. Please set it in Settings.")
            return
            
        tuning = SettingsDialog.get_tuning_params(self.project_root)
        
        # Setup loading dialog
        progress = QProgressDialog("Scanning generated/ PDFs & synthesizing your voice profile...", "", 0, 0, self)
        progress.setWindowTitle("Learning Style Voice")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Run relearn safely inside main GUI flow (its fast enough for standard corpuses, or uses Claude)
        try:
            count = self.style_learner.relearn_style(
                api_key=api_key,
                model=tuning["model"],
                temperature=tuning["temperature"]
            )
            progress.close()
            self.update_style_status()
            QMessageBox.information(self, "Success", f"Voice profile successfully updated!\n\nIngested {count} Cover Letters from generated/.")
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to relearn style voice:\n{e}")

    def on_settings_triggered(self):
        dlg = SettingsDialog(self, self.project_root)
        dlg.exec()
        self.update_style_status()

    def on_save_preset(self):
        # 1. Prompt for Preset Name
        name, ok = QInputDialog.getText(self, "Save Preset", "Enter a name for this configuration preset:")
        if not ok or not name.strip():
            return
            
        name = name.strip()
        
        # 2. Gather values from form
        # We need to expose a helper in FormTab to gather values, or retrieve from FormTab
        # Since FormTab has checkboxes, title dropdown, custom skill inputs, etc.
        # We can construct the dictionary
        
        # Let's extract values
        selected_focus = [cb.text() for cb in self.form_tab.focus_checkboxes if cb.isChecked()]
        
        selected_examples = []
        for cb in self.form_tab.example_checkboxes:
            if cb.isChecked():
                selected_examples.append(cb.property("ex_id"))
                
        selected_skills = []
        for cb, cat, combo in self.form_tab.skills_list:
            if cb.isChecked():
                selected_skills.append((cb.text(), cat))
                
        exp_entries = []
        for cb, title_input, entry in self.form_tab.exp_widgets:
            exp_entries.append({
                "id": entry["id"],
                "enabled": cb.isChecked(),
                "title": title_input.text().strip()
            })
            
        attachments = []
        for cb in self.form_tab.attachment_checkboxes:
            if cb.isChecked():
                attachments.append(cb.property("filename"))
                
        lang = "de"
        if self.form_tab.lang_en.isChecked():
            lang = "en"
        elif self.form_tab.lang_auto.isChecked():
            lang = "auto"
            
        preset_data = {
            "job_url": self.form_tab.url_input.text().strip(),
            "job_desc": self.form_tab.job_desc_input.toPlainText().strip(),
            "title": self.form_tab.title_combo.currentText().strip(),
            "focus": selected_focus,
            "examples": selected_examples,
            "skills": selected_skills,
            "experience": exp_entries,
            "attachments": attachments,
            "language": lang,
            "salary": self.form_tab.salary_input.text().strip(),
            "recipient_company": self.form_tab.rec_company_input.text().strip(),
            "recipient_contact": self.form_tab.rec_contact_input.text().strip(),
            "recipient_address": self.form_tab.rec_address_input.text().strip(),
            "page_limit": self.form_tab.page_limit_spin.value(),
            "humanize": self.form_tab.humanize_cb.isChecked()
        }
        
        self.preset_manager.save_preset(name, preset_data)
        self.rebuild_presets_menu()
        QMessageBox.information(self, "Preset Saved", f"Preset '{name}' saved successfully!")

    def on_load_preset(self, name):
        preset = self.preset_manager.get_preset(name)
        if not preset:
            return
            
        # Apply to FormTab
        # 1. Title
        title = preset.get("title", "")
        idx = self.form_tab.title_combo.findText(title)
        if idx >= 0:
            self.form_tab.title_combo.setCurrentIndex(idx)
        else:
            self.form_tab.title_combo.setEditText(title)
            
        # 2. Focus
        focus_list = preset.get("focus", [])
        for cb in self.form_tab.focus_checkboxes:
            cb.setChecked(cb.text() in focus_list)
            
        # 3. Examples
        examples_list = preset.get("examples", [])
        for cb in self.form_tab.example_checkboxes:
            cb.setChecked(cb.property("ex_id") in examples_list)
                
        # 4. Skills (including custom adding)
        skills_list = preset.get("skills", [])
        # Extract plain texts
        plain_skills = [sk[0] if isinstance(sk, list) else sk for sk in skills_list]
        
        # Reset standard skills checkbox state
        for cb, cat, combo in self.form_tab.skills_list:
            cb.setChecked(cb.text() in plain_skills)
                
        # 5. Experience
        exp_list = preset.get("experience", [])
        exp_dict = {item["id"]: item for item in exp_list if "id" in item}
        for cb, title_input, entry in self.form_tab.exp_widgets:
            if entry["id"] in exp_dict:
                cb.setChecked(exp_dict[entry["id"]].get("enabled", True))
                title_input.setText(exp_dict[entry["id"]].get("title", entry["default_title"]))
                
        # 6. Attachments
        attachments_list = preset.get("attachments", [])
        for cb in self.form_tab.attachment_checkboxes:
            cb.setChecked(cb.property("filename") in attachments_list)
            
        # 7. Language
        lang = preset.get("language", "de")
        if lang == "en":
            self.form_tab.lang_en.setChecked(True)
        elif lang == "auto":
            self.form_tab.lang_auto.setChecked(True)
        else:
            self.form_tab.lang_de.setChecked(True)
            
        # 8. Salary & Limits
        self.form_tab.salary_input.setText(preset.get("salary", "omit"))
        self.form_tab.page_limit_spin.setValue(preset.get("page_limit", 2))
        self.form_tab.humanize_cb.setChecked(preset.get("humanize", True))
        
        # 9. Recipient Block
        self.form_tab.rec_company_input.setText(preset.get("recipient_company", ""))
        self.form_tab.rec_contact_input.setText(preset.get("recipient_contact", "Recruiting Team"))
        self.form_tab.rec_address_input.setText(preset.get("recipient_address", ""))
        
        self.status_bar.showMessage(f"Preset '{name}' loaded successfully.", 3000)

    def on_delete_preset(self, name):
        reply = QMessageBox.question(
            self, "Confirm Delete", f"Are you sure you want to delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.preset_manager.delete_preset(name)
            self.rebuild_presets_menu()
            self.status_bar.showMessage(f"Preset '{name}' deleted.", 3000)

    # --- GENERATION FLOW ---
    
    def on_generation_requested(self, params):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            QMessageBox.critical(self, "API Key Missing", 
                                 "No Anthropic API Key found.\n"
                                 "Please enter your key in Tools -> API & Tuning Settings.")
            return

        # Load dynamic configurations
        tuning = SettingsDialog.get_tuning_params(self.project_root)
        style_profile = self.style_learner.get_style_profile()
        
        # Load career prompt
        career_context = ""
        if os.path.exists(self.form_tab.prompt_path):
            with open(self.form_tab.prompt_path, "r", encoding="utf-8") as f:
                career_context = f.read()

        # Load research papers
        papers_dict = {}
        papers_dir = os.path.join(self.project_root, "assets", "papers")
        if os.path.exists(papers_dir):
            import pypdf
            for fname in os.listdir(papers_dir):
                if fname.lower().endswith(".pdf"):
                    path = os.path.join(papers_dir, fname)
                    try:
                        reader = pypdf.PdfReader(path)
                        text = "".join([p.extract_text() or "" for p in reader.pages[:2]])
                        papers_dict[fname] = text[:2000] # limit length to optimize context
                    except:
                        pass

        # Progress indicator
        self.progress_dlg = QProgressDialog("🤖 Generating tailored LaTeX sections via Claude (Opus 4.8)...", "", 0, 0, self)
        self.progress_dlg.setWindowTitle("AI Generation running")
        self.progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dlg.show()

        # Start background worker
        self.gen_worker = self._track(GenerateWorker(self.generator, api_key, params, style_profile, career_context, papers_dict, tuning))
        self.gen_worker.done.connect(lambda s: self.on_generation_finished(s, params))
        self.gen_worker.error.connect(self.on_generation_error)
        self.gen_worker.start()

    def on_generation_finished(self, sections, params):
        self.progress_dlg.close()
        
        # Write files
        self.generator.write_sections(sections)
        
        # Load editors inside EditorTab
        self.editor_tab.load_generated_sections(sections)
        
        # Auto-trigger first compile
        self.compile_latex_bundle(params["attachments"])

    def on_generation_error(self, err_msg):
        self.progress_dlg.close()
        QMessageBox.critical(self, "Generation Error", f"Claude API Call Failed:\n{err_msg}")

    # --- AI CHAT FLOW ---
    def on_chat_requested(self, data):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self.ai_chat_tab.on_chat_finished(False, data['section_key'], "API Key Missing. Enter in Tools -> API Settings.")
            return

        tuning = SettingsDialog.get_tuning_params(self.project_root)
        
        self.chat_worker = self._track(AIChatWorker(
            generator=self.generator,
            api_key=api_key,
            section_key=data['section_key'],
            current_text=data['current_text'],
            user_prompt=data['user_prompt'],
            tuning_params=tuning
        ))
        self.chat_worker.done.connect(self.on_chat_finished)
        self.chat_worker.start()

    def on_chat_finished(self, success, section_key, result):
        # Update UI in Chat Tab
        self.ai_chat_tab.on_chat_finished(success, section_key, result if not success else "")
        
        if success:
            # Update Editor Tab and trigger compile
            self.editor_tab.load_generated_sections({section_key: result})
            
            # Use current attachments from form to compile
            attachments_map = {
                "professional_experience": [],
                "education": [],
                "certificates": [],
                "others": []
            }
            for cb in self.form_tab.attachment_checkboxes:
                if cb.isChecked():
                    cat = cb.property("category")
                    filename = cb.property("filename")
                    attachments_map[cat].append(filename)
                    
            self.compile_latex_bundle(attachments_map)

    # --- AI EXTRACTION FLOW ---
    def on_extraction_requested(self):
        job_description = self.form_tab.job_desc_input.toPlainText().strip()
        if not job_description:
            QMessageBox.warning(self, "No Job Description", "Please paste a job description first to extract details from.")
            return

        self.form_tab.extract_btn.setEnabled(False)
        self.form_tab.extract_btn.setText("Extracting & Tuning...")

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            QMessageBox.warning(self, "API Key Missing", "Enter your API Key in Tools -> API Settings.")
            self.form_tab.extract_btn.setEnabled(True)
            self.form_tab.extract_btn.setText("✨ Auto-Extract Details")
            return
            
        # Gather context for Auto-Tuning
        context_dict = {
            "foci": [cb.text() for cb in self.form_tab.focus_checkboxes],
            "examples": [cb.property("ex_id") for cb in self.form_tab.example_checkboxes],
            "skills": [cb.text() for cb, _, _ in self.form_tab.skills_list],
            "experience_entries": [cb.text() for cb, _, _ in self.form_tab.exp_widgets]
        }
            
        tuning = SettingsDialog.get_tuning_params(self.project_root)
        self.extraction_worker = self._track(ExtractionWorker(self.generator, api_key, job_description, tuning, context_dict))
        self.extraction_worker.done.connect(self.on_extraction_finished)
        self.extraction_worker.start()
        
    def on_extraction_finished(self, success, parsed_json, error_msg):
        self.form_tab.extract_btn.setEnabled(True)
        self.form_tab.extract_btn.setText("✨ Auto-Extract Details")
        
        if success:
            company = parsed_json.get("company", "")
            if company and company != "Unknown":
                self.form_tab.rec_company_input.setText(company)
                
            position = parsed_json.get("position", "")
            if position and position != "Unknown Position":
                self.form_tab.title_combo.setCurrentText(position)
                
            # Toggle Focus Checkboxes
            foci = parsed_json.get("foci", [])
            for cb in self.form_tab.focus_checkboxes:
                cb.setChecked(cb.text() in foci)
                
            # Toggle Example Checkboxes
            examples = parsed_json.get("examples", [])
            for cb in self.form_tab.example_checkboxes:
                cb.setChecked(cb.property("ex_id") in examples)
                
            # Toggle Skills Checkboxes
            skills = parsed_json.get("skills", [])
            for cb, _, _ in self.form_tab.skills_list:
                cb.setChecked(cb.text() in skills)
                
            # Toggle Experience Widgets
            exp_entries = parsed_json.get("experience_entries", [])
            for cb, _, _ in self.form_tab.exp_widgets:
                cb.setChecked(cb.text() in exp_entries)

            self.status_bar.showMessage("Job details and checkboxes auto-tuned successfully!", 5000)
        else:
            QMessageBox.warning(self, "Extraction Failed", f"Could not auto-tune details:\n{error_msg}")

    # --- LATEX COMPILING FLOW ---
    
    def on_recompile_requested(self, editor_contents):
        # 1. Write the edited texts back to sections folder
        self.generator.write_sections(editor_contents)
        
        # 2. Gather current attachment config from FormTab
        attachments_map = {
            "professional_experience": [],
            "education": [],
            "certificates": [],
            "others": []
        }
        for cb in self.form_tab.attachment_checkboxes:
            if cb.isChecked():
                cat = cb.property("category")
                filename = cb.property("filename")
                attachments_map[cat].append(filename)

        # 3. Compile only the document selected in the editor's dropdown
        self.compile_latex_bundle(attachments_map, self.editor_tab.selected_target())

    def compile_latex_bundle(self, attachments_map, target="full_bundle"):
        self.compile_dlg = QProgressDialog("Compiling PDFs via pdflatex & merging attachments...", "", 0, 0, self)
        self.compile_dlg.setWindowTitle("Document Compilation running")
        self.compile_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self.compile_dlg.show()

        self.compile_worker = self._track(CompileWorker(self.project_root, attachments_map, target))
        self.compile_worker.done.connect(self.on_compile_finished)
        self.compile_worker.error.connect(self.on_compile_error)
        self.compile_worker.start()

    def on_compile_finished(self, final_path):
        self.compile_dlg.close()
        
        # Reload current PDF inside editor tab
        self.editor_tab.load_selected_pdf()
        
        # Switch tab to editor tab (Index 1) so user can see it
        self.tabs.setCurrentIndex(1)
        
        msg = "Compilation successful!"
        if final_path:
            msg += f" Saved at: {os.path.basename(final_path)}"
            try:
                # Auto-log to Tracker
                if self.project_root not in sys.path:
                    sys.path.append(self.project_root)
                from src.main import extract_info_from_latex
                company, position = extract_info_from_latex("motivation_letter.tex")
                self.tracker_tab.auto_log_application(company, position)
            except Exception as e:
                print(f"Failed to auto-log application: {e}")
        
        self.status_bar.showMessage(msg, 10000)
        # AI proofreading no longer runs automatically — use the "🤖 AI Check"
        # button in the editor tab to run it on demand.

    def on_ai_check_requested(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            QMessageBox.warning(self, "API Key Missing",
                                "An Anthropic API Key is required for the AI check. Set it in Tools -> Settings.")
            return

        doc_text = ""
        for key, editor in self.editor_tab.editors.items():
            doc_text += f"\n--- {key} ---\n{editor.toPlainText()}\n"
        if not doc_text.strip():
            QMessageBox.information(self, "Nothing to Check", "Generate or write some content first.")
            return

        self.editor_tab.ai_check_btn.setEnabled(False)
        self.editor_tab.ai_check_btn.setText("🤖 Checking...")
        tuning = SettingsDialog.get_tuning_params(self.project_root)
        self.sanity_worker = self._track(SanityCheckWorker(self.generator, api_key, doc_text, tuning))
        self.sanity_worker.done.connect(self.on_sanity_check_finished)
        self.sanity_worker.start()
        self.status_bar.showMessage("Running AI check on the current document...", 10000)

    def on_sanity_check_finished(self, success, result):
        self.editor_tab.ai_check_btn.setEnabled(True)
        self.editor_tab.ai_check_btn.setText("🤖 AI Check")
        if success:
            if "all good" not in result.lower():
                # Create a non-modal dialog so the user can read it while editing
                self.sanity_dlg = QDialog(self)
                self.sanity_dlg.setWindowTitle("🤖 AI Sanity Check Alert")
                self.sanity_dlg.setModal(False) # NON-MODAL!
                self.sanity_dlg.resize(500, 350)
                
                layout = QVBoxLayout(self.sanity_dlg)
                
                warn_label = QLabel("<b>The AI spotted potential issues in your generated document:</b>")
                warn_label.setStyleSheet("color: #ef4444; font-size: 14px;")
                layout.addWidget(warn_label)
                
                text_edit = QTextEdit()
                text_edit.setPlainText(result)
                text_edit.setReadOnly(True)
                text_edit.setStyleSheet("font-family: 'Courier New', Courier, monospace; font-size: 13px; background-color: #1e293b; color: #f8fafc;")
                layout.addWidget(text_edit)
                
                ok_btn = QPushButton("Got it")
                ok_btn.clicked.connect(self.sanity_dlg.close)
                ok_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px; border-radius: 4px;")
                layout.addWidget(ok_btn)
                
                self.sanity_dlg.show()
            else:
                self.status_bar.showMessage("AI Sanity Check Passed: All Good! 🎉", 5000)
        else:
            print(f"Sanity check failed to run: {result}")

    def on_compile_error(self, err_msg):
        self.compile_dlg.close()
        if "LaTeX failed to compile" in err_msg:
            # Content error from a manual edit — show the actual LaTeX error.
            QMessageBox.critical(self, "LaTeX Error",
                                 "Your LaTeX has an error, so the PDF was not updated. "
                                 "Fix the highlighted issue and recompile:\n\n"
                                 f"{err_msg}")
        else:
            QMessageBox.critical(self, "Compilation Error",
                                 f"Latex/Python pipeline failed to run successfully:\n{err_msg}\n\n"
                                 "Please check LaTeX installation and make sure 'pdflatex' is callable.")

    # --- LIFECYCLE ---
    def closeEvent(self, event):
        # Stop every background QThread before teardown, otherwise Qt aborts the
        # process with "QThread: Destroyed while thread is still running". Grammar
        # workers can sit in a blocking network request, so a short wait isn't
        # enough — wait generously, then terminate as a last resort (safe here:
        # the process is exiting anyway).
        workers = list(self._workers)
        for editor in getattr(self.editor_tab, "editors", {}).values():
            current = getattr(editor, "worker", None)
            if current is not None:
                workers.append(current)
            workers.extend(getattr(editor, "_old_workers", set()))

        workers = [w for w in workers if w is not None]
        for w in workers:
            if w.isRunning():
                w.requestInterruption()
        for w in workers:
            if w.isRunning() and not w.wait(6000):
                w.terminate()
                w.wait(1000)

        super().closeEvent(event)
