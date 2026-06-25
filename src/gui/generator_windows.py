import os
import json
import requests
from .generator import Generator, DEFAULT_MODEL, _strip_code_fences

PROVIDER_GEMINI = "gemini"
PROVIDER_KIMI = "kimi"
PROVIDER_CLAUDE = "claude"
PROVIDER_OLLAMA = "ollama"

import time

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_MODEL = "gemini-2.0-flash"

KIMI_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "moonshot-v1-128k"  # largest context — handles big generation prompts

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"


def _openai_compat_complete(base_url, api_key, model, system, user_content, max_tokens, provider_name, timeout=60):
    if not api_key:
        raise ValueError(
            f"{provider_name} API key not set.\n"
            "Add it in Tools → Settings."
        )
    
    MAX_RETRIES = 5
    BACKOFF_FACTOR = 2
    for attempt in range(MAX_RETRIES):
        json_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        if provider_name == "Ollama":
            json_data["options"] = {"num_ctx": 16384}

        resp = requests.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=json_data,
            timeout=timeout,
        )
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
                    "at https://aistudio.google.com/apikey and update it in the sidebar settings."
                )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()




class GeneratorWindows(Generator):
    """Windows variant — all AI calls routed to the provider chosen in Settings."""

    def _get_settings(self):
        personal_settings = os.path.join(self.project_root, "personal", "data", "gui_settings.json")
        settings_path = personal_settings if os.path.exists(personal_settings) else os.path.join(self.project_root, "data", "gui_settings.json")
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _get_provider(self):
        return self._get_settings().get("ai_provider", PROVIDER_GEMINI)

    def _complete(self, api_key, system, user_content, max_tokens=16000, model=DEFAULT_MODEL):
        """Override: routes every AI call to the user-selected provider."""
        provider = self._get_provider()

        if provider == PROVIDER_CLAUDE:
            return super()._complete(api_key, system, user_content, max_tokens, model)

        if provider == PROVIDER_GEMINI:
            return _openai_compat_complete(
                base_url=GEMINI_URL,
                api_key=os.environ.get("GEMINI_API_KEY", ""),
                model=GEMINI_MODEL,
                system=system,
                user_content=user_content,
                max_tokens=min(max_tokens, 8192),  # Gemini flash free-tier output cap
                provider_name="Gemini",
                timeout=120,
            )

        if provider == PROVIDER_KIMI:
            return _openai_compat_complete(
                base_url=KIMI_URL,
                api_key=os.environ.get("KIMI_API_KEY", ""),
                model=KIMI_MODEL,
                system=system,
                user_content=user_content,
                max_tokens=max_tokens,
                provider_name="Kimi",
                timeout=120,
            )

        if provider == PROVIDER_OLLAMA:
            settings = self._get_settings()
            ollama_model = settings.get("ollama_model", "qwen2.5:7b")
            return _openai_compat_complete(
                base_url=OLLAMA_URL,
                api_key="ollama", # placeholder key for local server
                model=ollama_model,
                system=system,
                user_content=user_content,
                max_tokens=max_tokens,
                provider_name="Ollama",
                timeout=300,
            )

        raise ValueError(f"Unknown AI provider: {provider}")

    def _bypass_key(self, api_key):
        """Return api_key for Claude; a sentinel for other providers (bypasses base-class guard)."""
        return api_key if self._get_provider() == PROVIDER_CLAUDE else (api_key or "__provider__")

    def generate_application(self, api_key, params, style_profile, career_context,
                             papers_dict, model=DEFAULT_MODEL, temperature=0.2):
        return super().generate_application(
            self._bypass_key(api_key), params, style_profile, career_context,
            papers_dict, model, temperature)

    def extract_recipient_details(self, api_key, job_text, model=DEFAULT_MODEL):
        return super().extract_recipient_details(self._bypass_key(api_key), job_text, model)

    def extract_job_details(self, api_key, job_description, context_dict, model=DEFAULT_MODEL, temperature=0.1):
        return super().extract_job_details(self._bypass_key(api_key), job_description, context_dict, model, temperature)

    def edit_section(self, api_key, current_text, user_prompt, model=DEFAULT_MODEL, temperature=0.4):
        return super().edit_section(self._bypass_key(api_key), current_text, user_prompt, model, temperature)

    def run_sanity_check(self, api_key, document_text, model=DEFAULT_MODEL):
        return super().run_sanity_check(self._bypass_key(api_key), document_text, model)

