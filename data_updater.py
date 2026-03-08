#!/usr/bin/env python3
"""
Auto-download quest and item data for Project Gorgon Quest Helper
"""

import urllib.request
import json
from pathlib import Path
from typing import Optional


QUEST_DATA_URL = "https://cdn.projectgorgon.com/v386/data/quests.json"
ITEMS_DATA_URL = "https://cdn.projectgorgon.com/v386/data/items.json"


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to destination path"""
    try:
        print(f"Downloading {url}...")
        urllib.request.urlretrieve(url, dest_path)
        print(f"✓ Downloaded to {dest_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to download {url}: {e}")
        return False


def validate_json_file(file_path: Path) -> bool:
    """Validate that a file contains valid JSON"""
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except Exception:
        return False


def ensure_quest_data(base_dir: Path) -> bool:
    """Ensure quest data files exist, download if missing"""
    quests_file = base_dir / 'quests.json'
    items_file = base_dir / 'items.json'

    needs_download = False

    # Check if files exist and are valid
    if not quests_file.exists() or not validate_json_file(quests_file):
        print("Quest data missing or invalid")
        needs_download = True

    if not items_file.exists() or not validate_json_file(items_file):
        print("Item data missing or invalid")
        needs_download = True

    if not needs_download:
        return True

    # Download missing or invalid files
    print("\nDownloading game data from Project Gorgon CDN...")
    print("This may take a moment...")

    success = True

    if not quests_file.exists() or not validate_json_file(quests_file):
        if not download_file(QUEST_DATA_URL, quests_file):
            success = False

    if not items_file.exists() or not validate_json_file(items_file):
        if not download_file(ITEMS_DATA_URL, items_file):
            success = False

    if success:
        print("\n✓ Game data downloaded successfully!")
    else:
        print("\n✗ Failed to download some game data files")

    return success


if __name__ == '__main__':
    from config import get_config
    config = get_config()
    base_dir = config.get_base_dir()
    ensure_quest_data(base_dir)
