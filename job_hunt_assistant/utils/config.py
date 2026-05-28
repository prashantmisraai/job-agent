"""Configuration and environment loading for the job hunt assistant.

Put local secrets in ``utils/.env`` or a project-root ``.env`` file.
Common variables:

GROQ_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
LLM_PROVIDER=groq
LLM_MODEL=llama-3.3-70b-versatile
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - keeps imports friendly before deps install
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data"
COVER_LETTERS_DIR = DATA_DIR / "cover_letters"
TAILORED_RESUMES_DIR = DATA_DIR / "tailored_resumes"


def _load_environment() -> None:
    if load_dotenv is None:
        return

    for env_path in (PROJECT_ROOT / ".env", BASE_DIR / ".env", Path(__file__).parent / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


_load_environment()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
Groq_API_KEY = GROQ_API_KEY
groq_API_KEY = GROQ_API_KEY
groq_key = GROQ_API_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
