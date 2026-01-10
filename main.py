import os
import shutil  # <--- Added for copying files
import subprocess
from jinja2 import Environment, FileSystemLoader
from pypdf import PdfWriter

# --- Configuration ---
TEMPLATE_DIR = 'templates'
ASSETS_DIR = 'assets'
OUTPUT_DIR = 'generated'

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def compile_latex(tex_filename, output_name):
    print(f"Compiling {tex_filename}...")
    tex_path = os.path.join(OUTPUT_DIR, tex_filename)
    
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_path]
    
    # Run pdflatex
    # We capture output as text (universal_newlines=True) to process it easily
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    
    # Check if the PDF was actually created, even if there were errors
    expected_pdf = os.path.join(OUTPUT_DIR, output_name)
    pdf_exists = os.path.isfile(expected_pdf)
    
    if process.returncode != 0:
        # Scan log for specific errors (lines starting with !)
        errors = [line for line in process.stdout.split('\n') if line.startswith('!')]
        
        if errors:
            print(f" ! LaTeX Error found in {tex_filename}:")
            for err in errors[:5]: # Print first 5 errors
                print(f"   {err}")
        else:
            print(f" ! LaTeX returned error code {process.returncode} but no specific '!' error found.")

        if pdf_exists:
            print(f" * WARNING: PDF was generated despite errors. Proceeding...")
        else:
            print(" * CRITICAL: No PDF generated. Aborting.")
            return None
    
    return expected_pdf

def generate_application(data):
    # --- STEP 0: PREPARE ASSETS ---
    # Copy photo.jpg (and other images) from assets/ to generated/
    # so LaTeX can find them during compilation.
    print("Preparing assets...")
    for item in os.listdir(ASSETS_DIR):
        s = os.path.join(ASSETS_DIR, item)
        d = os.path.join(OUTPUT_DIR, item)
        if os.path.isfile(s) and (s.endswith('.jpg') or s.endswith('.png')):
            shutil.copy2(s, d)
            print(f" -> Copied {item} to build folder")

    # --- STEP 1: JINJA SETUP ---
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string=r'\BLOCK{',
        block_end_string='}',
        variable_start_string=r'\VAR{',
        variable_end_string='}',
        comment_start_string=r'\#{',
        comment_end_string='}',
        trim_blocks=True,
        autoescape=False,
    )
    
    # --- STEP 2: COMPILE COVER LETTER ---
    cl_template = env.get_template("cover_letter.tex")
    cl_rendered = cl_template.render(data)
    
    with open(os.path.join(OUTPUT_DIR, 'cover_letter.tex'), "w") as f:
        f.write(cl_rendered)
        
    cl_pdf = compile_latex('cover_letter.tex', 'cover_letter.pdf')

    # --- STEP 3: COMPILE RESUME ---
    # We read the resume template and write it to generated/
    with open(os.path.join(TEMPLATE_DIR, 'resume.tex'), 'r') as f:
        resume_content = f.read()
    
    with open(os.path.join(OUTPUT_DIR, 'resume.tex'), "w") as f:
        f.write(resume_content)
        
    resume_pdf = compile_latex('resume.tex', 'resume.pdf')

    # --- STEP 4: MERGE EVERYTHING ---
    if cl_pdf and resume_pdf:
        merger = PdfWriter()
        
        print("\nMerging Documents:")
        merger.append(cl_pdf)
        print(" + Cover Letter")
        
        merger.append(resume_pdf)
        print(" + Resume")
        
        for filename in data["attachments"]:
            file_path = os.path.join(ASSETS_DIR, filename)
            if os.path.exists(file_path):
                merger.append(file_path)
                print(f" + {filename}")
            else:
                print(f" ! Warning: Attachment '{filename}' not found.")

        final_output = os.path.join(OUTPUT_DIR, 'Full_Application.pdf')
        merger.write(final_output)
        merger.close()
        
        print(f"\nSUCCESS: Application created at: {final_output}")
        # Try to open the file (Mac)
        try:
            subprocess.run(['open', final_output], check=False)
        except:
            pass
    else:
        print("\nABORTED: One or more LaTeX compilations failed.")

if __name__ == "__main__":
    letter_data = {
        "my_name": "Juan Muñoz",
        "my_address": "Innsbruck, Austria",
        "recipient_name": "Dr. Smith",
        "recipient_company": "University of Science",
        "body_text": "I am writing to apply...",
        "attachments": ["id_card.pdf", "msc_diploma.pdf"]
    }

    generate_application(letter_data)