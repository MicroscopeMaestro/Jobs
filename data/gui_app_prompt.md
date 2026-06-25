# Build Prompt: Job Application GUI Generator

Paste this into a coding agent (Claude Code / Cursor) to build the app.

---

Build a desktop GUI application that generates tailored job applications (motivation letter + resume) as compiled PDFs. It wraps an existing LaTeX + Python pipeline and uses the Claude API for content generation. I provide parameters and final manual edits through the GUI.

## Context: existing project
The pipeline already exists at the project root directory:
- `templates/motivation_letter.tex` and `templates/resume.tex` are master LaTeX files that `\input` modular sections from `templates/sections/ml/` (sender, recipient, subject, body, closing) and `templates/sections/resume/` (header, summary, experience, technical_competencies, education, publications, soft_skills, languages, references).
- `src/main.py` compiles both via pdflatex, merges attachments with pypdf, and produces a final `generated/Application_<name>_<company>_<position>.pdf` plus a compressed version.
- `data/ai_application_prompt.md` holds my career story + a bank of professional examples (EX-1..EX-11) + skills.
- Cover letters are German (ngerman babel) for DACH roles; resume is English.
- Previously generated applications live as PDFs in `generated/`.

The GUI must REUSE this pipeline (write the section .tex files, then call main.py), not reinvent it.

## Tech stack
- Python. GUI framework: PySide6 (Qt) — native file pickers, multi-tab, text editors with live preview. (Fallback: if PySide6 too heavy, use a local web GUI with FastAPI + a single-page frontend, but prefer PySide6.)
- Anthropic Python SDK for generation. Model: claude-opus-4-7 (configurable). Use prompt caching for the static career context + examples bank.
- pdflatex (already installed) + pypdf for compile/merge.
- Store API key from env `ANTHROPIC_API_KEY`; never hardcode.

## GUI — input parameters
A form with these controls:
1. **Job description**: large text box (paste) OR URL field (fetch + strip to text). Required.
2. **Professional title**: editable dropdown — e.g. "Optical Systems Engineer", "System Engineer", "Junior System Engineer", "Implementation Engineer", "Verification Engineer", custom.
3. **Motivation letter focus**: dropdown/multi-select — Semiconductor, Machine Vision, System Engineering, Metrology, Photonics/Laser, Maintenance/Service, R&D, custom. Drives which angle + vocabulary the cover letter emphasizes.
4. **Professional examples**: checklist loaded from the examples bank (EX-1..EX-11 parsed from data/ai_application_prompt.md). I tick which to feature.
5. **Skills**: checklist + free-text add. Pre-populated from the skills section of the bank.
6. **Experience entries**: list of my roles (MUI, IPHT, INTECOL...) with per-role toggle and an editable job-title field per role (so I can relabel "Machine Vision Engineer" vs "Junior Machine Vision Engineer").
7. **Attachments**: file picker (multi-select) over `assets/` — checkboxes per PDF (diplomas, certificates, permit; passport optional). Maps to the ATTACHMENTS dict in main.py.
8. **Language**: cover letter DE / EN / auto-detect from job.
9. **Salary line**: optional text or "omit".
10. **Recipient block**: company, contact person, address (auto-extract from job text via Claude, editable).
11. **Page limits**: target resume pages (default 2), enforce by warning if exceeded.

## "Learn from my past applications"
- On startup, scan `generated/*.pdf` (and optionally a curated `corpus/` folder), extract text with pypdf.
- Build a local style profile: my phrasing, sentence rhythm, recurring framings, German register, how I open/close letters, how bullets are structured.
- Pass this profile as additional context to Claude so new letters match my voice (the project also has a /humanize style: varied sentence length, no corporate buzzwords, contractions, active voice, facts unchanged).
- Cache the extracted corpus; re-scan on demand via a "Re-learn" button. Show how many PDFs were ingested.

## Generation flow
1. I fill the form, click **Generate**.
2. App assembles a Claude prompt: career context + examples bank + selected examples/skills/experience + style profile from past PDFs + job description + chosen title/focus/language.
3. Claude returns structured content for each section (subject, recipient, body, summary, experience bullets, technical competencies) using the SAME tagged format the existing `src/generate_application.py` expects (`<ML_SUBJECT>`, `<ML_RECIPIENT>`, `<ML_BODY>`, `<RESUME_EXPERIENCE>`, `<RESUME_COMPETENCIES>`, etc.). Respect existing LaTeX strictures (escape &, %, _; no em-dashes; hard-wrap ~80 chars; adjustwidth at 103pt).
4. App writes the section .tex files, runs `src/main.py`, shows the compiled PDFs.

## Manual correction (required)
- After generation, show an **editor pane** per document: left = editable text/LaTeX of each section, right = live PDF preview.
- I can edit any section by hand, click **Recompile** to rebuild via main.py and refresh preview.
- Track edits so "Re-learn" can later fold my corrections back into the style profile.
- Undo/redo per section. A "Reset to generated" button.

## Output
- Final compiled, merged, compressed PDF in `generated/`, named like the existing convention.
- A "Save preset" feature: store a full parameter set (title + focus + examples + skills + attachments) under a name so I can reapply for similar roles.

## Deliverables
- Runnable app: `python app.py`.
- `requirements.txt`.
- README: setup, API key, how to run, how the learning corpus works.
- Do NOT change the existing `templates/` or `main.py` compile logic except where the GUI must write section files; if you need a hook, add a thin adapter module rather than rewriting main.py.
- Keep generation tunable: expose temperature + model in a settings panel.

Start by reading `src/main.py`, `src/generate_application.py`, `data/ai_application_prompt.md`, and the `templates/sections/` tree to match formats exactly. Then propose the module layout before coding.
