import os
import shutil
import subprocess
import sys
import fitz  # PyMuPDF — robust PDF merge engine (pypdf blanked vector resume pages)

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, 'templates')
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'generated')

def get_user_name():
    personal_dir = os.path.join(PROJECT_ROOT, "personal")
    if os.path.exists(personal_dir):
        return "Juan_Munoz"
    return "John_Doe"

def get_asset_path(filename):
    personal_path = os.path.join(PROJECT_ROOT, "personal", "assets", filename)
    if os.path.exists(personal_path):
        return personal_path
    return os.path.join(PROJECT_ROOT, "assets", filename)

# Static configuration for unique naming
USER_NAME = get_user_name()
COMPANY_NAME = "INNIO_Jenbacher"
POSITION_NAME = "Quality_Engineer_Messtechnik"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def setup_latex_path():
    """ Adds common macOS/Windows/Linux TeX distribution paths to the environment PATH. """
    current_path = os.environ.get("PATH", "")
    if sys.platform == 'win32':
        tex_paths = [
            r"C:\Program Files\MiKTeX\miktex\bin\x64",
            r"C:\Program Files\MiKTeX 2.9\miktex\bin\x64",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64"),
            r"C:\texlive\2026\bin\windows",
            r"C:\texlive\2025\bin\windows",
            r"C:\texlive\2024\bin\windows",
        ]
        separator = ";"
    else:
        tex_paths = [
            "/Library/TeX/texbin",
            "/usr/local/bin",
            "/usr/local/texlive/2025/bin/universal-darwin",
            "/usr/local/texlive/2024/bin/universal-darwin"
        ]
        separator = ":"
        
    for path in tex_paths:
        if os.path.exists(path) and path not in current_path:
            current_path = f"{path}{separator}{current_path}"
    os.environ["PATH"] = current_path

setup_latex_path()

# Define categories
ATTACHMENTS = {
    "professional_experience": [
        #"IPHT0.pdf",
        #"IPHT1.pdf",
        "intecol_english.pdf"
    ],
    "education": [
        "Bachelor Diploma.pdf",
        "master.pdf"
    ],
    "certificates": [
        #"ASML_School.pdf",
        #"Zeiss_Summer_School.pdf",
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
    Tries Ghostscript first, falls back to pypdf internal compression.
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
        print("   ! Ghostscript not found or failed. Falling back to pypdf compression...")
        from pypdf import PdfReader, PdfWriter
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

def _latex_error_snippet(tex_filename, max_lines=10):
    """Extract the *root-cause* LaTeX error from the log.

    pdflatex often reports a confusing cascade ("I can't find file X.aux",
    "Emergency stop", "Fatal error ... no output PDF") that hides the real
    problem. Surface the meaningful error (Runaway argument, Undefined control
    sequence, the offending `l.NN` line) and skip the cascade noise.
    """
    log_path = os.path.join(OUTPUT_DIR, tex_filename.replace('.tex', '.log'))
    try:
        with open(log_path, 'r', errors='replace') as f:
            log = [ln.rstrip() for ln in f.readlines()]
    except Exception:
        return "See the .log file in generated/ for details."

    cascade = ("i can't find file", "emergency stop", "fatal error", "==> fatal",
               "\\enddocument", "useonetimehook", "<inserted text>", "\\@@input")

    out = []
    for i, ln in enumerate(log):
        if not ln:
            continue
        low = ln.lower()
        is_runaway = "runaway argument" in low
        is_real_bang = ln.startswith("!") and not any(c in low for c in cascade)
        if is_runaway or is_real_bang:
            out.append(ln)
            for j in range(1, 4):  # following lines carry the offending text / `l.NN`
                if i + j < len(log) and log[i + j]:
                    out.append(log[i + j])
                    if log[i + j].startswith("l."):
                        break
            if len(out) >= max_lines:
                break

    if out:
        return "\n".join(out[:max_lines])

    # Only cascade lines found -> structural problem with no pinpointed line.
    return ("No specific line was reported. This usually means a section has an "
            "unbalanced brace { }, an unclosed \\begin{...}/\\end{...} environment, "
            "or a stray special character (& % # $ _). Check your most recent edit.")


def _pdf_is_valid(path):
    """True if path is a non-trivial, well-formed PDF (starts with %PDF)."""
    try:
        if not os.path.exists(path) or os.path.getsize(path) < 600:
            return False
        with open(path, 'rb') as f:
            return f.read(5).startswith(b'%PDF')
    except OSError:
        return False


def compile_latex(tex_filename, output_name):
    """ Compiles a .tex file inside TEMPLATE_DIR (or build_templates) to PDF via pdflatex. """
    # Setup build directory
    build_templates_dir = os.path.join(OUTPUT_DIR, "build_templates")
    if os.path.exists(build_templates_dir):
        try:
            shutil.rmtree(build_templates_dir)
        except Exception:
            pass
    os.makedirs(build_templates_dir, exist_ok=True)

    # 1. Copy public templates
    if os.path.exists(TEMPLATE_DIR):
        shutil.copytree(TEMPLATE_DIR, build_templates_dir, dirs_exist_ok=True)

    # 2. Overlay personal templates if present
    personal_templates_dir = os.path.join(PROJECT_ROOT, "personal", "templates")
    if os.path.exists(personal_templates_dir):
        shutil.copytree(personal_templates_dir, build_templates_dir, dirs_exist_ok=True)

    tex_path = os.path.join(build_templates_dir, tex_filename)
    if not os.path.exists(tex_path):
        print(f"   ! LaTeX file not found: {tex_path}")
        return None

    print(f"   Compiling LaTeX: {tex_filename} -> {output_name}...")

    base = tex_filename.replace('.tex', '')
    expected_pdf = os.path.join(OUTPUT_DIR, base + '.pdf')
    final_output = os.path.join(OUTPUT_DIR, output_name)
    cmd = ['pdflatex', '-output-directory', OUTPUT_DIR, '-interaction=nonstopmode', tex_filename]
    # With -output-directory, pdflatex writes <job>.aux into OUTPUT_DIR but, at
    # \enddocument, \@@input{<job>.aux} only finds it reliably when TEXMFOUTPUT
    # points there. Without this, the letter class intermittently aborts with
    # "I can't find file <job>.aux" / Emergency stop. This is the root-cause fix.
    run_env = dict(os.environ, TEXMFOUTPUT=OUTPUT_DIR)

    def _preclean():
        # Clean ALL stale intermediates for this job, not just the .pdf. A corrupt
        # .aux left by a previous failed compile makes the next run abort with
        # "I can't find file <job>.aux" / Emergency stop even though the source is
        # fine — start every attempt from a clean slate.
        for ext in ('.pdf', '.aux', '.out', '.toc', '.log', '.nav', '.snm',
                    '.vrb', '.fls', '.fdb_latexmk', '.synctex.gz'):
            stale = os.path.join(OUTPUT_DIR, base + ext)
            if os.path.exists(stale):
                try:
                    os.remove(stale)
                except OSError:
                    pass
        if os.path.exists(final_output) and final_output != expected_pdf:
            os.remove(final_output)

    last_snippet = ""
    # A pure ".aux cascade" failure (no real error line) is a transient state
    # left by a previous Emergency stop and clears on a clean retry; allow a few.
    # A real source error (Runaway, Undefined control sequence, ...) is
    # deterministic and raises on the first attempt.
    MAX_ATTEMPTS = 3
    for attempt in range(1, MAX_ATTEMPTS + 1):
        _preclean()
        process = None
        try:
            # Two passes: write the .aux, then read it back (the letter class
            # inputs \jobname.aux at \enddocument; also resolves references).
            for _ in range(2):
                process = subprocess.run(cmd, cwd=build_templates_dir, env=run_env, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, universal_newlines=True, errors='replace')
                if process.returncode != 0:
                    break
        except FileNotFoundError:
            print("   ! CRITICAL ERROR: 'pdflatex' command not found. Please install a TeX distribution (e.g., MikTeX or TeX Live).")
            return None

        # nonstopmode emits a blank/partial PDF even on error, so "PDF exists" is
        # not a success signal. Require a clean exit code AND a structurally valid
        # PDF — pdflatex can occasionally return 0 yet leave a zero-filled/corrupt
        # file, which would then be silently dropped when merged into the bundle.
        if process.returncode == 0 and _pdf_is_valid(expected_pdf):
            if expected_pdf != final_output:
                if os.path.exists(final_output):
                    os.remove(final_output)
                shutil.move(expected_pdf, final_output)
            cleanup_aux_files(tex_filename)
            return final_output

        last_snippet = _latex_error_snippet(tex_filename)
        if os.path.exists(expected_pdf):
            try:
                os.remove(expected_pdf)  # never keep a blank/partial/corrupt page
            except OSError:
                pass

        # A returncode-0 run that produced no valid PDF, or a pure .aux cascade,
        # is a transient state that clears on a clean retry. A real source error
        # (non-zero exit with a reported error line) is deterministic -> raise.
        transient = (process.returncode == 0) or last_snippet.startswith("No specific line")
        if transient and attempt < MAX_ATTEMPTS:
            print(f"   ! transient compile failure; retrying from a clean slate (attempt {attempt + 1})...")
            continue
        break

    print(f"   ! LaTeX compile error in {tex_filename}:\n{last_snippet}")
    cleanup_aux_files(tex_filename)
    raise RuntimeError(f"LaTeX failed to compile {tex_filename}.\n\n{last_snippet}")

def merge_pdfs(pdf_list, output_filename):
    """Merge PDFs with PyMuPDF (fitz).

    pypdf's PdfWriter.append silently blanked vector pages from the LaTeX resume
    (transparency-group / inherited-resource handling), so the resume showed up
    as a blank page in the bundle. MuPDF is a full PDF engine and reproduces
    every input page faithfully (scanned attachments included).
    """
    if not pdf_list:
        return None

    output_path = os.path.join(OUTPUT_DIR, output_filename)
    existing = [p for p in pdf_list if os.path.exists(p)]
    for p in pdf_list:
        if not os.path.exists(p):
            print(f"    ! WARNING: Missing file to merge: {p}")
    if not existing:
        return None

    out = fitz.open()
    merged = 0
    try:
        for pdf in existing:
            try:
                src = fitz.open(pdf)
                out.insert_pdf(src)
                src.close()
                merged += 1
            except Exception as e:
                print(f"    ! Failed to merge {pdf}: {e}")
        if merged == 0:
            return None
        out.save(output_path, garbage=4, deflate=True)
        print(f"   -> Merged {merged} files into {output_filename}")
        return output_path
    except Exception as e:
        print(f"    ! Could not produce {output_filename}: {e}")
        return None
    finally:
        out.close()

def extract_info_from_latex(tex_filename):
    """ Extracts Company and Position from motivation_letter modules or main file. """
    build_templates_dir = os.path.join(OUTPUT_DIR, "build_templates")
    ml_sections_path = os.path.join(build_templates_dir, 'sections', 'ml')
    if not os.path.exists(ml_sections_path):
        ml_sections_path = os.path.join(TEMPLATE_DIR, 'sections', 'ml')
    recipient_path = os.path.join(ml_sections_path, 'recipient.tex')
    subject_path = os.path.join(ml_sections_path, 'subject.tex')
    
    company = "Unknown_Company"
    position = "Unknown_Position"
    
    import re

    # Try sub-modules first
    if os.path.exists(recipient_path):
        try:
            with open(recipient_path, 'r', encoding='utf-8') as f:
                rec_content = f.read()
            company_match = re.search(r'\\textbf\{([^}]*)\}', rec_content)
            if company_match:
                company = company_match.group(1)
        except Exception:
            pass

    if os.path.exists(subject_path):
        try:
            with open(subject_path, 'r', encoding='utf-8') as f:
                sub_content = f.read()
            subject_match = re.search(r'\\textbf\{([^}]*)\}', sub_content)
            if subject_match:
                full_subject = subject_match.group(1)
                # Try to clean out common prefixes
                if 'Bewerbung als ' in full_subject:
                    position = full_subject.split('Bewerbung als ')[1].split('|')[0].strip()
                elif 'Application for ' in full_subject:
                    position = full_subject.split('Application for ')[1].split('|')[0].strip()
                else:
                    position = full_subject.split('|')[0].strip()
        except Exception:
            pass

    # Sanitize for filename
    def sanitize(s):
        import re
        s = s.replace('/', '_').replace('\\', '_').replace(' ', '_')
        return re.sub(r'[^a-zA-Z0-9_]', '', s).strip('_')

    return sanitize(company), sanitize(position)

def _category_source_files(category):
    """Existing source PDFs for an attachment category (from ATTACHMENTS)."""
    files = []
    for f in ATTACHMENTS.get(category, []):
        p = get_asset_path(f)
        if os.path.exists(p):
            files.append(p)
        else:
            print(f"    ! Missing attachment: {f}")
    return files


def build_category(category):
    """Merge one attachment category into <category>.pdf."""
    files = _category_source_files(category)
    if not files:
        print(f"   ! No files selected for category '{category}'.")
        return None
    return merge_pdfs(files, f"{category}.pdf")


def build_all_attachments():
    """Merge every attachment category into all_attachments.pdf."""
    files = []
    for category in ATTACHMENTS:
        files.extend(_category_source_files(category))
    if not files:
        print("   ! No attachments selected.")
        return None
    return merge_pdfs(files, "all_attachments.pdf")


def build_personal_documents():
    """Merge passport + residence permit into the identification PDF."""
    docs = []
    for name in ("passport.pdf", "resident_permit.pdf"):
        p = get_asset_path(name)
        if os.path.exists(p):
            docs.append(p)
    if not docs:
        print("   ! No personal documents (passport/resident_permit) found.")
        return None
    return merge_pdfs(docs, f"Passport_and_Resident_Permit_{USER_NAME}.pdf")


def compile_target(target, attachments_map=None):
    """Build a single output on demand. Returns the output path, or None.

    LaTeX targets (resume / motivation_letter) raise RuntimeError on a LaTeX
    error so the GUI can surface it. Merge targets continue resiliently.
    """
    if attachments_map is not None:
        global ATTACHMENTS
        ATTACHMENTS = attachments_map

    if target == "resume":
        return compile_latex("resume.tex", "resume.pdf")
    if target == "motivation_letter":
        return compile_latex("motivation_letter.tex", "motivation_letter.pdf")
    if target == "motivation_letter_and_resume":
        ml = compile_latex("motivation_letter.tex", "motivation_letter.pdf")
        rs = compile_latex("resume.tex", "resume.pdf")
        docs = [d for d in (ml, rs) if d]
        return merge_pdfs(docs, "motivation_letter_and_resume.pdf") if docs else None
    if target in ("professional_experience", "education", "certificates", "others"):
        return build_category(target)
    if target == "all_attachments":
        return build_all_attachments()
    if target == "personal_documents":
        return build_personal_documents()
    if target == "full_bundle":
        return build_all()

    print(f"   ! Unknown compile target: {target}")
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
            path = get_asset_path(f)
            if os.path.exists(path):
                cat_files.append(path)
                all_attachments.append(path)
        if cat_files:
            merge_pdfs(cat_files, f"{category}.pdf")
            
    # 4. Merge all_attachments.pdf
    if all_attachments:
        all_attach_pdf = merge_pdfs(all_attachments, "all_attachments.pdf")
    
    # 5. Merge full_application.pdf
    # Defensive: the core documents (motivation letter, resume) MUST be in the
    # bundle. If either file went missing since it was compiled (a transient
    # filesystem/merge race), recompile it now so the bundle is never missing
    # the resume or the cover letter.
    if ml_pdf and not _pdf_is_valid(ml_pdf):
        print("   ! motivation_letter.pdf missing before bundle; recompiling...")
        ml_pdf = compile_latex("motivation_letter.tex", "motivation_letter.pdf")
    if resume_pdf and not _pdf_is_valid(resume_pdf):
        print("   ! resume.pdf missing before bundle; recompiling...")
        resume_pdf = compile_latex("resume.tex", "resume.pdf")

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
    
    # 6. Create separate Identification file (Passport + Resident Permit)
    identification_docs = []
    passport_path = get_asset_path("passport.pdf")
    resident_permit_path = get_asset_path("resident_permit.pdf")
    if os.path.exists(passport_path): identification_docs.append(passport_path)
    if os.path.exists(resident_permit_path): identification_docs.append(resident_permit_path)
    if identification_docs:
        merge_pdfs(identification_docs, f"Passport_and_Resident_Permit_{USER_NAME}.pdf")
    
    if full_docs:
        # Extract unique name
        company, position = extract_info_from_latex("motivation_letter.tex")
        base_filename = f"{USER_NAME}_{company}_{position}"
        
        full_app = merge_pdfs(full_docs, f"{base_filename}.pdf")
        if full_app:
            # Compress final
            comp_app = os.path.join(OUTPUT_DIR, f"Compressed_{base_filename}.pdf")
            compress_pdf(full_app, comp_app, power=3)
            print(f"\\nSUCCESS! Final application ready at: {comp_app}")
            return comp_app
    return None
            
if __name__ == "__main__":
    build_all()