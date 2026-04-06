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

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define categories
ATTACHMENTS = {
    "professional_experience": [
        "IPHT0.pdf",
        "IPHT1.pdf"
    ],
    "education": [
        "Bachelor Diploma.pdf",
        "master.pdf"
    ],
    "certificates": [
        "B2.pdf",
        "Mündliche_test.pdf",
        "Zeiss_Summer_School.pdf",
        "ASML_School.pdf",
        "intecol_english.pdf"
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

def compile_latex(tex_filename, output_name):
    """ Compiles a .tex file inside TARGET_DIR to PDF via pdflatex. """
    tex_path = os.path.join(TEMPLATE_DIR, tex_filename)
    if not os.path.exists(tex_path):
        print(f"   ! LaTeX file not found: {tex_path}")
        return None

    print(f"   Compiling LaTeX: {tex_filename} -> {output_name}...")
    
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_path]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, errors='replace')
    
    expected_pdf = os.path.join(OUTPUT_DIR, tex_filename.replace('.tex', '.pdf'))
    final_output = os.path.join(OUTPUT_DIR, output_name)
    
    if os.path.exists(expected_pdf):
        if expected_pdf != final_output:
            shutil.move(expected_pdf, final_output)
    else:
        print(f"   ! CRITICAL ERROR compiling {tex_filename}")
        print("--- pdflatex stdout ---")
        print(process.stdout[:1000] + "\n...")
        return None
        
    # Cleanup intermediate files
    base_name = os.path.splitext(tex_filename)[0]
    extensions = ['.aux', '.log', '.out', '.synctex.gz', '.fdb_latexmk', '.fls']
    for ext in extensions:
        temp_file = os.path.join(OUTPUT_DIR, base_name + ext)
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
            
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
    if cv_pdf: full_docs.append(cv_pdf)
    if resume_pdf: full_docs.append(resume_pdf)
    full_docs.extend(all_attachments)
    
    if full_docs:
        full_app = merge_pdfs(full_docs, "full_application.pdf")
        if full_app:
            # Compress final
            comp_app = os.path.join(OUTPUT_DIR, "Compressed_full_application.pdf")
            compress_pdf(full_app, comp_app, power=3)
            print(f"\\nSUCCESS! Final application ready at: {comp_app}")
            
if __name__ == "__main__":
    build_all()