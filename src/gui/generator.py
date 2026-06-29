import os
import re
import json
import textwrap
import anthropic

# Default Claude model. Opus 4.8 is the most capable; billing is metered
# automatically per token by the Anthropic account tied to the API key.
DEFAULT_MODEL = "claude-opus-4-8"

PROVIDER_GEMINI = "gemini"
PROVIDER_KIMI = "kimi"
PROVIDER_CLAUDE = "claude"
PROVIDER_OLLAMA = "ollama"


def _normalize_model(model):
    """Guard against stale Gemini model ids lingering in saved settings."""
    if not model or not str(model).startswith("claude"):
        return DEFAULT_MODEL
    return model


def _strip_code_fences(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|latex)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


class Generator:
    def __init__(self, project_root):
        self.project_root = project_root
        self.templates_dir = os.path.join(project_root, "templates")
        self.sections_dir = os.path.join(self.templates_dir, "sections")

    def _get_settings(self):
        personal_settings = os.path.join(self.project_root, "personal", "data", "gui_settings.json")
        settings_path = personal_settings if os.path.exists(personal_settings) else os.path.join(self.project_root, "data", "gui_settings.json")
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_provider(self):
        return self._get_settings().get("ai_provider", "gemini")

    def _complete(self, api_key, system, user_content, max_tokens=16000, model=DEFAULT_MODEL):
        provider = self._get_provider()
        
        if provider == "claude":
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise ValueError("Anthropic API key is missing.")
            
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=_normalize_model(model),
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            return "".join(b.text for b in response.content if b.type == "text").strip()
            
        import requests
        import time
        
        if provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            url_api_key = os.environ.get("GEMINI_API_KEY", "")
            provider_name = "Gemini"
            target_model = "gemini-2.0-flash"
            max_tokens = min(max_tokens, 8192)
            timeout = 120
        elif provider == "kimi":
            url_api_key = os.environ.get("KIMI_API_KEY", "")
            if url_api_key.startswith("nvapi-"):
                base_url = "https://integrate.api.nvidia.com/v1/chat/completions"
                target_model = "meta/llama-3.1-70b-instruct"
                provider_name = "NVIDIA Kimi"
                max_tokens = min(max_tokens, 4096)
                timeout = 240
            else:
                base_url = "https://api.moonshot.cn/v1/chat/completions"
                target_model = "moonshot-v1-128k"
                provider_name = "Kimi"
                timeout = 120
        elif provider == "ollama":
            base_url = "http://localhost:11434/v1/chat/completions"
            url_api_key = "ollama"
            provider_name = "Ollama"
            settings = self._get_settings()
            target_model = settings.get("ollama_model", "qwen2.5:7b")
            timeout = 300
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
            
        if not url_api_key:
            raise ValueError(f"{provider_name} API key not set. Add it in Tools -> Settings.")
            
        MAX_RETRIES = 5
        BACKOFF_FACTOR = 2
        for attempt in range(MAX_RETRIES):
            json_data = {
                "model": target_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            }
            if provider_name == "Ollama":
                json_data["options"] = {"num_ctx": 16384}
                
            try:
                resp = requests.post(
                    base_url,
                    headers={"Authorization": f"Bearer {url_api_key}", "Content-Type": "application/json"},
                    json=json_data,
                    timeout=timeout,
                )
            except requests.exceptions.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    sleep_time = BACKOFF_FACTOR ** attempt
                    print(f"Request error/timeout for {provider_name} ({e}). Retrying in {sleep_time}s...")
                    if provider_name == "NVIDIA Kimi":
                        target_model = "meta/llama-3.1-8b-instruct"
                    time.sleep(sleep_time)
                    continue
                else:
                    raise RuntimeError(f"{provider_name} API request failed after {MAX_RETRIES} attempts: {e}")
                    
            if resp.status_code == 429:
                if attempt < MAX_RETRIES - 1:
                    sleep_time = BACKOFF_FACTOR ** attempt
                    print(f"Rate limited (429) for {provider_name}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue
                else:
                    raise RuntimeError(
                        f"{provider_name} API rate limit exceeded (429).\n\n"
                        "If you are using a shared API key, please generate a free personal key "
                        "at https://aistudio.google.com/apikey and update it in settings."
                    )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    def extract_recipient_details(self, api_key, job_text, model=DEFAULT_MODEL):
        """Calls Claude/Gemini/Kimi/Ollama to extract recipient information from a job posting."""
        provider = self._get_provider()
        if provider == "claude" and not api_key:
            raise ValueError("Anthropic API key is missing.")

        prompt = f"""
You are an expert career assistant. Analyze the following job description and extract the recipient details.

== JOB DESCRIPTION ==
{job_text}

== TASK ==
Extract the following information:
1. Company Name (legal or trading name of the company hiring)
2. Contact Person / Hiring Manager (specific name like "Dr. Anna Schmid" or department like "Recruiting Team" if no name is present)
3. Address (street, postal code, and city of the office or headquarters, if mentioned. If not, just the city/state)
4. Job Title (the specific title of the position being advertised)

You MUST respond with a single, valid JSON object only. Do not wrap the JSON in markdown code blocks.
The JSON must have exactly these keys:
- "company": string
- "contact_person": string
- "address": string
- "job_title": string
"""

        try:
            response_text = self._complete(
                api_key,
                system="You are a precise data extraction assistant. You only output valid raw JSON.",
                user_content=prompt,
                max_tokens=1024,
                model=model,
            )
            return json.loads(_strip_code_fences(response_text))
        except Exception as e:
            print(f"Error extracting recipient details: {e}")
            # Return empty/default dict
            return {
                "company": "",
                "contact_person": "Recruiting Team",
                "address": "",
                "job_title": ""
            }

    def generate_application(self, api_key, params, style_profile, career_context, papers_dict,
                             model=DEFAULT_MODEL, temperature=0.2):
        """Assembles context and prompts AI to generate tailored LaTeX sections."""
        provider = self._get_provider()
        if provider == "claude" and not api_key:
            raise ValueError("Anthropic API key is missing.")

        # Build papers section
        paper_sections = ""
        for name, text in papers_dict.items():
            paper_sections += f"\n### Research Paper: {name}\n{text[:3000]}\n"

        import re
        candidate_name = "John Doe"
        if career_context:
            name_match = re.search(r"\*\*Name:\*\*\s*(.+)", career_context)
            if name_match:
                candidate_name = name_match.group(1).strip()
            else:
                helping_match = re.search(r"helping\s+\*\*([^*]+)\*\*", career_context)
                if helping_match:
                    candidate_name = helping_match.group(1).strip()

        first_name = candidate_name.split()[0] if candidate_name else "John"

        # Format selected examples
        examples_str = ""
        if params.get("examples"):
            examples_str = "Selected Professional Examples to feature:\n"
            for ex in params["examples"]:
                examples_str += f"- {ex}\n"

        # Format selected skills
        skills_str = ""
        if params.get("skills"):
            skills_str = "Selected Skills to highlight:\n"
            for sk in params["skills"]:
                if isinstance(sk, dict):
                    skills_str += f"- {sk['name']} (Level: {sk['level']})\n"
                else:
                    skills_str += f"- {sk} (Level: Knowledge)\n"

        # Format selected experience roles
        experience_str = "Selected Career Roles and Titles to include:\n"
        for role in params.get("experience", []):
            if role.get("enabled", True):
                experience_str += f"- Role: {role['name']}. Custom Job Title: {role['title']}\n"

        lang = params.get("language", "de")
        lang_instruction = "German" if lang == "de" else "English"
        if lang == "auto":
            lang_instruction = "the language of the job description (default to German if unsure)"

        salary_line = params.get("salary", "")
        salary_instruction = ""
        if salary_line and salary_line.lower() != "omit":
            salary_instruction = f"- SALARY EXPECTATION: Weave the salary requirement '{salary_line}' naturally into the cover letter's closing paragraph."
        else:
            salary_instruction = "- SALARY EXPECTATION: Omit any mention of salary."

        # Compile strict system prompt
        is_humanize_enabled = params.get("humanize", True)
        if params.get("skills"):
            for sk in params["skills"]:
                sk_name = sk["name"] if isinstance(sk, dict) else sk
                if "humanize" in sk_name.lower() or "writing voice" in sk_name.lower():
                    is_humanize_enabled = True
                    break

        humanize_guideline = ""
        if is_humanize_enabled:
            humanize_guideline = textwrap.dedent("""
                - HUMANIZE WRITING STYLE (CRITICAL):
                  * Write in a highly natural, authentic, human voice.
                  * Avoid typical AI buzzwords and clichés (e.g., "delve", "testament", "passionate", "pioneered", "cutting-edge", "revolutionary", "meticulously", "harnessing", "moreover", "furthermore", "beacon", "in conclusion").
                  * Use varied sentence lengths (e.g., mix short, punchy sentences with occasional longer, descriptive ones).
                  * Use active voice and natural transitions.
                  * Make the motivation letter sound like a confident, senior physicist/engineer describing their real accomplishments, NOT an AI chatbot generating generic corporate copy.
            """).strip()

        system_instructions = textwrap.dedent(f"""
            You are an expert technical career advisor and LaTeX document generator helping
            {candidate_name} tailor their application for a specific job opening.
            CRITICAL TONE REQUIREMENT: You MUST frame the candidate as a highly-capable, eager JUNIOR ENGINEER.
            While they may have a strong educational or research background, they are applying for entry-level/junior positions.
            Adjust the tone to be humble, adaptable, and eager to learn from senior team members.
            Avoid sounding overqualified, overly senior, or like a manager. Focus on their strong technical foundation and readiness to execute.

            == CANDIDATE'S CAREER & EXAMPLES BANK ==
            {career_context}

            == CANDIDATE'S RESEARCH PAPERS ==
            {paper_sections}

            == CANDIDATE'S STYLE PROFILE (WRITING VOICE) ==
            {style_profile}

            == STRICTURES (CRITICAL) ==
            - STRICT LANGUAGE PROTOCOL: The ENTIRE standard resume document structure (Summary, Experience, Competencies, Education, Publications, Soft Skills, Languages, References) MUST ALWAYS be written in English. All Motivation Letter sections (<ML_SUBJECT>, <ML_RECIPIENT>, <ML_BODY>, <ML_CLOSING>) MUST be written in the specified target language ({lang_instruction}).
            - NO DASHES: Never use "-", "–", or "—" in the text or dates. Use "to" for date ranges (e.g., "2022 to 2026").
            - NO ARROWS: Never use "→", "\\rightarrow", or "->" in content text.
            - VERTICAL SPINE: Resume content must be aligned at exactly 103pt from the left using `\\begin{{adjustwidth}}{{103pt}}{{0pt}}`.
            - BE CONCRETE: Base every skill on specific projects, papers, or the examples bank. NO HALLUCINATION. DO NOT use random filler words.
            - HARD WRAP: Content in the source must be manually wrapped at ~80 characters.
            - LATEX SAFE: Escape special LaTeX characters appropriately (e.g., \\&, \\%, \\_).
            - SALARY PROTOCOL: {salary_instruction}
            {f"- {humanize_guideline}" if humanize_guideline else ""}
        """)

        # User request prompt
        user_prompt = textwrap.dedent(f"""
            Please generate a custom, tailored application based on this job posting:

            == JOB DESCRIPTION ==
            {params.get('job_description', '')}

            == SPECIFIED TARGET PARAMETERS ==
            - Professional Target Title: {params.get('title', 'Optical Systems Engineer')}
            - Focus Themes: {', '.join(params.get('focus', []))}
            {examples_str}
            {skills_str}
            {experience_str}
            - LANGUAGE PROTOCOL (CRITICAL):
              * THE ENTIRE STANDARD RESUME DOCUMENT STRUCTURE (Summary, Experience, Competencies, Education, Publications, Soft Skills, Languages, References) MUST ALWAYS BE IN ENGLISH ONLY! Do not translate any part of the resume into German or any other language.
              * ALL MOTIVATION LETTER SECTIONS (<ML_SUBJECT>, <ML_RECIPIENT>, <ML_BODY>, <ML_CLOSING>) MUST BE IN THE TARGET LANGUAGE: {lang_instruction}.
            - Target Recipient Info:
              * Company Name: {params.get('recipient_company', '')}
              * Contact Person: {params.get('recipient_contact', '')}
              * Address: {params.get('recipient_address', '')}

            == TASK ==
            Generate tailored LaTeX code for the following 6 distinct sections.
            Your entire response MUST be formatted using the XML-like tags exactly as shown below, with the exact LaTeX content inside.
            DO NOT output any markdown blocks or commentary outside the tags.

            1. <ML_SUBJECT>: Subject line of the motivation letter.
               Format: \\textbf{{Bewerbung als [Position] | Ref. [Ref_Number]}} (Translate "Bewerbung als" to English if ML is in English). Do NOT use en-dashes or hyphens for dates, but a vertical bar | is fine.

            2. <ML_RECIPIENT>: Recipient address block.
               Format:
               \\textbf{{[Company Name]}}\\\\
               [Department / Hiring Manager name]\\\\
               [Address / City]

            3. <ML_BODY>: The body paragraphs of the motivation letter.
               Include standard greeting (e.g. "Sehr geehrte Frau [Name]" or "Sehr geehrtes Recruiting-Team"), 3-4 body paragraphs tailoring the candidate's career story to the JD requirements and selected examples.
               Make sure the closing mentions any graduation/availability details and work permit details if they are relevant and specified in the candidate's career context (e.g. PhD timeline or residency status).
               CRITICAL RULES FOR ML_BODY:
               - Do NOT include any closing salutation (e.g., "Mit freundlichen Grüßen", "Sincerely", or the candidate's name) at the end, as this is already dynamically appended by the template.
               - NEVER use \\entry, \\cvtag, or any custom resume LaTeX macros in the motivation letter (<ML_BODY>). Use plain text to reference experience or roles.

            4. <RESUME_SUMMARY>: The summary paragraph at the top of the resume.
               CRITICAL RULE: THIS SECTION MUST BE 100% IN ENGLISH ONLY!!! NO GERMAN OR OTHER LANGUAGES ALLOWED!
               You MUST start this section exactly with: `\\section{{Summary}}`.
               Write a 3-4 sentence paragraph in ENGLISH ONLY that bridges his general photonics expertise with the specific domain of the job.

            5. <RESUME_EXPERIENCE>: The professional/research experience section for the resume.
               CRITICAL RULE: THIS SECTION MUST BE 100% IN ENGLISH ONLY!!! Translate any German job titles, institution names, descriptions, or bullet points into English! NO GERMAN ALLOWED!
               You MUST start this section exactly with: `\\section{{Research/Professional Experience}}`
               Generate `\\entry{{Institution}}{{Location}}{{Title}}{{Date}}` blocks for the selected experience entries, each followed by `\\begin{{adjustwidth}}{{103pt}}{{0pt}}` and bullet points.
               Make sure all dates use the short version of the month and the year, separated by "to" (e.g., "Jan 2022 to Jun 2026").
               CRITICAL FORMATTING RULE: Each bullet point MUST start exactly with `\\sepbullet ` followed directly by the concrete accomplishment text in ENGLISH ONLY. DO NOT use bold prefixes or subheadings in the bullet points, to perfectly maintain the clean, elegant structure of the candidate's archived master resume.
               IMPORTANT: Always escape ampersands in job titles or descriptions as `\\&` (e.g., `R\\&D`). Never write unescaped `&`.

            6. <RESUME_COMPETENCIES>: Technical competencies section.
               CRITICAL RULE: THIS SECTION MUST BE 100% IN ENGLISH ONLY!!! All category names (e.g., use "Quality Management", NOT "Qualitätsmanagement") and skill names MUST be in English! NO GERMAN ALLOWED!
               List skills grouped by category, highlighting the selected skills that match this job posting.
               Use `\\cvtagExpertise{{}}` for skills marked as 'Expertise' in the selected skills list, and `\\cvtagKnowledge{{}}` for skills marked as 'Knowledge'.
               You MUST use a beautiful, modern, tabular grid format to structure and align the categories perfectly.
               Format exactly as follows:
               \\section{{Technical Competencies}}
               \\renewcommand{{\\arraystretch}}{{1.5}}
               \\begin{{tabular}}{{@{{}}p{{95pt}}@{{\\hspace{{8pt}}}}p{{\\dimexpr\\textwidth-103pt\\relax}}@{{}}}}
                   \\raggedright\\textbf{{[Category 1 in English]}} & \\cvtagExpertise{{[Skill 1]}} \\cvtagKnowledge{{[Skill 2]}} \\cvtagExpertise{{[Skill 3]}} \\\\
                   \\raggedright\\textbf{{[Category 2 in English]}} & \\cvtagKnowledge{{[Skill 4]}} \\cvtagKnowledge{{[Skill 5]}} \\cvtagExpertise{{[Skill 6]}} \\\\
                   \\raggedright\\textbf{{[Category 3 in English]}} & \\cvtagExpertise{{[Skill 7]}} \\cvtagKnowledge{{[Skill 8]}} \\cvtagKnowledge{{[Skill 9]}} \\\\
               \\end{{tabular}}

            Let's begin. Generate the 6 sections enclosed in their tags.
        """)

        try:
            result = self._complete(
                api_key,
                system=system_instructions,
                user_content=user_prompt,
                max_tokens=16000,
                model=model,
            )
        except Exception as e:
            raise RuntimeError(f"Claude API generation error: {e}")

        # Parse XML tags with intelligent regex fallback recovery
        def extract_tag(text, tag):
            pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL | re.IGNORECASE)
            match = pattern.search(text)
            val = match.group(1).strip() if match else ""
            if not val:
                # Fallback heuristics if AI omitted XML tags
                if tag == "RESUME_SUMMARY":
                    m = re.search(r"\\section\{Summary\}(.*?)(?=\\section|\Z)", text, re.DOTALL | re.IGNORECASE)
                    if m: val = "\\section{Summary}\n" + m.group(1).strip()
                elif tag == "RESUME_EXPERIENCE":
                    m = re.search(r"\\section\{Research/Professional Experience\}(.*?)(?=\\section|\Z)", text, re.DOTALL | re.IGNORECASE)
                    if m: val = "\\section{Research/Professional Experience}\n" + m.group(1).strip()
                elif tag == "RESUME_COMPETENCIES":
                    m = re.search(r"\\section\{Technical Competencies\}(.*?)(?=\\section|\Z)", text, re.DOTALL | re.IGNORECASE)
                    if m: val = "\\section{Technical Competencies}\n" + m.group(1).strip()
                elif tag == "ML_SUBJECT":
                    m = re.search(r"\\textbf\{[^}]*\|[^}]*\}", text)
                    if m: val = m.group(0).strip()
                elif tag == "ML_BODY":
                    m = re.search(r"(Sehr geehrte[^\n]*|Dear[^\n]*)(.*?)(?=\\section|\Z)", text, re.DOTALL)
                    if m: val = m.group(1) + m.group(2).strip()
            if val.startswith("```"):
                lines = val.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip().startswith("```"):
                    lines = lines[:-1]
                val = "\n".join(lines).strip()
            return val

        ml_subject = extract_tag(result, "ML_SUBJECT")
        ml_recipient = extract_tag(result, "ML_RECIPIENT")
        ml_body = extract_tag(result, "ML_BODY")
        resume_sum = extract_tag(result, "RESUME_SUMMARY")
        resume_exp = extract_tag(result, "RESUME_EXPERIENCE")
        resume_comp = extract_tag(result, "RESUME_COMPETENCIES")

        return {
            "ml_subject": ml_subject,
            "ml_recipient": ml_recipient,
            "ml_body": ml_body,
            "resume_summary": resume_sum,
            "resume_experience": resume_exp,
            "resume_competencies": resume_comp
        }

    def write_sections(self, sections):
        """Writes the generated sections directly into the templates directory (or personal/ templates)."""
        mapping = {
            "ml_subject": "ml/subject.tex",
            "ml_recipient": "ml/recipient.tex",
            "ml_body": "ml/body.tex",
            "resume_summary": "resume/summary.tex",
            "resume_experience": "resume/experience.tex",
            "resume_competencies": "resume/technical_competencies.tex"
        }

        personal_dir = os.path.join(self.project_root, "personal")
        use_personal = os.path.exists(personal_dir)

        for key, rel_path in mapping.items():
            content = sections.get(key, "").strip()
            if content:
                content = re.sub(r'(?<!\\)%', r'\%', content)
                content = re.sub(r'(?<!\\)#', r'\#', content)
                content = re.sub(r'(?<!\\)_', r'\_', content)
                content = re.sub(r'(?<!\\)\$', r'\$', content)
                
                if key != "resume_competencies":
                    content = re.sub(r'(?<!\\)&', r'\&', content)
                else:
                    def clean_macro(m):
                        macro = m.group(1)
                        inner = m.group(2)
                        inner = re.sub(r'(?<!\\)&', r'\&', inner)
                        inner = re.sub(r'(?<!\\)%', r'\%', inner)
                        inner = re.sub(r'(?<!\\)#', r'\#', inner)
                        inner = re.sub(r'(?<!\\)_', r'\_', inner)
                        inner = re.sub(r'(?<!\\)\$', r'\$', inner)
                        return f"{macro}{{{inner}}}"
                    content = re.sub(r'(\\cvtag[A-Za-z]*|\\textbf)\{([^}]+)\}', clean_macro, content)

                content = content.replace("{1103pt}", "{103pt}")
                
                if key == "resume_experience":
                    opens = content.count(r'\begin{adjustwidth}')
                    closes = content.count(r'\end{adjustwidth}')
                    if opens > closes:
                        content += "\n\\end{adjustwidth}" * (opens - closes)
                        
                if key.startswith("ml_"):
                    content = re.sub(r'\\entry\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}', '', content)
                    content = re.sub(r'\\cvtag[A-Za-z]*\{[^}]*\}', '', content)
                    content = content.replace(r'\sepbullet', '').replace(r'\sepentry', '')

                if use_personal:
                    abs_path = os.path.join(personal_dir, "templates", "sections", rel_path)
                else:
                    abs_path = os.path.join(self.sections_dir, rel_path)
                
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                print(f"Written section to: {abs_path}")

    def edit_section(self, api_key, current_text, user_prompt, model=DEFAULT_MODEL, temperature=0.4):
        """Uses Claude to edit a single section based on user instructions."""
        system_instruction = (
            "You are an expert LaTeX editor. You will be provided with the current LaTeX content "
            "of a specific section of a job application (resume or motivation letter), along with "
            "an instruction from the user on how to modify it.\n\n"
            "CRITICAL RULES:\n"
            "- ONLY output the modified LaTeX code.\n"
            "- DO NOT wrap your response in markdown blocks (e.g. ```latex). Just output the raw text.\n"
            "- DO NOT output any conversational text or explanations.\n"
            "- Keep all formatting, commands, and structures intact unless instructed otherwise."
        )

        prompt = f"== CURRENT CONTENT ==\n{current_text}\n\n== INSTRUCTION ==\n{user_prompt}\n\nPlease provide the updated content."

        try:
            result = self._complete(
                api_key,
                system=system_instruction,
                user_content=prompt,
                max_tokens=8000,
                model=model,
            )
            return _strip_code_fences(result)
        except Exception as e:
            raise RuntimeError(f"Claude API chat error: {e}")

    def extract_job_details(self, api_key, job_description, context_dict, model=DEFAULT_MODEL, temperature=0.1):
        """Uses Claude to extract details and auto-select checkboxes based on the job description."""
        system_instruction = (
            "You are an intelligent Auto-Tuning bot for a job application generator. "
            "Your task is to analyze the provided Job Description and output a strict JSON payload. "
            "You must select the most relevant items from the provided available options to tailor the applicant's resume. "
            "Rules:\n"
            "1. 'company': Extract the Company Name. If unknown, return 'Unknown'.\n"
            "2. 'position': Extract the Position Title. If unknown, return 'Unknown Position'.\n"
            "3. 'foci': Select 1 to 2 exact strings from the available 'foci' list that best match the job.\n"
            "4. 'examples': Select exactly 2 to 3 exact strings from the available 'examples' list that showcase relevant experience.\n"
            "5. 'skills': Select 5 to 10 exact strings from the available 'skills' list that are mentioned or highly relevant.\n"
            "6. 'experience_entries': Select all exact strings from 'experience_entries' that are relevant to keep (usually all of them, unless one is completely irrelevant). "
            "Ensure ALL selected strings exactly match the provided available options.\n\n"
            "AVAILABLE OPTIONS:\n"
            f"{json.dumps(context_dict, indent=2)}\n\n"
            "Return ONLY valid JSON. Do not wrap it in markdown code blocks."
        )

        try:
            result = self._complete(
                api_key,
                system=system_instruction,
                user_content=job_description,
                max_tokens=2000,
                model=model,
            )
            return json.loads(_strip_code_fences(result))
        except Exception as e:
            raise RuntimeError(f"Extraction error: {e}")

    def run_sanity_check(self, api_key, document_text, model=DEFAULT_MODEL):
        """Runs a post-compilation sanity check on the provided document text."""
        system_instruction = (
            "You are a strict Quality Assurance reviewer for a job application. "
            "Review the provided LaTeX resume and motivation letter content. "
            "Look specifically for:\n"
            "1. Any leftover placeholders like [Company Name], [Date], or 'Unknown'.\n"
            "2. Any glaring logical contradictions.\n"
            "3. Extremely awkward phrasing or incomplete sentences.\n\n"
            "If everything is perfect, output exactly: 'All Good'.\n"
            "If you find issues, output a concise bulleted list of the discrepancies found."
        )

        try:
            return self._complete(
                api_key,
                system=system_instruction,
                user_content=document_text,
                max_tokens=2000,
                model=model,
            )
        except Exception as e:
            raise RuntimeError(f"Sanity Check API error: {e}")

# Alias for backward compatibility on Windows launcher scripts/web apps
GeneratorWindows = Generator
