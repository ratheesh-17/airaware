# backend/app/gemini.py
import os
import logging
logger = logging.getLogger(__name__)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini(prompt: str) -> str:
    """
    Placeholder wrapper for Gemini API. Replace with your production client code.
    For now returns a brief summary text.
    """
    if not GEMINI_KEY:
        logger.info("GEMINI_API_KEY not set — returning placeholder summary")
        return "Gemini key not configured. Install your Gemini client and replace call_gemini."
    # TODO: implement actual call using your Gemini client library / HTTP endpoint
    # Keep prompt concise to avoid large token usage.
    return "Short summary placeholder: route X recommended (lowest pollution)."
