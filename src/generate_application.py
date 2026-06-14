#!/usr/bin/env python3
"""
generate_application.py
-----------------------
Reads your research papers, professional experience bank, and a job offer.
Uses the Gemini API to write tailored content for your resume and motivation letter.
Automatically updates the corresponding LaTeX files in templates/sections/
so you can just run `python src/main.py` immediately after.

Usage:
    python3 src/generate_application.py --job-url "https://..." [--lang de|en]

Dependencies: pypdf, requests, html2text, google-generativeai
"""

import argparse
import os
import sys
import re
import textwrap

import html2text
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

try:
    import google.generativeai as genai
except ImportError:
    sys.exit("google-generativeai not found. Run: pip3 install google-generativeai")

API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    sys.exit(
        "No Gemini API key found.\n"
        "Set it with:  export GOOGLE_API_KEY='your-key-here'\n"
        "Or:           export GEMINI_API_KEY='your-key-here'"
    )

genai.configure(api_key=API_KEY)
MODEL = genai.GenerativeModel("gemini-2.0-flash")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Helpers ─────────────────────────────────────────────────────────────────

def extract_pdf_text(path: str, max_chars: int = 4_000) -> str:
    """Extract and truncate text from a PDF file."""
    try:
        reader = PdfReader(path)
        pages_text = []
        for page in reader.pages:
            pages_text.append(page.extract_text() or "")
        full = "\n".join(pages_text)
        return full[:max_chars]
    except Exception as e:
        print(f"  ⚠ Could not read {path}: {e}", file=sys.stderr)
        return ""

def fetch_job_description(url: str = None, file_path: str = None) -> str:
    """Get job description from URL or local file."""
    if file_path:
        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            sys.exit(f"Could not read job file: {e}")
    
    if url:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; AppGenerator/1.0)"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            converter = html2text.HTML2Text()
            converter.ignore_links = True
            converter.ignore_images = True
            text = converter.handle(resp.text)
            return text[:6000]
        except Exception as e:
            sys.exit(f"Could not fetch job URL: {e}")
    
    return ""

def load_career_context() -> str:
    """Load the candidate's career context from the prompt file."""
    prompt_path = os.path.join(PROJECT_ROOT, "data", "ai_application_prompt.md")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠ Could not load career context: {e}", file=sys.stderr)
        return ""

def build_prompt(papers: dict[str, str], job_text: str, career_context: str, lang: str) -> str:
    """Construct the Gemini prompt."""
    paper_sections = ""
    for name, content in papers.items():
        paper_sections += f"\n### Paper: {name}\n{content}\n"

    lang_instruction = "German" if lang == "de" else "English"
    if lang == "auto":
        lang_instruction = "the language of the job description (default to German if unsure)"

    return textwrap.dedent(f"""
        You are an expert technical career advisor and LaTeX document generator helping 
        Juan David Muñoz Bolaños tailor his application for a specific job opening.

        == CANDIDATE'S CAREER & EXAMPLES BANK ==
        {career_context}

        == CANDIDATE'S RESEARCH PAPERS ==
        {paper_sections}

        == JOB DESCRIPTION ==
        {job_text}

        == STRICTURES (CRITICAL) ==
        - NO DASHES: Never use "-", "–", or "—" in the text or dates. Use "to" for date ranges.
        - NO ARROWS: Never use "→", "\\rightarrow", or "->" in content text.
        - VERTICAL SPINE: Resume content must be aligned at exactly 103pt from the left using `\\begin{{adjustwidth}}{{103pt}}{{0pt}}`.
        - BE CONCRETE: Base every skill on specific projects, papers, or the examples bank. NO HALLUCINATION. DO NOT use random filler words.
        - HARD WRAP: Content in the source must be manually wrapped at ~80 characters.
        - LATEX SAFE: Escape special LaTeX characters appropriately (e.g., \\&, \\%, \\_).

        == TASK ==
        Generate tailored LaTeX code for 5 distinct files. 
        Your entire response MUST be formatted using the XML-like tags exactly as shown below, with the exact LaTeX content inside.
        
        1. Motivation Letter Language: {lang_instruction}.
        2. Resume: Always in English.
        3. Extract the Hiring Manager name and company name for the recipient block. If unknown, use general terms (e.g. Hiring Manager).
        4. Select 2-3 of the MOST relevant Personal Examples from the bank to feature in the Motivation Letter and Experience.
        5. DO NOT output any markdown blocks outside the tags.

        <ML_SUBJECT>
        % Subject Line
        \\textbf{{Bewerbung als [Position] | Ref. [Ref_Number]}} (Translate "Bewerbung als" if ML is in English)
        </ML_SUBJECT>

        <ML_RECIPIENT>
        % Recipient Information
        \\textbf{{[Company Name]}}\\\\
        [Department / Hiring Manager name if available]\\\\
        [Address if available]
        </ML_RECIPIENT>

        <ML_BODY>
        Dear [Name] / Sehr geehrte(r)...,

        [Paragraph 1: Hook and position]

        [Paragraph 2: Relevant experience based ONLY on papers and examples bank]

        [Paragraph 3: Additional relevant skills based ONLY on papers and examples bank]

        [Paragraph 4: Closing, PhD completion in June 2026, and permit seamlessly converts to working permit.]

        Sincerely / Mit freundlichen Grüßen,
        </ML_BODY>

        <RESUME_EXPERIENCE>
        \\section{{Professional/Research Experience}}

        \\entry{{[Institution 1]}}{{[Location]}}{{[Title]}}{{[Date to Date]}}    

        \\begin{{adjustwidth}}{{103pt}}{{0pt}}
            \\textbf{{[Skill/Project 1]:}}
            [Description based on actual experience/papers].\\sepbullet

            \\textbf{{[Skill/Project 2]:}}
            [Description based on actual experience/papers].
        \\end{{adjustwidth}}

        \\sepentry

        \\entry{{[Institution 2]}}{{[Location]}}{{[Title]}}{{[Date to Date]}}

        \\begin{{adjustwidth}}{{103pt}}{{0pt}}
            \\textbf{{[Skill/Project 3]:}}
            [Description based on actual experience/papers].\\sepbullet

            \\textbf{{[Skill/Project 4]:}}
            [Description based on actual experience/papers].
        \\end{{adjustwidth}}
        </RESUME_EXPERIENCE>

        <RESUME_COMPETENCIES>
        % --- TECHNICAL COMPETENCIES ---
        \\section{{Technical Competencies}}

        \\begin{{adjustwidth}}{{103pt}}{{0pt}}
            \\textbf{{[Category 1]:}}
            [List of relevant technical skills/tools].\\sepbullet

            \\textbf{{[Category 2]:}}
            [List of relevant technical skills/tools].\\sepbullet

            \\textbf{{[Category 3]:}}
            [List of relevant technical skills/tools].
        \\end{{adjustwidth}}
        </RESUME_COMPETENCIES>
    """)

def extract_tag(text: str, tag: str) -> str:
    """Extract content inside <TAG>...</TAG>."""
    pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return ""

def update_file(rel_path: str, content: str):
    """Write content to a file if content is not empty."""
    if not content:
        print(f"  ⚠ Warning: No content generated for {rel_path}")
        return
        
    abs_path = os.path.join(PROJECT_ROOT, rel_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content + "\n")
    print(f"  ✓ Updated {rel_path}")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate tailored application files (resume + motivation letter) using AI."
    )
    parser.add_argument("--job-url", help="URL of the job posting")
    parser.add_argument("--job-file", help="Path to a local text file containing the job description")
    parser.add_argument("--lang", choices=["de", "en", "auto"], default="de", 
                        help="Language for the Motivation Letter (default: de)")
    parser.add_argument("--papers", default="assets/papers",
                        help="Path to a directory of PDFs or a single PDF file (default: assets/papers/)")
    
    args = parser.parse_args()

    if not (args.job_url or args.job_file):
        sys.exit("Error: You must provide either --job-url or --job-file")

    # 1. Collect PDFs
    paper_dir = os.path.join(PROJECT_ROOT, args.papers if not os.path.isabs(args.papers) else "")
    if os.path.isabs(args.papers):
        paper_dir = args.papers

    pdf_paths = []
    if os.path.isfile(paper_dir):
        pdf_paths = [paper_dir]
    elif os.path.isdir(paper_dir):
        pdf_paths = sorted(
            os.path.join(paper_dir, f)
            for f in os.listdir(paper_dir)
            if f.lower().endswith(".pdf")
        )

    papers: dict[str, str] = {}
    print(f"\n📄 Loading {len(pdf_paths)} paper(s)...")
    for path in pdf_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        text = extract_pdf_text(path)
        if text:
            papers[name] = text

    # 2. Load Career Context
    print("📚 Loading career context and examples bank...")
    career_context = load_career_context()

    # 3. Fetch Job Description
    source = args.job_url if args.job_url else args.job_file
    print(f"🌐 Fetching job description from: {source}")
    job_text = fetch_job_description(url=args.job_url, file_path=args.job_file)
    
    if not job_text:
        sys.exit("Error: Could not retrieve job description content.")

    # 4. Call Gemini
    print("\n🤖 Generating tailored application via Gemini AI (this may take ~20 seconds)...")
    prompt = build_prompt(papers, job_text, career_context, args.lang)
    
    try:
        response = MODEL.generate_content(prompt)
        result = response.text
    except Exception as e:
        sys.exit(f"Gemini API error: {e}")

    # 5. Extract and Update Files
    print("\n💾 Updating LaTeX templates...")
    
    ml_subject = extract_tag(result, "ML_SUBJECT")
    ml_recipient = extract_tag(result, "ML_RECIPIENT")
    ml_body = extract_tag(result, "ML_BODY")
    resume_exp = extract_tag(result, "RESUME_EXPERIENCE")
    resume_comp = extract_tag(result, "RESUME_COMPETENCIES")

    update_file("templates/sections/ml/subject.tex", ml_subject)
    update_file("templates/sections/ml/recipient.tex", ml_recipient)
    update_file("templates/sections/ml/body.tex", ml_body)
    update_file("templates/sections/resume/experience.tex", resume_exp)
    update_file("templates/sections/resume/technical_competencies.tex", resume_comp)

    print("\n✅ Done! The LaTeX files have been updated.")
    print("   Run `python3 src/main.py` to build the new PDF.")

if __name__ == "__main__":
    main()
