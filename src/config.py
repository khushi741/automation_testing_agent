import os
from pathlib import Path

# Configure cache directories on D: drive to prevent filling up C: drive
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = r"D:\playwright_browsers"
os.environ["HF_HOME"] = r"D:\hf_cache"
os.environ["SENTENCE_TRANSFORMERS_HOME"] = r"D:\hf_cache"

# Workspace directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = WORKSPACE_DIR / "static"
REPORTS_DIR = STATIC_DIR / "reports"
SCREENSHOTS_DIR = STATIC_DIR / "screenshots"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Database path for run history
DB_PATH = WORKSPACE_DIR / "db.json"

# AI/LLM configurations
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

# Embedding configurations
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
HEALING_THRESHOLD = 0.20  # Similarity score threshold to accept a self-healed locator

# Playwright configuration
PLAYWRIGHT_TIMEOUT = 3000  # 3 seconds timeout for fast self-healing trigger
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_SLOW_MO = 200   # Add a small delay for demo execution visual clarity
