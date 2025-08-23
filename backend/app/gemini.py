# backend/app/gemini.py
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)
project_root = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=project_root / ".env")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini(prompt: str) -> str:
    """
    Placeholder wrapper for Gemini API. Replace with your production client code.
    """
    if not GEMINI_KEY:
        logger.warning("GEMINI_API_KEY not set — returning placeholder summary")
        return "Gemini key not configured. Install your Gemini client and replace call_gemini."
    # TODO: implement actual call using your Gemini client library / HTTP endpoint
    return "Short summary placeholder: route X recommended (lowest pollution)."
