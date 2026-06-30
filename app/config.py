import logging
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
STATIC_DIR = FRONTEND_DIR / "static"

load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("MODEL", "gemini-3.1-flash-live-preview")
VOICE = os.getenv("VOICE", "Puck")
SUPPORTED_MODELS = {
    "gemini-3.1-flash-live-preview": "Gemini 3.1 Flash Live Preview",
    "gemini-2.5-flash-native-audio-preview-12-2025": "Gemini 2.5 Flash Live Preview",
}
SUPPORTED_VOICES = {
    "Puck": "Puck",
    "Kore": "Kore",
    "Charon": "Charon",
    "Aoede": "Aoede",
    "Fenrir": "Fenrir",
    "Leda": "Leda",
}
FEEDBACK_STORE = BASE_DIR / os.getenv("FEEDBACK_STORE", "data/feedback.jsonl")
