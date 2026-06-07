# Job Application LaTeX GUI Generator (Gemini Version)

A modern, desktop-based GUI application built in **PySide6 (Qt)** designed to streamline the creation of highly tailored job applications (motivation letters and resumes). It wraps your existing modular LaTeX + Python compiling pipeline and harnesses the **Google Gemini API** (supporting fast, high-quality models) to write compelling content that matches your own writing voice.

---

## Technical Features

1. **AI Generation with Google Gemini**: Utilizes the official `google-generativeai` SDK to connect to Google's advanced model suites (e.g. `gemini-2.5-flash`, `gemini-2.5-pro`).
2. **Deep Voice Profiling ("Re-learn")**: Automatically reads cover letters and resume bullets from your previously generated applications (`generated/Application_*.pdf`) using PyMuPDF to extract text. It feeds these examples to Gemini to build a personalized style profile stored in `data/style_profile.txt` so new content matches your phrasing, rhythm, and DACH register perfectly.
3. **Responsive Async Workers**: Generation and document compilation are executed in background `QThread` processes, keeping the UI silky-smooth and fully responsive.
4. **Rich Multi-Tab LaTeX Editors**: Allows full manual tweaks for each section (`ML Subject`, `ML Recipient`, `ML Body`, `Resume Experience`, `Resume Competencies`) with built-in Undo/Redo and a "Reset to Generated" capability.
5. **Integrated PDF Preview**: Displays your compiled output instantly side-by-side using high-fidelity rendering from `PyMuPDF`. Supports multi-document switching (Letter, Resume, Full Bundle), interactive zooming, page navigation, and enforces target page limits with clear warnings.
6. **Flexible Settings Panel**: Exposes adjustable sliders for generation temperature, spinboxes for token limits, editable dropdowns for Gemini model selection, and secure API credential storage to a local `.env` file.
7. **Preset Manager**: Stores form parameters under custom names to let you instantly apply similar profiles for Metrology, Semiconductor, R&D, or Machine Vision roles.
8. **Asynchronous Recipient Extractor**: Input a job URL or description, click "Fetch & Parse Info", and watch the company, hiring manager, address, and target title get instantly filled in!

---

## Installation & Setup

To bypass macOS Homebrew python restrictions and ensure system stability, follow these steps to run the application in a local virtual environment:

### 1. Create a Virtual Environment
Run the following commands in the repository root directory:
```bash
# Create the virtual environment
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate
```

### 2. Install Dependencies
Install all package requirements directly inside the active virtual environment:
```bash
pip install -r requirements.txt
```

### 3. Set up your Gemini API Key
Create a `.env` file in the root directory (or let the app read your existing one) and add your key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
The application will read this on startup. It never hardcodes your credentials.

---

## How to Run

Ensure the virtual environment is active (or call its python binary directly) and execute:

```bash
# Run with active venv
python app.py

# Or run directly via path
.venv/bin/python app.py
```

---

## How the Learning Corpus Works

The "Learn from my past applications" engine establishes a powerful feedback loop to automate a personalized writing style:

1. **Startup Scan**: On launch, the app scans your `generated/` directory for any completed application bundles matching `Application_*.pdf`.
2. **Text Extraction**: Using `pypdf`, it isolates the Cover Letter (Page 1) and Resume (Pages 2-3) texts from each PDF and caches them inside `data/style_cache.json` with timestamp tracking.
3. **Style Profile Generation ("Re-learn")**:
   When you click the **"Re-learn Voice Profile"** button in the **Tools** menu, the app selects the Cover Letter texts and asks Gemini to conduct a professional analysis of your phrasing rhythm, DACH-region register, greeting hooks, closing structures, and technical framings.
4. **Integration**: The result is saved as a persistent style document at `data/style_profile.txt`. When creating new letters, this profile is fed into the Gemini generation system prompt to force it to replicate your exact tone.
5. **Feedback Loop (Manual Corrections)**:
   If you manually edit the generated LaTeX text in the revision pane and click "Recompile", `src/main.py` builds the new PDF directly into your `generated/` folder. The next time you click "Re-learn", this updated PDF is automatically ingested, folding your manual corrections back into your persistent style profile!

---

## File Structure

- `app.py`: Application loader and UI QSS stylesheet.
- `requirements.txt`: Project dependency listing.
- `src/gui/`: Core GUI implementation package:
  - `main_window.py`: Window controller, menus, status indicators, and threads.
  - `form_tab.py`: Dynamic parameter form, asset lists, custom skills, and async URL fetcher.
  - `editor_tab.py`: Split screen LaTeX editors and high-fidelity fitz-based PDF viewer.
  - `settings_dialog.py`: Model tuner, token limits, and secure API key writer.
  - `generator.py`: System prompts, XML response parser, and Gemini caller.
  - `preset_manager.py`: JSON loader/saver for saved forms.
  - `style_learner.py`: PDF text extractor and voice analysis engine.
