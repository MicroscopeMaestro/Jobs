import os
import re
import json
import textwrap
from google import genai
from google.genai import types as genai_types
from pypdf import PdfReader

class Generator:
    def __init__(self, project_root):
        self.project_root = project_root
        self.templates_dir = os.path.join(project_root, "templates")
        self.sections_dir = os.path.join(self.templates_dir, "sections")

    def extract_recipient_details(self, api_key, job_text, model="gemini-3.5-flash"):
        """Calls Gemini to extract recipient information from a job posting."""
        if not api_key:
            raise ValueError("Gemini API key is missing.")

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
            client = genai.Client(api_key=api_key)
            
            # Use 0.0 temperature for high precision
            config = genai_types.GenerateContentConfig(
                system_instruction="You are a precise data extraction assistant. You only output valid raw JSON.",
                temperature=0.0
            )
            
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            response_text = response.text.strip()
            
            # Clean markdown code blocks if the model returned them
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\n", "", response_text)
                response_text = re.sub(r"\n```$", "", response_text)
                response_text = response_text.strip()
                
            return json.loads(response_text)
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
                             model="gemini-3.5-flash", temperature=0.2):
        """Assembles context and prompts Gemini to generate tailored LaTeX sections."""
        if not api_key:
            raise ValueError("Gemini API key is missing.")

        # Build papers section
        paper_sections = ""
        for name, text in papers_dict.items():
            paper_sections += f"\n### Research Paper: {name}\n{text[:3000]}\n"

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
                skills_str += f"- {sk}\n"

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
                if "humanize" in sk.lower() or "writing voice" in sk.lower():
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
            Juan David Muñoz Bolaños tailor his application for a specific job opening.

            == CANDIDATE'S CAREER & EXAMPLES BANK ==
            {career_context}

            == CANDIDATE'S RESEARCH PAPERS ==
            {paper_sections}

            == CANDIDATE'S STYLE PROFILE (WRITING VOICE) ==
            {style_profile}

            == STRICTURES (CRITICAL) ==
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
            - Language for Motivation Letter: {lang_instruction}
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
               Include standard greeting (e.g. "Sehr geehrte Frau [Name]" or "Sehr geehrtes Recruiting-Team"), 3-4 body paragraphs tailoring Juan's career story to the JD requirements and selected examples.
               Make sure the closing mentions Juan finishing his PhD in June 2026, and that his Austrian Residence Permit converts seamlessly to a working permit.
               Do NOT include any closing salutation (e.g., "Mit freundlichen Grüßen" or Juan's name) at the end, as this is already dynamically appended by the template.

            4. <RESUME_SUMMARY>: The summary paragraph at the top of the resume.
               You MUST start this section exactly with: `\\section{{Summary}}`.
               Write a 3-4 sentence paragraph that bridges his general photonics expertise with the specific domain of the job.

            5. <RESUME_EXPERIENCE>: The professional/research experience section for the resume.
               You MUST start this section exactly with: `\\section{{Research/Professional Experience}}`
               Generate `\\entry{{Institution}}{{Location}}{{Title}}{{Date}}` blocks for the selected experience entries, each followed by `\\begin{{adjustwidth}}{{103pt}}{{0pt}}` and bullet points with `\\sepbullet` or `\\sepentry` separators, aligned to 103pt. Use the custom job titles specified by the user!
               Make sure all dates use the short version of the month and the year, separated by "to" (e.g., "Jan 2022 to Jun 2026").
               Ensure bullet points are concrete, highly relevant to the JD, and structured with bold prefixes.

            6. <RESUME_COMPETENCIES>: Technical competencies section.
               List skills grouped by category, highlighting the selected skills that match this job posting.
               You MUST use a beautiful, modern, tabular grid format to structure and align the categories perfectly.
               Format exactly as follows:
               \\section{{Technical Competencies}}
               \\renewcommand{{\\arraystretch}}{{1.5}}
               \\begin{{tabular}}{{@{{}}p{{95pt}}@{{\\hspace{{8pt}}}}p{{\\dimexpr\\textwidth-103pt\\relax}}@{{}}}}
                   \\raggedright\\textbf{{[Category 1]}} & \\cvtag{{[Skill 1]}} \\cvtag{{[Skill 2]}} \\cvtag{{[Skill 3]}} \\\\
                   \\raggedright\\textbf{{[Category 2]}} & \\cvtag{{[Skill 4]}} \\cvtag{{[Skill 5]}} \\cvtag{{[Skill 6]}} \\\\
                   \\raggedright\\textbf{{[Category 3]}} & \\cvtag{{[Skill 7]}} \\cvtag{{[Skill 8]}} \\cvtag{{[Skill 9]}} \\\\
               \\end{{tabular}}
               
            Let's begin. Generate the 6 sections enclosed in their tags.
        """)

        try:
            client = genai.Client(api_key=api_key)
            
            config = genai_types.GenerateContentConfig(
                system_instruction=system_instructions,
                temperature=temperature
            )
            
            response = client.models.generate_content(model=model, contents=user_prompt, config=config)
            result = response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API generation error: {e}")
        
        # Parse XML tags
        def extract_tag(text, tag):
            pattern = re.compile(rf"<{tag}>(.*?)</{tag}>", re.DOTALL)
            match = pattern.search(text)
            return match.group(1).strip() if match else ""

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
        """Writes the generated sections directly into the templates directory."""
        os.makedirs(os.path.join(self.sections_dir, "ml"), exist_ok=True)
        os.makedirs(os.path.join(self.sections_dir, "resume"), exist_ok=True)

        mapping = {
            "ml_subject": "ml/subject.tex",
            "ml_recipient": "ml/recipient.tex",
            "ml_body": "ml/body.tex",
            "resume_summary": "resume/summary.tex",
            "resume_experience": "resume/experience.tex",
            "resume_competencies": "resume/technical_competencies.tex"
        }

        for key, rel_path in mapping.items():
            content = sections.get(key, "").strip()
            if content:
                abs_path = os.path.join(self.sections_dir, rel_path)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                print(f"Written section to: {abs_path}")

    def edit_section(self, api_key, current_text, user_prompt, model="gemini-2.5-flash", temperature=0.4):
        """Uses Gemini to edit a single section based on user instructions."""
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
            client = genai.Client(api_key=api_key)
            config = genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature
            )
            response = client.models.generate_content(model=model, contents=prompt, config=config)
            
            # Clean up potential markdown blocks if the model ignores instructions
            result = response.text.strip()
            if result.startswith("```latex"):
                result = result[8:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            return result.strip()
        except Exception as e:
            raise RuntimeError(f"Gemini API chat error: {e}")

    def extract_job_details(self, api_key, job_description, context_dict, model="gemini-2.5-flash", temperature=0.1):
        """Uses Gemini to extract details and auto-select checkboxes based on the job description."""
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
            "Return ONLY valid JSON."
        )
        
        try:
            client = genai.Client(api_key=api_key)
            config = genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json"
            )
            response = client.models.generate_content(model=model, contents=job_description, config=config)
            
            return json.loads(response.text.strip())
        except Exception as e:
            raise RuntimeError(f"Extraction error: {e}")

    def run_sanity_check(self, api_key, document_text, model="gemini-2.5-flash"):
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
            client = genai.Client(api_key=api_key)
            config = genai_types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
            response = client.models.generate_content(model=model, contents=document_text, config=config)
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"Sanity Check API error: {e}")

