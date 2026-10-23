import sys
import requests
import json
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from src.config import GEMINI_API_KEY

for m in ["gemini-3.5-flash-lite", "gemini-3.6-flash"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": 'Return JSON: {"status": "success", "model": "' + m + '"}'}]}],
        "generationConfig": {"temperature": 0.1, "response_mime_type": "application/json"}
    }
    r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
    print(f"Model {m}: Status={r.status_code}")
    if r.status_code == 200:
        print("  Response:", r.json()["candidates"][0]["content"]["parts"][0]["text"])
