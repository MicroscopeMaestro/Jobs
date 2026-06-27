import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.gui.generator import Generator
from src import main as pipeline

def run_ultimate_goal_simulation():
    print("=== [GOAL] ULTIMATE EDGE-CASE AI GENERATION & LATEX SANITIZATION SIMULATION ===")
    print("Verifying automatic protection against LLM hallucinations: unescaped %, #, _, &, mismatched adjustwidth, markdown fences, and illegal macros.\n")

    gen = Generator(project_root=PROJECT_ROOT)
    
    # Simulate an LLM hallucinating all common LaTeX breaking errors across different sections
    mock_llm_sections = {
        "ml_subject": "```latex\nBewerbung als R&D Quality Engineer | C# & Messtechnik #1\n```",
        "ml_recipient": "OptoTech Precision R&D GmbH\nDr. Julia_Wagner\nLaserring 12, 07745 Jena",
        "ml_body": """
Sehr geehrtes Recruiting-Team,

ich bewerbe mich mit 100% Motivation für die R&D Position. Mit Expertise in C# und PySide6_GUI habe ich komplexe Kalibrierungssysteme entwickelt (siehe \\entry{Medical University}{Innsbruck}{Researcher}{2022-2026}). Meine Fehlerquote liegt unter 0.5% bei allen Messungen.

Ich freue mich auf das Vorstellungsgespräch.
        """.strip(),
        "resume_summary": "R&D Optical Engineer mit Fokus auf 100% Qualität und C#_Entwicklung im Bereich Laser_Messtechnik.",
        "resume_experience": """
\\section{Research/Professional Experience}
\\entry{Medical University of Innsbruck}{Innsbruck, Austria}{PhD Researcher | R&D Optics}{Jan 2022 to Jun 2026}
\\begin{adjustwidth}{1103pt}{0pt}
    \\sepbullet Entwickelte R&D Systeme in C# mit 100% Genauigkeit
    \\sepbullet Analysierte Messabweichungen für PySide6_GUI
\\end{adjustwidth}

\\entry{Leibniz Institute IPHT}{Jena, Germany}{R&D Research Assistant}{Jul 2019 to Dec 2021}
\\begin{adjustwidth}{103pt}{0pt}
    \\sepbullet Optimierte C# und C++ Messroutinen (50% schneller)
        """.strip(), # NOTE: intentionally missing \end{adjustwidth} to test environment healing!
        "resume_competencies": """
\\section{Technical Competencies}
\\renewcommand{\\arraystretch}{1.5}
\\begin{tabular}{@{}p{95pt}@{\\hspace{8pt}}p{\\dimexpr\\textwidth-103pt\\relax}@{}}
    \\raggedright\\textbf{R&D / Optik} & \\cvtagExpertise{R&D Messtechnik} \\cvtagExpertise{C# & Python_GUI} \\cvtagKnowledge{100% Precision} \\\\
\\end{tabular}
        """.strip()
    }

    print("[STAGE 1/2] Executing Generator.write_sections() on mock LLM hallucinated outputs...")
    gen.write_sections(mock_llm_sections)
    print(" -> All sections sanitized and saved successfully to templates/sections/")

    # STAGE 2: LaTeX Compiling & Merging
    print("\n[STAGE 2/2] Executing LaTeX compilation and PDF merge pipeline on sanitized files...")
    try:
        pipeline.setup_latex_path()
        attachments = {
            "professional_experience": ["intecol_english.pdf"],
            "education": ["Bachelor Diploma.pdf", "master.pdf"],
            "certificates": ["B2.pdf", "Mündliche_test.pdf"],
            "others": ["resident_permit.pdf", "passport.pdf"]
        }
        comp_app = pipeline.compile_target("full_bundle", attachments)
        if comp_app and os.path.exists(comp_app):
            size_kb = os.path.getsize(comp_app) / 1024.0
            print(f"\n=== [GOAL] SUCCESS! Ultimate Edge-Case Verification Passed Perfectly ===")
            print(f" -> Output File: {comp_app} ({size_kb:.1f} KB)")
        else:
            print("\n -> Compilation completed but output PDF was not found.")
            sys.exit(1)
    except Exception as e:
        print(f"\n -> Pipeline compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_ultimate_goal_simulation()
