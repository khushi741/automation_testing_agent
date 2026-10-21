import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

load_dotenv()
_cur_dir = Path(__file__).resolve().parent.parent
load_dotenv(_cur_dir / ".env")
load_dotenv(_cur_dir.parent / ".env")

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
PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "1500"))  # 1.5s snappy timeout for fast self-healing
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))    # 0ms delay for maximum cloud execution speed

# --- HealAgent 2.0 Configuration ---
CONFIG_YAML_PATH = WORKSPACE_DIR / "config.yaml"
APP_CONFIG = {}
if CONFIG_YAML_PATH.exists():
    try:
        with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
            APP_CONFIG = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to parse config.yaml: {e}")

SANDBOX_ROOT = WORKSPACE_DIR / APP_CONFIG.get("sandbox", {}).get("root_dir", "scratch/sandboxes")
SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)

TRUSTED_REPOS = APP_CONFIG.get("pipeline", {}).get("trusted_repos", [])
ALLOW_ALL_REPOS = APP_CONFIG.get("pipeline", {}).get("allow_all_repos", False)
GEMINI_API_KEY = os.getenv(APP_CONFIG.get("llm", {}).get("api_key_env", "GEMINI_API_KEY"), "")
