import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

BENCHMARKS_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks"
MANIFEST_PATH = BENCHMARKS_DIR / "manifest.json"


def compute_file_sha256(file_path: Path) -> str:
    """Computes SHA256 checksum for a given file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_benchmark_manifest() -> Dict[str, str]:
    """Scans all benchmark files (excluding manifest.json and caches) and generates SHA256 manifest."""
    manifest: Dict[str, str] = {}
    for p in sorted(BENCHMARKS_DIR.rglob("*")):
        if p.is_file() and p.name != "manifest.json" and not any(part in p.parts for part in ["__pycache__", ".pytest_cache", ".git"]):
            rel_path = p.relative_to(BENCHMARKS_DIR).as_posix()
            manifest[rel_path] = compute_file_sha256(p)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    logger.info(f"Generated frozen benchmark manifest with {len(manifest)} files at {MANIFEST_PATH}")
    return manifest


def validate_benchmark_integrity() -> Tuple[bool, str]:
    """
    Cryptographically verifies that no benchmark files have been altered,
    tampered with, or modified since freezing.
    Fails the pipeline immediately if any drift is detected.
    """
    if not MANIFEST_PATH.exists():
        return False, f"Manifest file missing at {MANIFEST_PATH}"

    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            frozen_manifest = json.load(f)
    except Exception as e:
        return False, f"Failed to read manifest: {e}"

    for rel_path, expected_hash in frozen_manifest.items():
        file_path = BENCHMARKS_DIR / rel_path
        if not file_path.exists():
            return False, f"Benchmark file missing: {rel_path}"
        actual_hash = compute_file_sha256(file_path)
        if actual_hash != expected_hash:
            return False, f"Benchmark file tampered or modified: {rel_path} (expected {expected_hash[:10]}..., got {actual_hash[:10]}...)"

    return True, f"All {len(frozen_manifest)} benchmark files verified byte-identical to frozen manifest."


if __name__ == "__main__":
    m = generate_benchmark_manifest()
    print(f"Frozen {len(m)} benchmark files successfully. Manifest written to {MANIFEST_PATH}")
    ok, msg = validate_benchmark_integrity()
    print(f"Validation status: {ok} -> {msg}")
