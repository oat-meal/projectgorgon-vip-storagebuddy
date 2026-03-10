"""
Path utilities for handling bundled resources and base directories
"""

import sys
from pathlib import Path
from typing import Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def is_frozen() -> bool:
    """Check if running as PyInstaller bundle"""
    return getattr(sys, 'frozen', False)


@lru_cache(maxsize=1)
def get_bundle_dir() -> Path:
    """Get the PyInstaller bundle directory (or script directory if not frozen)"""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent  # app/utils -> app -> project root


def get_bundled_path(relative_path: str) -> Path:
    """
    Get the path to a bundled resource.
    Works for both PyInstaller bundles and normal Python execution.

    Args:
        relative_path: Path relative to bundle/project root

    Returns:
        Absolute path to the resource
    """
    return get_bundle_dir() / relative_path


@lru_cache(maxsize=1)
def get_base_dir() -> Path:
    """
    Get the base directory for application data.
    This is where config, logs, and cached data are stored.

    Returns:
        Path to base data directory
    """
    from config import get_config
    return get_config().get_base_dir()


def get_project_root() -> Path:
    """Get the project root directory (where web_server.py lives)"""
    if is_frozen():
        # In frozen mode, executable location
        return Path(sys.executable).parent
    # In development, relative to this file
    return Path(__file__).parent.parent.parent
