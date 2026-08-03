"""
Cleanup utilities — removes cloned repository files after test runs complete,
and performs startup cleanup of orphaned scratch directories.
"""
import shutil
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from src.config import SCRATCH_DIR

logger = logging.getLogger(__name__)


def cleanup_repo(repo_id: str, local_path: Optional[str] = None):
    """
    Deletes the cloned repo directory after a test run completes.
    Targets the scratch/<repo_id> directory specifically.
    Removes node_modules and the full clone, keeping only DB records.
    """
    target = Path(local_path) if local_path else SCRATCH_DIR / repo_id

    if target.exists():
        logger.info(f"Cleaning up cloned repo at {target}...")
        try:
            shutil.rmtree(target)
            logger.info(f"Successfully removed {target}")
        except Exception as e:
            logger.error(f"Failed to remove {target}: {e}")
            # Try removing node_modules at least
            nm = target / "node_modules"
            if nm.exists():
                try:
                    shutil.rmtree(nm)
                    logger.info(f"Removed node_modules from {target}")
                except Exception as nm_err:
                    logger.error(f"Failed to remove node_modules: {nm_err}")
    else:
        logger.debug(f"Cleanup target {target} does not exist, skipping.")


def startup_cleanup(db: Session):
    """
    Called on FastAPI startup. Scans the scratch directory for orphaned
    directories that don't correspond to any active 'cloning' or 'analyzing'
    repo in the database, and removes them.
    """
    from models import Repo

    if not SCRATCH_DIR.exists():
        return

    logger.info("Running startup cleanup of orphaned scratch directories...")

    # Get all repo IDs that are actively being processed
    active_repos = db.query(Repo.id).filter(
        Repo.status.in_(["cloning", "analyzing"])
    ).all()
    active_ids = {r.id for r in active_repos}

    removed_count = 0
    for item in SCRATCH_DIR.iterdir():
        if item.is_dir() and item.name not in active_ids:
            try:
                shutil.rmtree(item)
                logger.info(f"Removed orphaned scratch directory: {item.name}")
                removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove orphaned directory {item.name}: {e}")

    logger.info(f"Startup cleanup complete. Removed {removed_count} orphaned directories.")
