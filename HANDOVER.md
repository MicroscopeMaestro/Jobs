# 🚀 Project Handover / Progress Summary

## What is this project?
This is a **PySide6** desktop GUI application designed to automatically generate and compile highly-tailored LaTeX resumes and cover letters using the Gemini API. 

## What we accomplished in this session:
1. **Framework Migration**: Successfully migrated the entire GUI from `PyQt6` to `PySide6` to resolve a Homebrew dependency issue on macOS.
2. **Fixed Core Crash**: Resolved a critical `SIGABRT` crash caused by Python garbage-collecting `QThread` workers prematurely. Background tasks (like the live grammar checker) are now properly managed using a `self._old_workers` reference set.
3. **Advanced Skill Tagging System**: 
   - Introduced a two-tier color-coding system for Technical Competencies (`Expertise` vs `Knowledge`).
   - Hardcoded the legend directly into the base `resume.tex` so it renders flawlessly and is protected from UI overrides.
4. **Tone & Formatting Adjustments**: 
   - Enforced a strict "Junior Engineer" tone in the AI generator prompt.
   - Removed the bold styling from the degree/job titles in the LaTeX `\entry` macro.
5. **Grammar Checker UI Fix**: Fixed a macOS rendering issue where the background `LanguageTool` grammar checker wasn't displaying its wavy underlines. Errors are now clearly marked with red/blue `WaveUnderline`.

## How to run the application:
Ensure your virtual environment is active, then run:
```bash
venv_gui/bin/python app.py
```

## Current State:
The application is fully stable, tested, and works beautifully! All work has been committed and pushed to the `main` branch. 
