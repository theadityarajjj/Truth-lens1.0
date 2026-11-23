import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    FACTCHECK_API_KEY = os.getenv("FACTCHECK_API_KEY", "")
    DATABASE_PATH = os.getenv("DATABASE_PATH", "truthlens.db")
    MAX_INPUT_CHARS = 5000