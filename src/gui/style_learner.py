import os
import json
import glob
import pypdf
import anthropic
from .generator import DEFAULT_MODEL, _normalize_model

class StyleLearner:
    def __init__(self, project_root):
        self.project_root = project_root
        self.generated_dir = os.path.join(project_root, "generated")
        self.data_dir = os.path.join(project_root, "data")
        self.cache_path = os.path.join(self.data_dir, "style_cache.json")
        self.profile_path = os.path.join(self.data_dir, "style_profile.txt")
        
        os.makedirs(self.data_dir, exist_ok=True)
        self.cache = self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading style cache: {e}")
        return {}

    def save_cache(self):
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving style cache: {e}")

    def scan_past_applications(self):
        """Scans the generated directory for past applications and extracts text."""
        # Past full-application bundles are named Juan_Munoz_<company>_<position>.pdf
        # (page 1 = motivation letter). The old "Application_*.pdf" pattern no
        # longer matches anything after the output filenames were renamed.
        pdf_files = glob.glob(os.path.join(self.generated_dir, "Juan_Munoz_*.pdf"))
        
        ingested_count = 0
        updated = False
        
        for pdf_path in pdf_files:
            filename = os.path.basename(pdf_path)
            mtime = os.path.getmtime(pdf_path)
            
            # Check if cache is up-to-date for this file
            if filename in self.cache and self.cache[filename].get("mtime") == mtime:
                ingested_count += 1
                continue
                
            # Otherwise extract text
            try:
                reader = pypdf.PdfReader(pdf_path)
                num_pages = len(reader.pages)
                if num_pages == 0:
                    continue
                
                # Page 1: Motivation Letter
                cover_letter_text = reader.pages[0].extract_text() or ""
                
                # Pages 2-3: Resume (if they exist)
                resume_text = ""
                if num_pages > 1:
                    resume_text += reader.pages[1].extract_text() or ""
                if num_pages > 2:
                    resume_text += "\n" + (reader.pages[2].extract_text() or "")
                
                self.cache[filename] = {
                    "mtime": mtime,
                    "cover_letter": cover_letter_text,
                    "resume": resume_text
                }
                ingested_count += 1
                updated = True
            except Exception as e:
                print(f"Error reading PDF {filename}: {e}")
                
        if updated:
            self.save_cache()
            
        return ingested_count

    def get_style_profile(self):
        """Returns the loaded style profile or a robust default if none exists."""
        if os.path.exists(self.profile_path):
            try:
                with open(self.profile_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                print(f"Error reading style profile: {e}")
                
        # Default fallback profile
        return (
            "Juan's Voice Profile (Default / Humanized):\n"
            "- Tone & Register: Professional, clear, confident, yet highly natural German (B2 level, authentic register for Austrian/German jobs).\n"
            "- Formatting & Phrasing: Active voice, varied sentence lengths, direct statements, no inflated corporate buzzwords or cliché academic filler.\n"
            "- Structural style: Clean opening capturing a solid hook matching the job description; experience-driven paragraphs utilizing concrete metrics; closes with a smooth explanation that the PhD completes in June 2026 and the Austrian residence permit seamlessly transitions to a work permit.\n"
            "- Resume structure: Focused bullet points with strong active verbs starting each item, clear category headers, and consistent technical competencies."
        )

    def relearn_style(self, api_key, model=DEFAULT_MODEL, temperature=0.2):
        """Uses Claude to analyze cover letters in the cache and synthesize a voice profile."""
        if not api_key:
            raise ValueError("Anthropic API key is required to relearn style.")
            
        self.scan_past_applications()
        
        cover_letters = []
        for filename, data in self.cache.items():
            cl_text = data.get("cover_letter", "").strip()
            if cl_text:
                cover_letters.append(f"--- Application file: {filename} ---\n{cl_text}")
                
        if not cover_letters:
            # Nothing to learn from, write the default profile
            with open(self.profile_path, "w", encoding="utf-8") as f:
                f.write(self.get_style_profile())
            return 0
            
        # Select up to 5 diverse or recent letters to keep prompt size reasonable
        sample_letters = cover_letters[:5]
        letters_input = "\n\n".join(sample_letters)
        
        system_prompt = (
            "You are an expert copywriter, linguist, and technical CV advisor. Your task is to analyze "
            "a selection of past job application cover letters written by Juan David Muñoz Bolaños and extract "
            "a highly precise style, voice, and formatting profile. This profile will be used to guide the model "
            "in generating brand new cover letters that sound identical to Juan's natural voice."
        )
        
        analysis_prompt = f"""
Here is a collection of Cover Letters previously sent or edited by Juan (written in German/ngerman):

{letters_input}

Please analyze these letters and build a comprehensive **Style Profile** detailing:
1. **German Register & Local Adaptations**: Describe how German (or Austrian ngerman) is structured. Note standard salutations, closing formats, and specific local phrasings (e.g. references to the Rot-Weiß-Rot-Plus-Karte, Innsbruck residency, PhD timeline).
2. **Tone, Voice, and Rhythm**: Identify the balance of formal vs. technical, sentence length variations, active voice patterns, and the absence of generic corporate buzzwords.
3. **Openings and Closings**: Analyze exactly how he opens the letters (hooks) and how he formats the closing transitions.
4. **Key Phrasings & Framing**: Identify recurring phrasing or stylistic choices (e.g. how he frames optomechatronic builds, C++/LabVIEW/Python coding integration, and vendor coordination).

Provide a highly concise, bulleted description of his writing style. Focus on patterns that can be easily fed back into an LLM system prompt.
"""

        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=_normalize_model(model),
                max_tokens=4000,
                system=system_prompt,
                messages=[{"role": "user", "content": analysis_prompt}],
            )
            profile_text = "".join(
                b.text for b in response.content if b.type == "text"
            ).strip()

            with open(self.profile_path, "w", encoding="utf-8") as f:
                f.write(profile_text)

            return len(cover_letters)
        except Exception as e:
            print(f"Error during Claude style synthesis: {e}")
            # Ensure we write a default profile if the synthesis fails
            if not os.path.exists(self.profile_path):
                with open(self.profile_path, "w", encoding="utf-8") as f:
                    f.write(self.get_style_profile())
            raise e
