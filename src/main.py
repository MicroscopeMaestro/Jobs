#%%
import os
import shutil
import subprocess
import re
import sys
from jinja2 import Environment, FileSystemLoader

# --- CORRECT IMPORT FOR PyPDF2 3.0+ ---
from PyPDF2 import PdfMerger

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'generated')
DATA_FILE = os.path.join(PROJECT_ROOT, 'data', 'data.json')

os.makedirs(OUTPUT_DIR, exist_ok=True)

def compress_pdf(input_path, output_path, power=3):
    """
    Tries Ghostscript first, falls back to PyPDF2 internal compression.
    power 3 = /ebook (150 dpi), power 4 = /screen (72 dpi)
    """
    quality = {1: '/prepress', 2: '/printer', 3: '/ebook', 4: '/screen'}
    gs_settings = quality.get(power, '/ebook')
    
    # 1. Try Ghostscript (The Heavy Lifter)
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
        
        # 2. Fallback: PyPDF2 Internal (Lossless, less effective but works everywhere)
        from PyPDF2 import PdfReader, PdfWriter
        reader = PdfReader(input_path)
        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams() # This zips the text/vector data
            writer.add_page(page)
        
        with open(output_path, "wb") as f:
            writer.write(f)
        return True
    
def sanitize_filename(text):
    clean = re.sub(r'[^a-zA-Z0-9]', '_', text)
    clean = re.sub(r'_+', '_', clean)
    return clean.strip('_')

def compile_latex(tex_filename, output_name):
    """ Compiles a .tex file inside OUTPUT_DIR to PDF. """
    print(f"   Compiling LaTeX: {tex_filename} -> {output_name}...")
    tex_path = os.path.join(OUTPUT_DIR, tex_filename)
    
    # Run pdflatex once and capture all output
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_path]
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, errors='replace')
    
    expected_pdf = os.path.join(OUTPUT_DIR, output_name)
    
    if process.returncode != 0 or not os.path.isfile(expected_pdf):
        print(f"   ! CRITICAL ERROR compiling {tex_filename}")
        print("--- pdflatex stdout ---")
        print(process.stdout)
        print("--- pdflatex stderr ---")
        print(process.stderr)
        return None
        
    # Cleanup intermediate files
    base_name = os.path.splitext(tex_filename)[0]
    extensions = ['.aux', '.log', '.out', '.synctex.gz', '.fdb_latexmk', '.fls']
    for ext in extensions:
        temp_file = os.path.join(OUTPUT_DIR, base_name + ext)
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
    return expected_pdf

def create_scaled_pdf(filename, scale=0.8):
    """ 
    Wraps a PDF/Image in a LaTeX container to resize and center it. 
    """
    print(f"   -> Scaling {filename} to {scale*100}%...")
    
    base_name = os.path.splitext(filename)[0]
    wrapper_tex_name = f"scaled_{base_name}.tex"
    wrapper_pdf_name = f"scaled_{base_name}.pdf"
    
    wrapper_path = os.path.join(OUTPUT_DIR, wrapper_tex_name)
    
    tex_content = fr"""
\documentclass[a4paper]{{article}}
\usepackage{{graphicx}}
\usepackage[margin=1in]{{geometry}}
\pagestyle{{empty}} 

\begin{{document}}
    \vspace*{{\fill}}
    \begin{{center}}
        \includegraphics[width={scale}\textwidth, keepaspectratio]{{{filename}}}
    \end{{center}}
    \vspace*{{\fill}}
\end{{document}}
    """
    
    with open(wrapper_path, "w", encoding='utf-8') as f:
        f.write(tex_content)
        
    return compile_latex(wrapper_tex_name, wrapper_pdf_name)

def generate_application(data):
    company = data.get('recipient_company', 'Company')
    print(f"\n--- Generating Application for: {company} ---")

    # --- STEP 0: PREPARE ASSETS ---
    # Only copy non-PDF files (e.g., photo.png) that LaTeX templates need.
    # PDFs stay in assets/ and are read from there directly to avoid duplication.
    if os.path.exists(ASSETS_DIR):
        for item in os.listdir(ASSETS_DIR):
            if item.lower().endswith('.pdf'):
                continue  # PDFs are read directly from assets/, never copied
            s = os.path.join(ASSETS_DIR, item)
            d = os.path.join(OUTPUT_DIR, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
    else:
        print(f" ! Warning: '{ASSETS_DIR}' folder missing.")

    # --- STEP 1: COMPILE LETTER ---
    print("1. Generating Motivation Letter...")
    cl_pdf = None
    try:
        env = Environment(
            loader=FileSystemLoader(TEMPLATE_DIR),
            block_start_string='((',
            block_end_string='))',
            variable_start_string='<<',
            variable_end_string='>>',
            comment_start_string='((#',
            comment_end_string='#))'
        )
        cl_rendered = env.get_template("motivation_letter.tex").render(data)
        
        # Added encoding='utf-8' for special characters like 'ñ'
        with open(os.path.join(OUTPUT_DIR, 'motivation_letter.tex'), "w", encoding='utf-8') as f: 
            f.write(cl_rendered)
        
        cl_pdf = compile_latex('motivation_letter.tex', 'motivation_letter.pdf')
    except Exception as e:
        print(f" ! Error rendering motivation letter: {e}")

    # --- STEP 2: COMPILE RESUME ---
    print("2. Generating Resume...")
    resume_pdf = None
    try:
        # Added encoding='utf-8' and dynamic rendering
        resume_rendered = env.get_template("resume.tex").render(data)
        
        with open(os.path.join(OUTPUT_DIR, 'resume.tex'), "w", encoding='utf-8') as f: 
            f.write(resume_rendered)
            
        resume_pdf = compile_latex('resume.tex', 'resume.pdf')
    except Exception as e:
        print(f" ! Error rendering resume: {e}")

    # --- STEP 3: MERGE & ATTACH ---
    if cl_pdf and resume_pdf:
        # FIX: Using PdfMerger class
        merger = PdfMerger()
        
        merger.append(cl_pdf)
        merger.append(resume_pdf)
        
        print("3. Processing Attachments...")
        for attachment in data.get("attachments", []):
            fname = attachment
            scale = 1.0
            
            if isinstance(attachment, dict):
                fname = attachment.get('file')
                scale = attachment.get('scale', 1.0)
            
            # Look in assets/ first, then fall back to generated/ for compiled files
            file_path = os.path.join(ASSETS_DIR, fname)
            if not os.path.exists(file_path):
                file_path = os.path.join(OUTPUT_DIR, fname)
            
            if not os.path.exists(file_path):
                print(f"  ! WARNING: '{fname}' not found. Skipping.")
                continue

            try:
                if scale < 1.0:
                    scaled_pdf_path = create_scaled_pdf(fname, scale)
                    if scaled_pdf_path and os.path.exists(scaled_pdf_path):
                        print(f"  + Appending SCALED {fname}")
                        merger.append(scaled_pdf_path)
                    else:
                        print(f"  ! Scaling failed, appending original.")
                        merger.append(file_path)
                else:
                    print(f"  + Appending {fname}")
                    merger.append(file_path)
                    
            except Exception as e:
                print(f"    ! Failed to append {fname}: {e}")

        # --- OUTPUT ---
        role = sanitize_filename(data.get('job_position', 'Application'))
        name = sanitize_filename(data.get('my_name', 'Applicant'))
        company_clean = sanitize_filename(company)
        
        final_filename = f"Application_{name}_{company_clean}_{role}.pdf"
        final_output_path = os.path.join(OUTPUT_DIR, final_filename)

        merger.write(final_output_path)
        merger.close()
        
        # --- NEW: COMPRESSION STEP ---
        if data.get('compress', False):
            compressed_path = os.path.join(OUTPUT_DIR, f"Compressed_{final_filename}")
            # Use power=3 for a good balance (Ebook quality)
            compress_pdf(final_output_path, compressed_path, power=3)
            print(f"SUCCESS! Compressed version: {compressed_path}")
        else:
            print(f"SUCCESS! Generated: {final_output_path}")

    else:
        print("\nFAILED: Could not compile basic documents.")

if __name__ == "__main__":
    import json
    import yaml
    
    applications = []
    
    data_en = os.path.join(PROJECT_ROOT, 'data', 'data_en.yaml')
    data_de = os.path.join(PROJECT_ROOT, 'data', 'data_de.yaml')
    
    for lang, file_path in [('en', data_en), ('de', data_de)]:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    apps = yaml.safe_load(f) or []
                    for app in apps:
                        app['language'] = lang # explicitly tag the application with its language
                    applications.extend(apps)
                print(f"--- Loaded {len(apps)} {lang} applications from {file_path} ---")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                sys.exit(1)
                
    if not applications:
        print("Error: No applications found in either data_en.yaml or data_de.yaml.")
        sys.exit(1)

    for app in applications:
        generate_application(app)
# %%