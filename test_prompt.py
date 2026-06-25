import textwrap

salary_instruction = "test"
humanize_guideline = "test"
lang_instruction = "test"
examples_str = "test"
skills_str = "test"
experience_str = "test"
career_context = "test"
paper_sections = "test"
style_profile = "test"
params = {}

system_instructions = textwrap.dedent(f"""
    You are an expert technical career advisor and LaTeX document generator helping 
    John Doe tailor his application for a specific job opening.

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
    Generate tailored LaTeX code for the following 5 distinct sections.
    Your entire response MUST be formatted using the XML-like tags exactly as shown below, with the exact LaTeX content inside.
    DO NOT output any markdown blocks or commentary outside the tags.

    1. <ML_SUBJECT>: Subject line of the motivation letter.
       MUST BE EXACTLY 1 LINE. 
       Format: Application for [Target Title] | Ref. [Optional Reference] or something similar, translated to {lang_instruction}.

    2. <ML_RECIPIENT>: The recipient block.
       Include the company name, contact person (if any), and address exactly as provided, formatted cleanly with standard LaTeX newlines (\\\\).

    3. <ML_BODY>: The body of the motivation letter.
       Write entirely in {lang_instruction}.
       Include standard greeting (e.g. "Sehr geehrte Frau [Name]" or "Sehr geehrtes Recruiting-Team"), 3-4 body paragraphs tailoring John's career story to the JD requirements and selected examples.
       Make sure the closing mentions any graduation/availability details and work permit details if they are relevant and specified in the candidate's career context.
       Do NOT include any closing salutation (e.g., "Mit freundlichen Grüßen" or the candidate's name) at the end, as this is already dynamically appended by the template.

    4. <RESUME_EXPERIENCE>: The professional/research experience section for the resume.
       You MUST start this section exactly with: `\\section{{Research/Professional Experience}}`
       Generate `\\entry{{Institution}}{{Location}}{{Title}}{{Date}}` blocks for the selected experience entries, each followed by `\\begin{{adjustwidth}}{{103pt}}{{0pt}}` and bullet points with `\\sepbullet` or `\\sepentry` separators, aligned to 103pt. Use the custom job titles specified by the user!
       Make sure all dates use the short version of the month and the year, separated by "to" (e.g., "Jan 2022 to Jun 2026").
       Ensure bullet points are concrete, highly relevant to the JD, and structured with bold prefixes.

    5. <RESUME_COMPETENCIES>: Technical competencies section.
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
       
    Let's begin. Generate the 5 sections enclosed in their tags.
""")
print("Success!")
