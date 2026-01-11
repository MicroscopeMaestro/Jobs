#%%
import os
import shutil
import subprocess
import re  # <--- ADDED: To clean up the filenames
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfWriter

# --- Configuration ---
TEMPLATE_DIR = 'templates'
ASSETS_DIR = 'assets'
OUTPUT_DIR = 'generated'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Helper: Clean Text for Filenames ---
def sanitize_filename(text):
    """
    Removes special characters and spaces to make strings safe for filenames.
    Example: "R&D Engineer @ Zeiss!" -> "R_D_Engineer_Zeiss"
    """
    # Replace non-alphanumeric characters with underscores
    clean = re.sub(r'[^a-zA-Z0-9]', '_', text)
    # Remove multiple underscores in a row (optional, looks nicer)
    clean = re.sub(r'_+', '_', clean)
    return clean.strip('_')

def compile_latex(tex_filename, output_name):
    """ Compiles a .tex file inside OUTPUT_DIR to PDF. """
    print(f"Compiling {tex_filename}...")
    tex_path = os.path.join(OUTPUT_DIR, tex_filename)
    
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_path]
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    expected_pdf = os.path.join(OUTPUT_DIR, output_name)
    
    if process.returncode != 0 and not os.path.isfile(expected_pdf):
        print(f" ! CRITICAL ERROR in {tex_filename}")
        errors = [line for line in process.stdout.split('\n') if line.startswith('!')]
        for err in errors[:5]: print(f"   {err}")
        return None
        
    return expected_pdf

def create_scaled_pdf(filename, scale=0.5):
    """ Wraps a PDF/Image in a LaTeX container to resize and center it. """
    print(f" -> Resizing {filename} to {scale*100}%...")
    
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
    
    wrapper_name = f"scaled_{filename}.tex"
    with open(os.path.join(OUTPUT_DIR, wrapper_name), "w") as f:
        f.write(tex_content)
        
    return compile_latex(wrapper_name, f"scaled_{filename}.pdf")

def generate_application(data):
    # --- STEP 0: PREPARE ASSETS ---
    print("Preparing assets...")
    for item in os.listdir(ASSETS_DIR):
        s = os.path.join(ASSETS_DIR, item)
        d = os.path.join(OUTPUT_DIR, item)
        if os.path.isfile(s):
            shutil.copy2(s, d)

    # --- STEP 1: COMPILE LETTER ---
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), block_start_string=r'\BLOCK{', variable_start_string=r'\VAR{')
    
    cl_rendered = env.get_template("cover_letter.tex").render(data)
    with open(os.path.join(OUTPUT_DIR, 'cover_letter.tex'), "w") as f: f.write(cl_rendered)
    cl_pdf = compile_latex('cover_letter.tex', 'cover_letter.pdf')

    # --- STEP 2: COMPILE RESUME ---
    with open(os.path.join(TEMPLATE_DIR, 'resume.tex'), 'r') as f: resume_content = f.read()
    with open(os.path.join(OUTPUT_DIR, 'resume.tex'), "w") as f: f.write(resume_content)
    resume_pdf = compile_latex('resume.tex', 'resume.pdf')

    # --- STEP 3: MERGE & RENAME ---
    if cl_pdf and resume_pdf:
        merger = PdfWriter()
        merger.append(cl_pdf)
        merger.append(resume_pdf)
        
        print("\nProcessing Attachments...")
        for attachment in data.get("attachments", []):
            if isinstance(attachment, dict):
                fname = attachment['file']
                scale = attachment.get('scale', 1.0)
                if scale < 1.0:
                    scaled_pdf = create_scaled_pdf(fname, scale)
                    if scaled_pdf: merger.append(scaled_pdf)
                else:
                    merger.append(os.path.join(OUTPUT_DIR, fname))
            else:
                merger.append(os.path.join(OUTPUT_DIR, attachment))

        # --- DYNAMIC FILENAME LOGIC ---
        # 1. Get company and role from data
        company = sanitize_filename(data.get('recipient_company', 'Company'))
        role = sanitize_filename(data.get('job_position', 'Application'))
        
        # 2. Build the name: "Application_JuanMunoz_Zeiss_OpticalEngineer.pdf"
        final_filename = f"Application_JuanMunoz_{company}_{role}.pdf"
        final_output_path = os.path.join(OUTPUT_DIR, final_filename)

        merger.write(final_output_path)
        merger.close()
        
        print(f"\n✅ SUCCESS! Created: {final_filename}")
        #try: subprocess.run(['open', final_output_path], check=False)
        #except: pass

if __name__ == "__main__":
    
    # --- YOUR CONTROL SETUP ---
    # You can now loop through multiple applications here
    
    applications = [
        {
            "my_name": "Juan Muñoz",
            "recipient_name": "Dr. Smith",
            "recipient_company": "Zeiss Meditec", # <--- Used for Filename
            "job_position": "R&D Optical Engineer", # <--- Used for Filename
            "body_text": "I am writing to apply for the R&D position...",
            "attachments": ["id_card.pdf"]
        },
        {
            "my_name": "Juan Muñoz",
            "recipient_name": "Hiring Manager",
            "recipient_company": "ASML", # <--- Used for Filename
            "job_position": "Metrology Scientist", # <--- Used for Filename
            "body_text": "I am fascinated by extreme UV lithography...",
            "attachments": [] 
        }
    ]

    for app in applications:
        generate_application(app)
# %%