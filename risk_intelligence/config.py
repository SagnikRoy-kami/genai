import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM Configuration ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))

# ── Database Configuration ──────────────────────────────────────────
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/projects.db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
CHROMA_COLLECTION = "company_history"

# ── Upload Configuration ────────────────────────────────────────────
UPLOAD_DIR = "uploads"
MAX_CONTEXT_CHARS = 4000
