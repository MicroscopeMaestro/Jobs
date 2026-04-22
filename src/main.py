import os
import shutil
import subprocess
import sys
from PyPDF2 import PdfMerger

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'generated')

# Static configuration for unique naming
USER_NAME = "Juan_David_Munoz_Bolanos"
COMPANY_NAME = "ZEISS_tooz_XR"
POSITION_NAME = "Pioneer_Extended_Reality_XR"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_latex_path():
    """ Adds common macOS TeX distribution paths to the environment PATH. """
    tex_paths = [
        "/Library/TeX/texbin",
        "/usr/local/bin",
        "/usr/local/texlive/2025/bin/universal-darwin",
        "/usr/local/texlive/2024/bin/universal-darwin"
    ]
    current_path = os.environ.get("PATH", "")
    for path in tex_paths:
        if os.path.exists(path) and path not in current_path:
            current_path = f"{path}:{current_path}"
    os.environ["PATH"] = current_path

setup_latex_path()

# Define categories
ATTACHMENTS = {
    "professional_experience": [
        "intecol_english.pdf"
    ],
    "education": [
        "Bachelor Diploma.pdf",
        "master.pdf"
    ],
    "certificates": [
        "B2.pdf",
        "Mündliche_test.pdf"
    ],
    "others": [
        "passport.pdf",
        "resident_permit.pdf"
    ]
}

def compress_pdf(input_path, output_path, power=3):
    """
    Tries Ghostscript first, falls back to PyPDF2 internal compression.
    power 3 = /ebook (150 dpi), power 4 = /screen (72 dpi)
    """
    quality = {1: '/prepress', 2: '/printer', 3: '/ebook', 4: '/screen'}
    gs_settings = quality.get(power, '/ebook')
    
    gs_cmd = 'gs' if sys.platform != 'win32' else 'gswin64c'
    cmd = [
        gs_cmd, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
        f'-dPDFSETTINGS={gs_settings}', '-dNOPAUSE', '-dQUIET', '-dBATCH',
        f'-sOutputFile={output_path}', input_path
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"   Success: Compressed via Ghostscript ({gs_settings})")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ! Ghostscript not found or failed. Falling back to PyPDF2 compression...")
        from PyPDF2 import PdfReader, PdfWriter
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            try:
                page.compress_content_streams()
            except Exception:
                pass
            writer.add_page(page)
        
        with open(output_path, "wb") as f:
            writer.write(f)
        return True

def cleanup_aux_files(tex_filename):
    """ Deletes temporary LaTeX files like .aux, .out, etc., but KEEPS .log for review. """
    base = tex_filename.replace('.tex', '')
    # We explicitly EXCLUDE '.log' from this list to keep it for the user
    exts = ['.aux', '.out', '.toc', '.nav', '.snm', '.vrb', '.fls', '.fdb_latexmk', '.synctex.gz']
    for ext in exts:
        f = os.path.join(OUTPUT_DIR, base + ext)
        if os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

def compile_latex(tex_filename, output_name):
    """ Compiles a .tex file inside TEMPLATE_DIR to PDF via pdflatex. """
    tex_path = os.path.join(TEMPLATE_DIR, tex_filename)
    if not os.path.exists(tex_path):
        print(f"   ! LaTeX file not found: {tex_path}")
        return None

    print(f"   Compiling LaTeX: {tex_filename} -> {output_name}...")
    
    # Delete old output to ensure we don't report a "ghost" success if pdflatex fails
    expected_pdf = os.path.join(OUTPUT_DIR, tex_filename.replace('.tex', '.pdf'))
    if os.path.exists(expected_pdf):
        os.remove(expected_pdf)
    final_output = os.path.join(OUTPUT_DIR, output_name)
    if os.path.exists(final_output) and final_output != expected_pdf:
        os.remove(final_output)

    # Run pdflatex from TEMPLATE_DIR so it can resolve relative \input{sections/...} paths
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_filename]
    
    try:
        process = subprocess.run(cmd, cwd=TEMPLATE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, errors='replace')
    except FileNotFoundError:
        print("   ! CRITICAL ERROR: 'pdflatex' command not found. Please install a TeX distribution (e.g., MikTeX or TeX Live).")
        return None
    
    expected_pdf = os.path.join(OUTPUT_DIR, tex_filename.replace('.tex', '.pdf'))
    final_output = os.path.join(OUTPUT_DIR, output_name)
    
    if os.path.exists(expected_pdf):
        if expected_pdf != final_output:
            if os.path.exists(final_output):
                os.remove(final_output)
            shutil.move(expected_pdf, final_output)
    else:
        print(f"   ! CRITICAL ERROR compiling {tex_filename}")
        log_path = os.path.join(OUTPUT_DIR, tex_filename.replace('.tex', '.log'))
        if os.path.exists(log_path):
            print(f"   Check the log file for details: {log_path}")
            # Optional: print the last 10 lines of the log for immediate feedback
            try:
                with open(log_path, 'r') as log_f:
                    lines = log_f.readlines()
                    print("--- Snippet of LaTeX Error Log ---")
                    for line in lines[-20:]:
                        if '!' in line or 'Error' in line:
                            print(line.strip())
            except:
                pass
        return None
        
    # Cleanup intermediate files
    cleanup_aux_files(tex_filename)
            
    return final_output

def merge_pdfs(pdf_list, output_filename):
    if not pdf_list:
        return None
        
    merger = PdfMerger()
    merged_count = 0
    
    for pdf in pdf_list:
        if os.path.exists(pdf):
            try:
                merger.append(pdf)
                merged_count += 1
            except Exception as e:
                print(f"    ! Failed to merge {pdf}: {e}")
        else:
            print(f"    ! WARNING: Missing file to merge: {pdf}")
            
    if merged_count > 0:
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        merger.write(output_path)
        merger.close()
        print(f"   -> Merged {merged_count} files into {output_filename}")
        return output_path
        
    merger.close()
    return None

def extract_info_from_latex(tex_filename):
    """ Extracts Company and Position from motivation_letter modules or main file. """
    ml_sections_path = os.path.join(TEMPLATE_DIR, 'sections', 'ml')
    recipient_path = os.path.join(ml_sections_path, 'recipient.tex')
    subject_path = os.path.join(ml_sections_path, 'subject.tex')
    
    company = "Unknown_Company"
    position = "Unknown_Position"
    
    import re

    # Try sub-modules first
    content = ""
    if os.path.exists(recipient_path):
        with open(recipient_path, 'r', encoding='utf-8') as f:
            content += f.read()
    if os.path.exists(subject_path):
        with open(subject_path, 'r', encoding='utf-8') as f:
            content += f.read()

    # If sub-modules don't exist or are empty, fall back to main file
    if not content:
        path = os.path.join(TEMPLATE_DIR, tex_filename)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

    if content:
        try:
            # 1. Company Name
            company_match = re.search(r'%\s*Recipient Information.*?\\textbf\{([^}]*)\}', content, re.DOTALL)
            if not company_match:
                # Fallback: look for the first \textbf in recipient if marker missing (less reliable)
                company_match = re.search(r'\\textbf\{([^}]*)\}', content)
            
            if company_match:
                company = company_match.group(1)
            
            # 2. Position
            subject_match = re.search(r'%\s*Subject Line.*?\\textbf\{([^}]*)\}', content, re.DOTALL)
            if subject_match:
                full_subject = subject_match.group(1)
                if 'Bewerbung als ' in full_subject:
                    position = full_subject.split('Bewerbung als ')[1].split('|')[0].strip()
                else:
                    position = full_subject
        except Exception as e:
            print(f"   ! Error parsing LaTeX for naming: {e}")

    # Sanitize for filename
    def sanitize(s):
        import re
        s = s.replace('/', '_').replace('\\', '_').replace(' ', '_')
        return re.sub(r'[^a-zA-Z0-9_]', '', s).strip('_')

    return sanitize(company), sanitize(position)

def build_all():
    print(f"\\n--- Building Application Documents ---\\n")
    
    # 1. Compile LaTeX files (Resume, CV, Motivation Letter if they exist)
    compiled_docs = []
    
    resume_pdf = compile_latex("resume.tex", "resume.pdf")
    if resume_pdf: compiled_docs.append(resume_pdf)
        
    cv_pdf = compile_latex("cv.tex", "cv.pdf")
    if cv_pdf: compiled_docs.append(cv_pdf)
    
    # Add Motivation Letter if present
    ml_pdf = compile_latex("motivation_letter.tex", "motivation_letter.pdf")
    
    # 2. Merge motivation_letter_and_resume.pdf
    ml_and_resume = []
    if ml_pdf: ml_and_resume.append(ml_pdf)
    if resume_pdf: ml_and_resume.append(resume_pdf)
    if ml_and_resume:
        merge_pdfs(ml_and_resume, "motivation_letter_and_resume.pdf")

    # 2b. Merge cv_and_resume.pdf (if cv exists)
    cv_and_resume = []
    if cv_pdf: cv_and_resume.append(cv_pdf)
    if resume_pdf: cv_and_resume.append(resume_pdf)
    if cv_and_resume:
        merge_pdfs(cv_and_resume, "cv_and_resume.pdf")
        
    # 3. Merge Category attachments
    all_attachments = []
    
    for category, filenames in ATTACHMENTS.items():
        cat_files = []
        for f in filenames:
            path = os.path.join(ASSETS_DIR, f)
            if os.path.exists(path):
                cat_files.append(path)
                all_attachments.append(path)
        if cat_files:
            merge_pdfs(cat_files, f"{category}.pdf")
            
    # 4. Merge all_attachments.pdf
    if all_attachments:
        all_attach_pdf = merge_pdfs(all_attachments, "all_attachments.pdf")
    
    # 5. Merge full_application.pdf
    full_docs = []
    if ml_pdf: full_docs.append(ml_pdf)
    if resume_pdf: full_docs.append(resume_pdf)
    full_docs.extend(all_attachments)
    
    # 5b. Create Resume_with_Attachments.pdf
    resume_with_attach = []
    if resume_pdf: resume_with_attach.append(resume_pdf)
    resume_with_attach.extend(all_attachments)
    if resume_with_attach:
        merge_pdfs(resume_with_attach, "Resume_with_Attachments.pdf")
    
    if full_docs:
        # Extract unique name
        company, position = extract_info_from_latex("motivation_letter.tex")
        base_filename = f"Application_{USER_NAME}_{company}_{position}"
        
        full_app = merge_pdfs(full_docs, f"{base_filename}.pdf")
        if full_app:
            # Compress final
            comp_app = os.path.join(OUTPUT_DIR, f"Compressed_{base_filename}.pdf")
            compress_pdf(full_app, comp_app, power=3)
            print(f"\\nSUCCESS! Final application ready at: {comp_app}")
            
if __name__ == "__main__":
    build_all()