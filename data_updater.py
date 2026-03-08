#!/usr/bin/env python3
"""
Auto-download quest and item data for Project Gorgon Quest Helper
"""

import urllib.request
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

QUEST_DATA_URL = "https://cdn.projectgorgon.com/v386/data/quests.json"
ITEMS_DATA_URL = "https://cdn.projectgorgon.com/v386/data/items.json"


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to destination path"""
    try:
        logger.info(f"Downloading {url}...")

        # Add User-Agent header to avoid 403 Forbidden errors
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (ProjectGorgonQuestHelper)'}
        )

        with urllib.request.urlopen(req) as response:
            with open(dest_path, 'wb') as out_file:
                out_file.write(response.read())

        logger.info(f"✓ Downloaded to {dest_path}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to download {url}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        return False


def validate_json_file(file_path: Path) -> bool:
    """Validate that a file contains valid JSON"""
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except Exception:
        return False


def copy_bundled_data(bundled_dir: Path, dest_dir: Path) -> bool:
    """Copy bundled data files from PyInstaller bundle to destination"""
    import shutil

    try:
        quests_src = bundled_dir / 'quests.json'
        items_src = bundled_dir / 'items.json'
        quests_dest = dest_dir / 'quests.json'
        items_dest = dest_dir / 'items.json'

        if quests_src.exists():
            logger.info(f"Copying bundled quests.json to {quests_dest}...")
            shutil.copy2(quests_src, quests_dest)
            logger.info("✓ Copied quests.json")

        if items_src.exists():
            logger.info(f"Copying bundled items.json to {items_dest}...")
            shutil.copy2(items_src, items_dest)
            logger.info("✓ Copied items.json")

        return True
    except Exception as e:
        logger.error(f"✗ Failed to copy bundled data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def ensure_quest_data(base_dir: Path, bundled_dir: Optional[Path] = None) -> bool:
    """Ensure quest data files exist, copy from bundle or download if missing"""
    quests_file = base_dir / 'quests.json'
    items_file = base_dir / 'items.json'

    needs_data = False

    # Check if files exist and are valid
    if not quests_file.exists() or not validate_json_file(quests_file):
        logger.info("Quest data missing or invalid")
        needs_data = True

    if not items_file.exists() or not validate_json_file(items_file):
        logger.info("Item data missing or invalid")
        needs_data = True

    if not needs_data:
        return True

    # Try to copy from bundled resources first (PyInstaller executable)
    if bundled_dir and bundled_dir.exists():
        logger.info("Copying game data from bundled resources...")
        if copy_bundled_data(bundled_dir, base_dir):
            logger.info("✓ Game data copied successfully!")
            return True
        else:
            logger.warning("Bundled data copy failed, will try downloading...")

    # Fall back to downloading if bundled copy failed or not available
    logger.info("Downloading game data from Project Gorgon CDN...")
    logger.info("This may take a moment...")

    success = True

    if not quests_file.exists() or not validate_json_file(quests_file):
        if not download_file(QUEST_DATA_URL, quests_file):
            success = False

    if not items_file.exists() or not validate_json_file(items_file):
        if not download_file(ITEMS_DATA_URL, items_file):
            success = False

    if success:
        logger.info("✓ Game data downloaded successfully!")
    else:
        logger.error("✗ Failed to download some game data files")

    return success


if __name__ == '__main__':
    from config import get_config
    config = get_config()
    base_dir = config.get_base_dir()
    ensure_quest_data(base_dir)
