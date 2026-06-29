"""Streamlit web version of the Job Application Generator."""

import os
import sys
import re
import json
import glob
import shutil
import base64
import subprocess
from datetime import datetime
from io import BytesIO

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Windows LaTeX path setup
def _setup_latex_path():
    for p in [
        r"C:\Program Files\MiKTeX\miktex\bin\x64",
        r"C:\Program Files\MiKTeX 2.9\miktex\bin\x64",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"),
        r"C:\texlive\2025\bin\windows",
        r"C:\texlive\2024\bin\windows",
    ]:
        if os.path.exists(p) and p not in os.environ.get("PATH", ""):
            os.environ["PATH"] = p + ";" + os.environ["PATH"]

_setup_latex_path()

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import streamlit as st
import fitz  # PyMuPDF

from src.gui.generator import GeneratorWindows, PROVIDER_GEMINI, PROVIDER_KIMI, PROVIDER_CLAUDE, PROVIDER_OLLAMA
from src import main as pipeline

# ── Constants ────────────────────────────────────────────────────────────────

def resolve_data_path(filename):
    personal_path = os.path.join(PROJECT_ROOT, "personal", "data", filename)
    if os.path.exists(personal_path) or os.path.exists(os.path.join(PROJECT_ROOT, "personal")):
        os.makedirs(os.path.dirname(personal_path), exist_ok=True)
        return personal_path
    return os.path.join(PROJECT_ROOT, "data", filename)

SETTINGS_PATH = resolve_data_path("gui_settings.json")
TRACKER_PATH  = resolve_data_path("tracker.json")
PROMPT_PATH   = resolve_data_path("ai_application_prompt.md")

def get_assets_dir():
    personal_assets = os.path.join(PROJECT_ROOT, "personal", "assets")
    if os.path.exists(personal_assets):
        return personal_assets
    return os.path.join(PROJECT_ROOT, "assets")

ASSETS_DIR    = get_assets_dir()
OUTPUT_DIR    = os.path.join(PROJECT_ROOT, "generated")
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")

SECTION_MAP = {
    "ML Subject":      "templates/sections/ml/subject.tex",
    "ML Recipient":    "templates/sections/ml/recipient.tex",
    "ML Body":         "templates/sections/ml/body.tex",
    "ML Closing":      "templates/sections/ml/closing.tex",
    "Resume Header":   "templates/sections/resume/header.tex",
    "Resume Summary":  "templates/sections/resume/summary.tex",
    "Resume Experience":      "templates/sections/resume/experience.tex",
    "Resume Competencies":    "templates/sections/resume/technical_competencies.tex",
    "Resume Education":       "templates/sections/resume/education.tex",
    "Resume Soft Skills":     "templates/sections/resume/soft_skills.tex",
    "Resume Languages":       "templates/sections/resume/languages.tex",
    "Resume References":      "templates/sections/resume/references.tex",
    "Resume Publications":    "templates/sections/resume/publications.tex",
}

def resolve_section_path(section_name):
    rel_path = SECTION_MAP[section_name]
    personal_path = os.path.join(PROJECT_ROOT, "personal", rel_path)
    if os.path.exists(os.path.join(PROJECT_ROOT, "personal")):
        os.makedirs(os.path.dirname(personal_path), exist_ok=True)
        return personal_path
    return os.path.join(PROJECT_ROOT, rel_path)

def get_user_name():
    personal_dir = os.path.join(PROJECT_ROOT, "personal")
    if os.path.exists(personal_dir):
        return "Juan_Munoz"
    return "John_Doe"

USER_NAME = get_user_name()

PDF_TARGETS = [
    ("Resume",                      "resume",                    "resume.pdf"),
    ("Motivation Letter",           "motivation_letter",         "motivation_letter.pdf"),
    ("ML + Resume",                 "motivation_letter_and_resume", "motivation_letter_and_resume.pdf"),
    ("Experience Attachments",      "professional_experience",   "professional_experience.pdf"),
    ("Education Attachments",       "education",                 "education.pdf"),
    ("Certificates",                "certificates",              "certificates.pdf"),
    ("Other Documents",             "others",                    "others.pdf"),
    ("All Attachments",             "all_attachments",           "all_attachments.pdf"),
    ("Personal Documents",          "personal_documents",        f"Passport_and_Resident_Permit_{USER_NAME}.pdf"),
    ("Full Application Bundle",     "full_bundle",               None),
]

def load_app_config():
    personal_config = os.path.join(PROJECT_ROOT, "personal", "data", "config.json")
    default_config = os.path.join(PROJECT_ROOT, "data", "config.json")
    config_path = personal_config if os.path.exists(personal_config) else default_config
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                data.get("exp_entries", []),
                data.get("focus_themes", []),
                data.get("title_options", [])
            )
    except Exception:
        return (
            [
                {"id": "COMP1", "name": "Tech Corp (Software Development)", "default_title": "Software Engineer"}
            ],
            ["Software Engineering"],
            ["Software Engineer"]
        )

EXP_ENTRIES, FOCUS_THEMES, TITLE_OPTIONS = load_app_config()

# ── Helpers ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_settings():
    defaults = {"model": "claude-opus-4-8", "temperature": 0.2, "max_tokens": 4000,
                "ai_provider": PROVIDER_KIMI, "ollama_model": "qwen2.5:7b"}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                defaults.update(json.load(f))
        except Exception:
            pass
    return defaults


def save_settings(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    existing = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass
    existing.update(data)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(existing, f, indent=2)
    load_settings.clear()


def update_env_key(var, value):
    env_path = os.path.join(PROJECT_ROOT, ".env")
    lines, replaced = [], False
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.strip().startswith(f"{var}="):
                    lines.append(f"{var}={value}\n"); replaced = True
                else:
                    lines.append(line)
    if not replaced:
        lines.append(f"{var}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    os.environ[var] = value


def _get_api_key():
    s = st.session_state.get("settings", {})
    provider = s.get("ai_provider", PROVIDER_GEMINI)
    if provider == PROVIDER_GEMINI:
        return os.environ.get("GEMINI_API_KEY", "")
    elif provider == PROVIDER_KIMI:
        return os.environ.get("KIMI_API_KEY", "")
    elif provider == PROVIDER_OLLAMA:
        return "ollama"
    return os.environ.get("ANTHROPIC_API_KEY", "")


@st.cache_data
def parse_prompt():
    """Returns (examples_list, skills_by_category) from ai_application_prompt.md."""
    examples, skills = [], {}
    if not os.path.exists(PROMPT_PATH):
        return examples, skills
    with open(PROMPT_PATH, encoding="utf-8") as f:
        content = f.read()
    for m in re.finditer(r'###\s*(EX-\d+)\s*·?\s*(.*?)\n(.*?)(?=\n###|\n---|\Z)', content, re.DOTALL):
        ex_id, title, body = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        summary = next((l.replace("- **What:**", "").strip() for l in body.splitlines() if "**What:**" in l), body[:80])
        examples.append({"id": ex_id, "title": title, "summary": summary})
    sm = re.search(r'##\s*MY\s*SKILLS\s*AT\s*A\s*GLANCE(.*?)(?=\n##|\n---|\Z)', content, re.DOTALL)
    if sm:
        for line in sm.group(1).splitlines():
            line = line.strip()
            if line.startswith("**") and ":" in line:
                cat, rest = line.split(":", 1)
                cat = cat.replace("**", "").strip()
                items = [s.strip() for s in re.split(r'[·•]', rest.replace("**", "")) if s.strip()]
                skills.setdefault(cat, []).extend(items)
    return examples, skills


def get_generator():
    return GeneratorWindows(PROJECT_ROOT)


def render_pdf_page_img(pdf_path, page_idx=0, zoom=1.5):
    try:
        doc = fitz.open(pdf_path)
        n = len(doc)
        if n == 0:
            doc.close()
            return None, 0, 0
        page_idx = max(0, min(page_idx, n - 1))
        pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        doc.close()
        return pix.tobytes("png"), n, page_idx
    except Exception as e:
        return None, 0, 0


def resolve_pdf_path(label):
    for lbl, _, fname in PDF_TARGETS:
        if lbl == label:
            if fname:
                return os.path.join(OUTPUT_DIR, fname)
            # Full bundle — newest Compressed_ file
            files = glob.glob(os.path.join(OUTPUT_DIR, "Compressed_*.pdf"))
            if not files:
                files = glob.glob(os.path.join(OUTPUT_DIR, f"{USER_NAME}_*.pdf"))
            return max(files, key=os.path.getmtime) if files else ""
    return ""


def load_tracker():
    if not os.path.exists(TRACKER_PATH):
        return []
    try:
        with open(TRACKER_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def save_tracker(entries):
    os.makedirs(os.path.dirname(TRACKER_PATH), exist_ok=True)
    with open(TRACKER_PATH, "w") as f:
        json.dump(entries, f, indent=4)


def scan_assets():
    categories = {
        "professional_experience": ["intecol_english.pdf","intecol_german.pdf","IPHT0.pdf","IPHT1.pdf"],
        "education": ["Bachelor Diploma.pdf","master.pdf"],
        "certificates": ["B2.pdf","Mündliche_test.pdf","ASML_School.pdf","Zeiss_Summer_School.pdf"],
        "others": ["resident_permit.pdf","passport.pdf"],
    }
    defaults = {"intecol_english.pdf","Bachelor Diploma.pdf","master.pdf",
                "B2.pdf","Mündliche_test.pdf","resident_permit.pdf"}
    if not os.path.exists(ASSETS_DIR):
        return categories, {}, defaults
    actual = set(f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(".pdf"))
    handled = set(f for files in categories.values() for f in files if f in actual)
    uncategorized = actual - handled
    if uncategorized:
        categories["uncategorized"] = sorted(uncategorized)
    return categories, actual, defaults


def get_default_attachments_map():
    categories, actual, defaults = scan_assets()
    default_map = {}
    for cat, fnames in categories.items():
        default_map[cat] = [f for f in fnames if f in actual and f in defaults]
    return default_map


# ── State init ───────────────────────────────────────────────────────────────

def init_state():
    if "sections" not in st.session_state:
        st.session_state.sections = {}
    if "pdf_page" not in st.session_state:
        st.session_state.pdf_page = 0
    if "pdf_zoom" not in st.session_state:
        st.session_state.pdf_zoom = 1.5
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "tracker" not in st.session_state:
        st.session_state.tracker = load_tracker()
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
    if "attachments_map" not in st.session_state:
        st.session_state.attachments_map = get_default_attachments_map()
    if "compile_sel" not in st.session_state:
        st.session_state.compile_sel = "Full Application Bundle"
    if "preview_sel" not in st.session_state:
        st.session_state.preview_sel = "Full Application Bundle"


# ── Sidebar settings ─────────────────────────────────────────────────────────

def render_sidebar():
    st.sidebar.title("Settings")
    s = st.session_state.settings

    provider = st.sidebar.selectbox(
        "AI Provider",
        [PROVIDER_GEMINI, PROVIDER_KIMI, PROVIDER_CLAUDE, PROVIDER_OLLAMA],
        index=[PROVIDER_GEMINI, PROVIDER_KIMI, PROVIDER_CLAUDE, PROVIDER_OLLAMA].index(s.get("ai_provider", PROVIDER_GEMINI)),
        format_func=lambda p: {"gemini": "Gemini 2.0 Flash (free)",
                               "kimi": "Kimi / Moonshot (free tier)",
                               "claude": "Claude (paid)",
                               "ollama": "Ollama (local AI model)"}[p],
    )
    if provider != s.get("ai_provider"):
        save_settings({"ai_provider": provider})
        st.session_state.settings = load_settings()
        st.rerun()

    if provider == PROVIDER_GEMINI:
        key = st.sidebar.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY",""), type="password",
                                    help="Get free key at aistudio.google.com/apikey")
        if key != os.environ.get("GEMINI_API_KEY",""):
            update_env_key("GEMINI_API_KEY", key)

    elif provider == PROVIDER_KIMI:
        key = st.sidebar.text_input("Kimi API Key", value=os.environ.get("KIMI_API_KEY",""), type="password",
                                    help="Get key at platform.moonshot.cn")
        if key != os.environ.get("KIMI_API_KEY",""):
            update_env_key("KIMI_API_KEY", key)

    elif provider == PROVIDER_OLLAMA:
        model_val = st.sidebar.text_input("Ollama Model Tag", value=s.get("ollama_model", "qwen2.5:7b"),
                                          help="Local Ollama model name (e.g. qwen2.5:7b, gemma4:e4b)")
        if model_val != s.get("ollama_model"):
            save_settings({"ollama_model": model_val})
            st.session_state.settings = load_settings()

    else:  # Claude
        key = st.sidebar.text_input("Anthropic API Key", value=os.environ.get("ANTHROPIC_API_KEY",""), type="password")
        if key != os.environ.get("ANTHROPIC_API_KEY",""):
            update_env_key("ANTHROPIC_API_KEY", key)

    if st.sidebar.button("Save Settings"):
        save_settings({"ai_provider": provider})
        st.session_state.settings = load_settings()
        st.sidebar.success("Saved!")


def sync_attachment(fname, source_key, target_key):
    st.session_state[target_key] = st.session_state[source_key]
    categories, actual_assets, _ = scan_assets()
    new_map = {"professional_experience":[],"education":[],"certificates":[],"others":[]}
    for cat, fnames in categories.items():
        for f in fnames:
            if f in actual_assets:
                if st.session_state.get(f"att_{f}", False):
                    new_map.setdefault(cat, []).append(f)
    st.session_state.attachments_map = new_map


# ── Tab 1: Configure & Generate ──────────────────────────────────────────────

def tab_configure():
    st.header("Configure & Generate")
    examples, skills = parse_prompt()
    categories, actual_assets, default_assets = scan_assets()

    # Job info
    with st.expander("Job Information", expanded=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            job_url = st.text_input("Job URL (optional)", key="job_url",
                                    placeholder="https://example.com/careers/...")
        with col2:
            st.write("")
            fetch_clicked = st.button("Fetch & Parse", width="stretch")

        if fetch_clicked and job_url:
            with st.spinner("Fetching…"):
                try:
                    import requests, html2text
                    r = requests.get(job_url, headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
                    r.raise_for_status()
                    converter = html2text.HTML2Text()
                    converter.ignore_links = True
                    converter.ignore_images = True
                    fetched = converter.handle(r.text)
                    st.session_state["job_desc"] = fetched
                    st.rerun()
                except Exception as e:
                    st.error(f"Fetch failed: {e}")

        job_desc = st.text_area("Job Description", height=180, key="job_desc",
                                placeholder="Paste the job description here…")


        col_extract, _ = st.columns([1, 3])
        with col_extract:
            extract_clicked = st.button("✨ Auto-Extract Details")
        if extract_clicked and st.session_state.get("job_desc","").strip():
            with st.spinner("Extracting details…"):
                try:
                    g = get_generator()
                    api_key = _get_api_key()
                    result = g.extract_job_details(
                        api_key=api_key,
                        job_description=st.session_state["job_desc"],
                        context_dict={
                            "foci": FOCUS_THEMES,
                            "examples": [e["id"] for e in examples],
                            "skills": [sk for items in skills.values() for sk in items],
                            "experience_entries": [e["name"] for e in EXP_ENTRIES],
                        }
                    )
                    if result.get("company"):
                        st.session_state["rec_company"] = result["company"]
                    if result.get("position") and result["position"] != "Unknown Position":
                        st.session_state["title_sel"] = result["position"]
                    if result.get("foci"):
                        st.session_state["focus"] = result["foci"]
                    if result.get("skills"):
                        st.session_state["skills_sel"] = result["skills"]
                    st.success("Details auto-extracted!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Extraction failed: {e}")

    # Profile
    with st.expander("Target Profile", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            title_options = TITLE_OPTIONS.copy()
            if "title_sel" not in st.session_state:
                title_input = st.session_state.get("title_input", TITLE_OPTIONS[0])
                if title_input not in title_options:
                    title_options.insert(0, title_input)
                st.session_state["title_sel"] = title_input
            else:
                if st.session_state["title_sel"] not in title_options:
                    title_options.insert(0, st.session_state["title_sel"])
            title = st.selectbox("Professional Title", title_options, key="title_sel")
        with col2:
            focus_options = FOCUS_THEMES.copy()
            if "focus" in st.session_state:
                val = st.session_state["focus"]
                if isinstance(val, str):
                    val = [s.strip() for s in val.split(",") if s.strip()]
                elif not isinstance(val, list):
                    val = list(val)
                st.session_state["focus"] = val
                for f in val:
                    if f not in focus_options:
                        focus_options.append(f)
                focus = st.multiselect("Motivation Letter Focus", focus_options, key="focus")
            else:
                focus = st.multiselect("Motivation Letter Focus", focus_options, default=[], key="focus")

    # Examples
    with st.expander(f"Professional Examples ({len(examples)} available)"):
        ex_options = {f"{e['id']}: {e['title']}": e["id"] for e in examples}
        sel_ex_labels = st.multiselect("Select 2–3 examples to feature", list(ex_options.keys()),
                                       key="examples_sel")
        selected_examples = [ex_options[l] for l in sel_ex_labels]

    # Skills
    with st.expander("Skills"):
        all_skills = [sk for items in skills.values() for sk in items]
        if "skills_sel" in st.session_state:
            val = st.session_state["skills_sel"]
            if isinstance(val, str):
                val = [s.strip() for s in val.split(",") if s.strip()]
            elif not isinstance(val, list):
                val = list(val)
            st.session_state["skills_sel"] = val
            for s in val:
                if s not in all_skills:
                    all_skills.append(s)
            sel_skills = st.multiselect("Select skills to highlight", all_skills, key="skills_sel")
        else:
            sel_skills = st.multiselect("Select skills to highlight", all_skills, default=[], key="skills_sel")
        
        if sel_skills:
            st.write("Select degree of experience for each skill:")
            for s in sel_skills:
                col_sk1, col_sk2 = st.columns([3, 2])
                col_sk1.write(f"**{s}**")
                col_sk2.selectbox("Level", ["Expertise", "Knowledge"], key=f"sk_lvl_{s}", label_visibility="collapsed")

    # Experience
    with st.expander("Resume Experience Entries"):
        exp_entries = []
        for entry in EXP_ENTRIES:
            cols = st.columns([3, 4])
            enabled = cols[0].checkbox(entry["name"], value=True, key=f"exp_en_{entry['id']}")
            title_val = cols[1].text_input("Job Title", entry["default_title"], key=f"exp_t_{entry['id']}")
            exp_entries.append({"id": entry["id"], "name": entry["name"],
                                 "enabled": enabled, "title": title_val})

    # Attachments
    with st.expander("Attachment PDFs"):
        if actual_assets:
            for cat, fnames in categories.items():
                st.write(f"**{cat.replace('_',' ').title()}**")
                cols = st.columns(3)
                for i, fname in enumerate(fnames):
                    if fname in actual_assets:
                        is_checked = (fname in st.session_state.attachments_map.get(cat, []))
                        if f"att_{fname}" not in st.session_state:
                            st.session_state[f"att_{fname}"] = is_checked
                        cols[i%3].checkbox(fname, key=f"att_{fname}",
                                           on_change=sync_attachment, args=(fname, f"att_{fname}", f"att_ed_{fname}"))
        else:
            st.info("No PDFs found in assets/")
        attachments_map = st.session_state.attachments_map

    # Options
    with st.expander("Application Options"):
        col1, col2, col3 = st.columns(3)
        lang = col1.radio("Language", ["German (DE)","English (EN)","Auto"], key="lang")
        salary = col2.text_input("Salary (or 'omit')", "omit", key="salary")
        page_limit = col3.number_input("Resume pages", 1, 4, 2, key="page_limit")
        humanize = st.checkbox("Humanize writing style", True, key="humanize")

    # Recipient
    with st.expander("Recipient Block"):
        rec_company = st.text_input("Company Name", st.session_state.get("rec_company",""), key="rec_company")
        rec_contact = st.text_input("Contact Person", "Recruiting Team", key="rec_contact")
        rec_address = st.text_input("Address / Location", key="rec_address")

    # Generate
    st.divider()
    if st.button("Generate Tailored Application", type="primary", width="stretch"):
        job_description = st.session_state.get("job_desc","").strip()
        if not job_description:
            st.error("Job description is required.")
            return

        lang_code = "de" if "German" in st.session_state.get("lang","German") else \
                    "en" if "English" in st.session_state.get("lang","") else "auto"

        params = {
            "job_description": job_description,
            "title": st.session_state.get("title_sel", TITLE_OPTIONS[0]),
            "focus": st.session_state.get("focus", []),
            "examples": selected_examples,
            "skills": [{"name": s, "level": st.session_state.get(f"sk_lvl_{s}", "Expertise")} for s in st.session_state.get("skills_sel",[])],
            "experience": exp_entries,
            "attachments": attachments_map,
            "language": lang_code,
            "salary": st.session_state.get("salary","omit"),
            "recipient_company": st.session_state.get("rec_company",""),
            "recipient_contact": st.session_state.get("rec_contact","Recruiting Team"),
            "recipient_address": st.session_state.get("rec_address",""),
            "page_limit": st.session_state.get("page_limit", 2),
            "humanize": st.session_state.get("humanize", True),
        }

        # Load career context
        career_context = ""
        if os.path.exists(PROMPT_PATH):
            with open(PROMPT_PATH, encoding="utf-8") as f:
                career_context = f.read()

        settings = st.session_state.settings
        api_key = _get_api_key()

        with st.spinner("Generating application sections…"):
            try:
                g = get_generator()
                sections = g.generate_application(
                    api_key=api_key,
                    params=params,
                    style_profile="",
                    career_context=career_context,
                    papers_dict={},
                    model=settings.get("model","claude-opus-4-8"),
                    temperature=settings.get("temperature", 0.2),
                )
                g.write_sections(sections)
                st.session_state.sections = sections
                st.success("Generation complete! Switch to the Edit & Preview tab.")
            except Exception as e:
                st.error(f"Generation failed: {e}")

        # Auto-compile
        with st.spinner("Compiling PDFs…"):
            try:
                pipeline.setup_latex_path()
                pipeline.compile_target("full_bundle", st.session_state.attachments_map)
                st.success("Compiled successfully!")
            except Exception as e:
                st.warning(f"Compilation note: {e}")


# ── Tab 2: Edit & Preview ────────────────────────────────────────────────────

def tab_editor():
    st.header("Edit LaTeX & Preview PDF")
    
    with st.expander("📎 Select Attachment PDFs", expanded=False):
        categories, actual_assets, default_assets = scan_assets()
        if actual_assets:
            for cat, fnames in categories.items():
                st.write(f"**{cat.replace('_',' ').title()}**")
                cols = st.columns(3)
                for i, fname in enumerate(fnames):
                    if fname in actual_assets:
                        is_checked = (fname in st.session_state.attachments_map.get(cat, []))
                        if f"att_ed_{fname}" not in st.session_state:
                            st.session_state[f"att_ed_{fname}"] = is_checked
                        cols[i%3].checkbox(fname, key=f"att_ed_{fname}",
                                           on_change=sync_attachment, args=(fname, f"att_ed_{fname}", f"att_{fname}"))
        else:
            st.info("No PDFs found in assets/")

    with st.expander("📦 Save & Restore Working Application", expanded=False):
        st.write("Save your current generated LaTeX sections to continue editing them later, or restore a previously saved application.")
        col_s, col_r = st.columns(2)
        
        saves_dir = os.path.join(PROJECT_ROOT, "saved_applications")
        os.makedirs(saves_dir, exist_ok=True)
        
        with col_s:
            st.subheader("💾 Save Application")
            save_name = st.text_input("Save Name", placeholder="e.g. Zeiss_Optical_Engineer", key="app_save_name")
            if st.button("Save Current Application", type="primary", width="stretch"):
                if not save_name.strip():
                    st.warning("Please enter a valid save name.")
                else:
                    target_save_dir = os.path.join(saves_dir, save_name.strip())
                    os.makedirs(target_save_dir, exist_ok=True)
                    # Copy all section files
                    for sec_key, rel_sec in SECTION_MAP.items():
                        src_path = resolve_section_path(sec_key)
                        if os.path.exists(src_path):
                            dest_path = os.path.join(target_save_dir, os.path.basename(rel_sec))
                            shutil.copy2(src_path, dest_path)
                    st.success(f"Successfully saved application as '{save_name.strip()}'!")

        with col_r:
            st.subheader("📂 Restore Application")
            existing_saves = [d for d in os.listdir(saves_dir) if os.path.isdir(os.path.join(saves_dir, d))]
            if not existing_saves:
                st.info("No saved applications found yet.")
            else:
                selected_save = st.selectbox("Select Saved Application", existing_saves, key="app_restore_name")
                if st.button("Restore Application", width="stretch"):
                    source_save_dir = os.path.join(saves_dir, selected_save)
                    # Copy back to active sections dir
                    for sec_key, rel_sec in SECTION_MAP.items():
                        active_path = resolve_section_path(sec_key)
                        saved_file = os.path.join(source_save_dir, os.path.basename(rel_sec))
                        if os.path.exists(saved_file):
                            os.makedirs(os.path.dirname(active_path), exist_ok=True)
                            shutil.copy2(saved_file, active_path)
                    st.success(f"Successfully restored application '{selected_save}'!")
                    st.rerun()

    col_ed, col_prev = st.columns([1, 1])

    with col_ed:
        section_name = st.selectbox("Section", list(SECTION_MAP.keys()), key="section_sel")
        section_path = resolve_section_path(section_name)
        # Load from disk
        current_content = ""
        if os.path.exists(section_path):
            with open(section_path, encoding="utf-8") as f:
                current_content = f.read()

        if st.session_state.get("compile_success_msg"):
            st.success(st.session_state["compile_success_msg"])
            st.session_state["compile_success_msg"] = None

        edited = st.text_area("LaTeX Source", value=current_content, height=500,
                              key=f"editor_{section_name}",
                              help="Edit LaTeX directly. Changes are automatically saved and compiled.")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Save to disk", width="stretch"):
                os.makedirs(os.path.dirname(section_path), exist_ok=True)
                with open(section_path, "w", encoding="utf-8") as f:
                    f.write(edited)
                st.success("Saved.")

        if "compile_sel" not in st.session_state:
            st.session_state["compile_sel"] = "Full Application Bundle"
        target_label = st.selectbox("Compile target", [t[0] for t in PDF_TARGETS], key="compile_sel")
        target_key = next(t[1] for t in PDF_TARGETS if t[0] == target_label)

        with col2:
            if st.button("Save & Compile", type="primary", width="stretch"):
                os.makedirs(os.path.dirname(section_path), exist_ok=True)
                with open(section_path, "w", encoding="utf-8") as f:
                    f.write(edited)
                with st.spinner("Compiling…"):
                    try:
                        pipeline.setup_latex_path()
                        result = pipeline.compile_target(target_key, st.session_state.get("attachments_map"))
                        if result:
                            st.success(f"Compiled: {os.path.basename(result)}")
                        else:
                            st.warning("Compile returned no output.")
                    except Exception as e:
                        st.error(f"Compile error: {e}")

        if edited != current_content:
            os.makedirs(os.path.dirname(section_path), exist_ok=True)
            with open(section_path, "w", encoding="utf-8") as f:
                f.write(edited)
            with st.spinner("Auto-compiling changes…"):
                try:
                    pipeline.setup_latex_path()
                    result = pipeline.compile_target(target_key, st.session_state.get("attachments_map"))
                    if result:
                        st.session_state["compile_success_msg"] = f"Auto-compiled: {os.path.basename(result)}"
                    else:
                        st.session_state["compile_success_msg"] = "Auto-compile finished (no output returned)."
                except Exception as e:
                    st.session_state["compile_success_msg"] = f"Auto-compile error: {e}"
            st.rerun()

    with col_prev:
        if "preview_sel" not in st.session_state:
            st.session_state["preview_sel"] = "Full Application Bundle"
        preview_label = st.selectbox("Preview document", [t[0] for t in PDF_TARGETS], key="preview_sel")
        pdf_path = resolve_pdf_path(preview_label)

        nav1, nav2, nav3, nav4, nav5 = st.columns([1,1,2,1,1])
        if nav1.button("◀"):
            st.session_state.pdf_page = max(0, st.session_state.pdf_page - 1)
        if nav5.button("▶"):
            st.session_state.pdf_page += 1
        if nav3.button("Zoom +"):
            st.session_state.pdf_zoom = min(3.0, st.session_state.pdf_zoom + 0.25)
        if nav4.button("Zoom -"):
            st.session_state.pdf_zoom = max(0.5, st.session_state.pdf_zoom - 0.25)
        if nav2.button("Fit"):
            st.session_state.pdf_zoom = 1.5

        if pdf_path and os.path.exists(pdf_path):
            img_bytes, n_pages, page_idx = render_pdf_page_img(
                pdf_path, st.session_state.pdf_page, st.session_state.pdf_zoom)
            st.session_state.pdf_page = page_idx
            if img_bytes:
                st.image(img_bytes, caption=f"Page {page_idx+1} of {n_pages}  |  {os.path.basename(pdf_path)}")
                with open(pdf_path, "rb") as f:
                    st.download_button("Download PDF", f.read(),
                                       file_name=os.path.basename(pdf_path), mime="application/pdf")
            else:
                st.warning("Could not render PDF page.")
        else:
            st.info("No PDF found. Generate or compile first.")


# ── Tab 3: AI Chat ────────────────────────────────────────────────────────────

def tab_chat():
    st.header("AI Chat Assistant")
    section_name = st.selectbox("Section to edit", list(SECTION_MAP.keys()), key="chat_section")
    section_path = resolve_section_path(section_name)

    current_content = ""
    if os.path.exists(section_path):
        with open(section_path, encoding="utf-8") as f:
            current_content = f.read()
    st.text_area("Current content (read-only)", value=current_content, height=200, disabled=True)

    st.subheader("Chat History")
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"][:500] + ("…" if len(msg["content"])>500 else ""))

    user_prompt = st.chat_input("Instruction (e.g. 'Make the first paragraph more concise')")
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.spinner("Editing with AI…"):
            try:
                g = get_generator()
                api_key = _get_api_key()
                updated = g.edit_section(api_key=api_key, current_text=current_content,
                                         user_prompt=user_prompt)
                # Write back
                os.makedirs(os.path.dirname(section_path), exist_ok=True)
                with open(section_path, "w", encoding="utf-8") as f:
                    f.write(updated)
                st.session_state.chat_history.append({"role": "assistant", "content": updated})
                st.success("Section updated. Recompile in the Edit tab.")
                st.rerun()
            except Exception as e:
                st.error(f"AI edit failed: {e}")

    if st.button("Clear chat history"):
        st.session_state.chat_history = []
        st.rerun()


# ── Tab 4: Tracker ───────────────────────────────────────────────────────────

def tab_tracker():
    st.header("Application Tracker")
    entries = st.session_state.tracker

    if entries:
        import pandas as pd
        df = pd.DataFrame(reversed(entries))
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("No applications logged yet.")

    st.divider()
    with st.expander("Add Entry"):
        col1, col2 = st.columns(2)
        company  = col1.text_input("Company", key="t_company")
        position = col2.text_input("Position", key="t_position")
        status   = col1.selectbox("Status", ["Draft","Applied","Interviewing","Offer","Rejected"],
                                  index=1, key="t_status")
        notes    = col2.text_input("Notes", key="t_notes")
        if st.button("Add", type="primary"):
            if company or position:
                entry = {"date": datetime.now().strftime("%Y-%m-%d"),
                         "company": company, "position": position,
                         "status": status, "notes": notes}
                st.session_state.tracker.append(entry)
                save_tracker(st.session_state.tracker)
                st.success("Entry added.")
                st.rerun()

    if entries:
        with st.expander("Update / Delete"):
            idx = st.number_input("Entry # (0 = newest)", 0, len(entries)-1, 0)
            real_idx = len(entries) - 1 - idx
            entry = entries[real_idx]
            st.write(f"**{entry['date']}** — {entry['company']} | {entry['position']} | {entry['status']}")
            new_status = st.selectbox("New status", ["Draft","Applied","Interviewing","Offer","Rejected"],
                                      index=["Draft","Applied","Interviewing","Offer","Rejected"].index(
                                          entry.get("status","Applied")), key=f"t_new_status_{real_idx}")
            col1, col2 = st.columns(2)
            if col1.button("Update Status"):
                st.session_state.tracker[real_idx]["status"] = new_status
                save_tracker(st.session_state.tracker)
                st.rerun()
            if col2.button("Delete Entry", type="secondary"):
                del st.session_state.tracker[real_idx]
                save_tracker(st.session_state.tracker)
                st.rerun()


# ── Tab 5: A4 Document Scaler & Merger ───────────────────────────────────────

def tab_scaler():
    st.header("A4 Document Scaler & Merger")
    st.write("Easily merge and scale multiple images or PDF documents (e.g., front and back of a resident permit or passport) into a single perfectly-proportioned A4 PDF page.")

    uploaded_files = st.file_uploader("Upload Images / PDFs to Merge (PNG, JPG, PDF)", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True, key="scaler_uploader")
    
    col1, col2 = st.columns(2)
    with col1:
        out_name = st.text_input("Output Asset Filename", value="resident_permit.pdf", key="scaler_out_name")
        if not out_name.endswith(".pdf"):
            out_name += ".pdf"

    with col2:
        image_width = st.slider("Scaling Width (% of A4 text width)", min_value=50, max_value=100, value=85, step=5, key="scaler_width")

    if st.button("Scale, Merge & Save to Assets", type="primary", width="stretch"):
        if not uploaded_files:
            st.warning("Please upload at least one file to merge.")
            return

        with st.spinner("Generating A4 scaled PDF..."):
            try:
                output_dir = os.path.join(PROJECT_ROOT, "generated")
                os.makedirs(output_dir, exist_ok=True)
                temp_dir = os.path.join(output_dir, "scale_temp")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Save uploaded files to temp_dir
                file_paths = []
                for uf in uploaded_files:
                    fpath = os.path.join(temp_dir, uf.name)
                    with open(fpath, "wb") as f:
                        f.write(uf.getbuffer())
                    # Convert path to forward slashes for LaTeX
                    file_paths.append(fpath.replace("\\", "/"))

                # Generate scaled_document.tex
                max_height = 0.9 / len(file_paths)
                
                latex_code = f"""\\documentclass[a4paper]{{article}}
\\usepackage[margin=1.5cm]{{geometry}}
\\usepackage{{graphicx}}
\\usepackage{{grffile}}
\\pagestyle{{empty}}
\\begin{{document}}
\\begin{{center}}
"""
                for i, fp in enumerate(file_paths):
                    latex_code += f"\\includegraphics[width={image_width/100.0}\\textwidth,height={max_height}\\textheight,keepaspectratio]{{{fp}}}\n"
                    if i < len(file_paths) - 1:
                        latex_code += "\\vspace{1cm}\n"

                latex_code += """\\end{center}
\\end{document}
"""
                tex_path = os.path.join(output_dir, "scaled_document.tex")
                with open(tex_path, "w", encoding="utf-8") as f:
                    f.write(latex_code)

                # Compile with pdflatex
                run_env = dict(os.environ, TEXMFOUTPUT=output_dir)
                pipeline.setup_latex_path()
                cmd = ['pdflatex', '-output-directory', output_dir, '-interaction=nonstopmode', 'scaled_document.tex']
                res = subprocess.run(cmd, cwd=output_dir, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

                pdf_path = os.path.join(output_dir, "scaled_document.pdf")
                if res.returncode == 0 and os.path.exists(pdf_path):
                    # Save to personal/assets/
                    personal_assets = os.path.join(PROJECT_ROOT, "personal", "assets")
                    os.makedirs(personal_assets, exist_ok=True)
                    target_asset = os.path.join(personal_assets, out_name)
                    shutil.copy2(pdf_path, target_asset)
                    
                    # Also copy to assets/ for fallback
                    base_assets = os.path.join(PROJECT_ROOT, "assets")
                    os.makedirs(base_assets, exist_ok=True)
                    shutil.copy2(pdf_path, os.path.join(base_assets, out_name))

                    st.success(f"Successfully scaled and merged documents into {out_name}!")
                    
                    # Display PDF preview
                    with open(target_asset, "rb") as f:
                        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}#toolbar=0&navpanes=0" width="100%" height="600" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                else:
                    st.error("LaTeX compilation failed during scaling. Check file formats or logs.")
                    st.code(res.stdout)
            except Exception as e:
                st.error(f"Error during scaling and merging: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Job Application Generator", layout="wide",
                   page_icon="📄", initial_sidebar_state="expanded")

st.markdown("""
<style>
textarea[data-testid="stTextArea"] textarea {
    font-family: 'Courier New', monospace;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

init_state()
render_sidebar()

st.title("Job Application LaTeX Generator")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Configure & Generate", "2. Edit & Preview", "3. AI Chat", "4. Tracker", "5. A4 Document Scaler"])

with tab1:
    tab_configure()

with tab2:
    tab_editor()

with tab3:
    tab_chat()

with tab4:
    tab_tracker()

with tab5:
    tab_scaler()
