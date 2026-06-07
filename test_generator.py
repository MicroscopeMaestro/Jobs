import os
import sys

PROJECT_ROOT = "/Users/juanmunoz/Documents/GitHub/Jobs"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
api_key = os.environ.get("GEMINI_API_KEY")

from src.gui.generator import Generator

params = {
    "job_description": "Test JD",
    "title": "Engineer",
    "focus": [],
    "examples": [],
    "skills": [],
    "experience": [],
    "attachments": {"professional_experience": [], "education": [], "certificates": [], "others": []},
    "language": "en",
    "salary": "",
    "recipient_company": "Acme",
    "recipient_contact": "",
    "recipient_address": "",
    "page_limit": 2,
    "humanize": False
}

gen = Generator(project_root=PROJECT_ROOT)
tuning = {"model": "gemini-2.5-flash", "temperature": 0.3}

try:
    sections = gen.generate_application(
        api_key=api_key,
        params=params,
        style_profile="",
        career_context="",
        papers_dict={},
        model=tuning["model"],
        temperature=tuning["temperature"]
    )
    print("Generation successful!")
except Exception as e:
    print(f"Exception: {e}")
