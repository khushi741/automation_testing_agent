import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Workspace directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = WORKSPACE_DIR / "static"
REPORTS_DIR = STATIC_DIR / "reports"
SCREENSHOTS_DIR = STATIC_DIR / "screenshots"
SCRATCH_DIR = WORKSPACE_DIR / "scratch"

# Ensure directories exist
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://agent:agent_pass@localhost:5432/test_agent"
)

# AI/LLM configurations
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

# Embedding configurations
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
HEALING_THRESHOLD = 0.20  # Similarity score threshold to accept a self-healed locator

# Playwright configuration
PLAYWRIGHT_TIMEOUT = 3000  # 3 seconds timeout for fast self-healing trigger
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_SLOW_MO = 200   # Small delay for demo execution visual clarity
