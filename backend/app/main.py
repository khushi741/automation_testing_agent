"""
Forwarding module to support backend/app/main.py path references.
"""
import sys
from pathlib import Path

# Add backend root to sys.path
backend_root = str(Path(__file__).parent.parent)
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from main import *
from main import app
