#!/usr/bin/env python3
"""
match_skills.py
---------------
Reads your research paper PDFs, fetches a job offer URL, and uses the
Gemini API to match methods from your papers to the job requirements.
Outputs LaTeX-ready bullet point suggestions for your resume.

Usage:
    python3 src/match_skills.py --job-url "https://..." [--papers assets/papers/]

Dependencies: pypdf, requests, html2text, google-generativeai
"""

import argparse
import os
import sys
import textwrap

import html2text
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()

# ── Gemini setup ────────────────────────────────────────────────────────────
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
MODEL = genai.GenerativeModel("gemini-3.1-pro-preview")

# ── Helpers ─────────────────────────────────────────────────────────────────

def extract_pdf_text(path: str, max_chars: int = 12_000) -> str:
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
            headers = {"User-Agent": "Mozilla/5.0 (compatible; SkillMatcher/1.0)"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            converter = html2text.HTML2Text()
            converter.ignore_links = True
            converter.ignore_images = True
            text = converter.handle(resp.text)
            # Keep first 6000 chars — enough to capture all requirements
            return text[:6000]
        except Exception as e:
            sys.exit(f"Could not fetch job URL: {e}")
    
    return ""


def build_prompt(papers: dict[str, str], job_text: str) -> str:
    """Construct the Gemini prompt."""
    paper_sections = ""
    for name, content in papers.items():
        paper_sections += f"\n### Paper: {name}\n{content}\n"

    return textwrap.dedent(f"""
        You are an expert career advisor helping a PhD candidate in optics and 
        machine vision tailor their CV for a specific job opening.

        == JOB DESCRIPTION ==
        {job_text}

        == CANDIDATE'S RESEARCH PAPERS ==
        {paper_sections}

        == STRICTURES (CRITICAL) ==
        - NO DASHES: Never use "-", "–", or "—". Use "to" for ranges.
        - VERTICAL SPINE: Content must be aligned at exactly 103pt from the left.
        - MAX 2 PAGES: Keep bullet points extremely concise (max 140 chars).
        - HARD WRAP: Content must be manually wrapped at ~80 characters.

        == TASK ==
        1. Identify the KEY TECHNICAL REQUIREMENTS (concisely).
        2. For EACH paper, extract specific methods/tools relevant to the job.
        3. Suggest IMPACTFUL LaTeX bullet points for the resume:
           a) Professional Experience: \\\\textbf{{<Project>:}} <Achievement sentence>.
           b) Technical Competencies: \\\\textbf{{<Category>:}} <keyword list>.

        Format your response EXACTLY like this:

        ---
        ## Key Job Requirements
        - <requirement 1>
        ...

        ## Suggested Resume Bullets (Tailored for ZEISS/tooz)

        ### Professional Experience (experience.tex)
        \\\\textbf{{<Label>:}} <concise sentence matching a method to a need>.

        ### Technical Competencies (technical_competencies.tex additions)
        \\\\textbf{{<Category>:}} <updated keyword list>.
        ---
    """)


def print_section(title: str, content: str, width: int = 80):
    """Pretty-print a titled section."""
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print(content)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Match your research papers to a job offer and suggest resume bullets."
    )
    parser.add_argument(
        "--job-url",
        help="URL of the job posting"
    )
    parser.add_argument(
        "--job-file",
        help="Path to a local text file containing the job description"
    )
    parser.add_argument(
        "--papers",
        default="assets/papers",
        help="Path to a directory of PDFs or a single PDF file (default: assets/papers/)"
    )
    args = parser.parse_args()

    # ── Collect PDFs ────────────────────────────────────────────────────────
    paper_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        args.papers if not os.path.isabs(args.papers) else ""
    )
    if os.path.isabs(args.papers):
        paper_dir = args.papers

    if os.path.isfile(paper_dir):
        pdf_paths = [paper_dir]
    elif os.path.isdir(paper_dir):
        pdf_paths = sorted(
            os.path.join(paper_dir, f)
            for f in os.listdir(paper_dir)
            if f.lower().endswith(".pdf")
        )
    else:
        sys.exit(f"Papers path not found: {paper_dir}\n"
                 f"Place your PDFs in assets/papers/ or use --papers <path>")

    if not pdf_paths:
        sys.exit(
            f"No PDFs found in {paper_dir}.\n"
            f"Copy your papers there:\n"
            f"  cp ~/Downloads/your_paper.pdf {paper_dir}/"
        )

    print(f"\n📄 Found {len(pdf_paths)} paper(s):")
    papers: dict[str, str] = {}
    for path in pdf_paths:
        name = os.path.splitext(os.path.basename(path))[0]
        print(f"   • {name}")
        text = extract_pdf_text(path)
        if text:
            papers[name] = text

    if not papers:
        sys.exit("Could not extract text from any PDF. Check your files.")

    # ── Fetch job description ────────────────────────────────────────────────
    if not (args.job_url or args.job_file):
        sys.exit("Error: You must provide either --job-url or --job-file")
    
    source = args.job_url if args.job_url else args.job_file
    print(f"\n🌐 Fetching job description from: {source}")
    job_text = fetch_job_description(url=args.job_url, file_path=args.job_file)
    
    if not job_text:
        sys.exit("Error: Could not retrieve job description content.")
    
    print(f"   ✓ Retrieved {len(job_text)} characters")

    # ── Call Gemini ──────────────────────────────────────────────────────────
    print("\n🤖 Analysing with Gemini AI (this may take ~15 seconds)...")
    prompt = build_prompt(papers, job_text)
    try:
        response = MODEL.generate_content(prompt)
        result = response.text
    except Exception as e:
        sys.exit(f"Gemini API error: {e}")

    # ── Output ───────────────────────────────────────────────────────────────
    print_section("SKILL MATCH ANALYSIS", result)
    print()
    print("✅ Done! Copy the suggested bullets above into your .tex files.")
    print("   • experience.tex          → Professional Experience section")
    print("   • technical_competencies.tex → Technical Competencies section")
    print()


if __name__ == "__main__":
    main()
