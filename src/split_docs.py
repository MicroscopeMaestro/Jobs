import os
import subprocess

base_dir = "/Users/juanmunoz/Documents/GitHub/Jobs/assets"
output_dir = "/Users/juanmunoz/Documents/GitHub/Jobs/generated"

# Group 1: Experience Documents
exp_docs = ["IPHT1.pdf", "IPHT0.pdf", "intecol_english.pdf"]

# Group 2: Certificates Only
certificate_docs = ["B2.pdf", "Mündliche_test.pdf", "Zeiss_Summer_School.pdf"]

# Group 3: Education Only
education_docs = ["master.pdf", "Bachelor Diploma.pdf"]

# Group 4: Personal Documents (ID & Authorization)
personal_docs = ["passport.pdf", "resident_permit.pdf"]

def merge_pdfs(doc_list, output_name):
    cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", f"-sOutputFile={os.path.join(output_dir, output_name)}"]
    for doc in doc_list:
        cmd.append(os.path.join(base_dir, doc))
    
    print(f"Merging {output_name}...")
    subprocess.run(cmd, check=True)
    print(f"Successfully created {output_name}")

try:
    merge_pdfs(exp_docs, "Experience_Documents.pdf")
    merge_pdfs(certificate_docs, "Certificates_Only.pdf")
    merge_pdfs(education_docs, "Education_Only.pdf")
    merge_pdfs(personal_docs, "Personal_Documents.pdf")
    
    # Final order: Experience -> Diplomas -> Certificates -> Personal
    all_docs = [
        # Professional Experience
        "IPHT1.pdf", "IPHT0.pdf", "intecol_english.pdf",
        # Diplomas
        "master.pdf", "Bachelor Diploma.pdf",
        # Certificates
        "Zeiss_Summer_School.pdf", "B2.pdf", "Mündliche_test.pdf",
        # Personal / Identity
        "passport.pdf", "resident_permit.pdf",
    ]
    merge_pdfs(all_docs, "All_Attachments.pdf")
except Exception as e:
    print(f"Error: {e}")
