import os
import sys
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from dotenv import load_dotenv


def _load_shared_env() -> None:
    """Load a shared .env from common locations without overriding existing env vars."""
    candidates = [
        # Repo/workspace root (one level above Job_Hunter)
        Path(__file__).parent.parent / ".env",
        # Local folder as fallback
        Path(__file__).parent / ".env",
        # User config locations
        Path.home() / ".config/gemini/.env",
        Path.home() / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(dotenv_path=p, override=False)


def _get_api_key() -> Optional[str]:
    # Prefer already-set env vars
    key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")  # often used with google-generativeai
        or os.getenv("GENAI_API_KEY")
    )
    if key:
        return key

    # Try loading from shared .env locations
    _load_shared_env()
    key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GENAI_API_KEY")
    )
    return key


def configure_genai() -> str:
    """Configure google.generativeai using a shared API key.

    Looks for keys in env vars first, then in shared .env files located at:
      - <repo_root>/.env (one level above this file)
      - Job_Hunter/.env
      - ~/.config/gemini/.env
      - ~/.env

    Accepts any of: GEMINI_API_KEY, GOOGLE_API_KEY, GENAI_API_KEY.
    """
    api_key = _get_api_key()

    # Optional interactive fallback if running in a TTY
    if not api_key and sys.stdin.isatty():
        try:
            from getpass import getpass

            api_key = getpass("Enter Gemini API Key: ")
        except Exception:
            api_key = None

    if not api_key:
        raise RuntimeError(
            "No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment, "
            "or create a .env in one of: ../.env (repo root), Job_Hunter/.env, ~/.config/gemini/.env, or ~/.env."
        )

    genai.configure(api_key=api_key)
    return api_key


__all__ = ["configure_genai"]