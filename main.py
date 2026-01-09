import os
import subprocess
from jinja2 import Environment, FileSystemLoader

# Configuration
TEMPLATE_DIR = 'templates'
ASSETS_DIR = 'assets'
OUTPUT_DIR = 'generated'
LATEX_COMPILER = 'pdflatex' # Ensure you have a TeX distribution installed

def generate_cover_letter(data, template_name="standard_letter.tex"):
    # 1. Setup Jinja2 Environment
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        block_start_string='\BLOCK{', # Change delimiters to avoid conflict with LaTeX syntax
        block_end_string='}',
        variable_start_string='\VAR{',
        variable_end_string='}',
        comment_start_string='\#{',
        comment_end_string='}',
        line_statement_prefix='%%',
        line_comment_prefix='%#',
        trim_blocks=True,
        autoescape=False,
    )
    
    # Note: I changed standard Jinja delimiters ({{ }}) in the config above 
    # because they conflict with LaTeX. 
    # In your .tex file, use \VAR{ variable } instead of {{ variable }}.
    
    template = env.get_template(template_name)

    # 2. Render the LaTeX content
    rendered_tex = template.render(data)

    # 3. Write the .tex file to output
    output_tex_path = os.path.join(OUTPUT_DIR, 'final_letter.tex')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    with open(output_tex_path, "w") as f:
        f.write(rendered_tex)
    
    # 4. Compile to PDF
    # We run it twice to ensure references/layout are correct (standard LaTeX practice)
    subprocess.run([LATEX_COMPILER, '-output-directory', OUTPUT_DIR, output_tex_path], check=True)
    
    print(f"Success! PDF generated at: {os.path.join(OUTPUT_DIR, 'final_letter.pdf')}")

if __name__ == "__main__":
    # Define the dynamic content for this specific application
    letter_data = {
        "my_name": "Jane Doe",
        "my_address": "123 Research Lane, Innsbruck",
        "recipient_name": "Dr. Smith",
        "recipient_company": "University of Science",
        "body_text": "I am writing to apply for the position...",
        
        # Attachments must be absolute paths or relative to where .tex is compiled
        "attachments": [
            os.path.abspath(f"{ASSETS_DIR}/id_card.pdf"),
            os.path.abspath(f"{ASSETS_DIR}/msc_diploma.pdf")
        ]
    }

    generate_cover_letter(letter_data)