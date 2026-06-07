# 🚀 Project Handover / Progress Summary

## What is this project?
This is a **PySide6** desktop GUI application designed to automatically generate and compile highly-tailored LaTeX resumes and cover letters using the Gemini API. 

## What we accomplished in this session:
1. **Framework Migration**: Successfully migrated the entire GUI from `PyQt6` to `PySide6` to resolve a Homebrew dependency issue on macOS.
2. **Fixed Core Crash**: Resolved a critical `SIGABRT` crash caused by Python garbage-collecting `QThread` workers prematurely. Background tasks (like the live grammar checker) are now properly managed using a `self._old_workers` reference set.
3. **Advanced Skill Tagging System**: 
   - Introduced a two-tier color-coding system for Technical Competencies (`Expertise` vs `Knowledge`).
   - Updated the GUI to allow you to easily choose your level for each skill via a dropdown.
   - Updated the LaTeX templates (`\cvtagExpertise` and `\cvtagKnowledge`) and added a legend (*"Dark tags indicate expertise; light tags indicate knowledge"*) to explain the color coding on the generated PDF.
4. **Content Organization**: Cleaned up the `ai_application_prompt.md` skills section by merging "Standards & Quality" into Soft Skills, and splitting the "Machine Vision" tools across Software and Hardware categories.

## How to run the application:
Ensure your virtual environment is active, then run:
```bash
venv_gui/bin/python app.py
```

## Current State:
The application is fully stable, tested, and works beautifully! All work has been committed and pushed to the `main` branch. 
