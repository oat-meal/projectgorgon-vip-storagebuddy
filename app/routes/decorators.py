"""
Route decorators for common functionality
"""

import logging
from functools import wraps
from typing import Callable

from flask import g, current_app

from config import get_config
from ..utils.responses import not_configured, internal_error

logger = logging.getLogger(__name__)

# Global tracker instances (initialized lazily)
_quest_db = None
_chat_parser = None
_inventory_parser = None
_tracker = None


def get_tracker_components():
    """Get or initialize tracker components"""
    global _quest_db, _chat_parser, _inventory_parser, _tracker

    if _tracker is not None:
        return _quest_db, _chat_parser, _inventory_parser, _tracker

    config = get_config()
    if not config.get_status()['configured']:
        return None, None, None, None

    try:
        from quest_parser import QuestDatabase, ChatLogParser, QuestTracker, InventoryParser
        from ..utils.paths import get_bundled_path

        base_dir = config.get_base_dir()
        chat_log_dir = config.get_chat_log_dir()
        reports_dir = config.get_reports_dir()

        _quest_db = QuestDatabase(
            base_dir / 'quests.json',
            base_dir / 'items.json'
        )
        _chat_parser = ChatLogParser(chat_log_dir)
        _inventory_parser = InventoryParser(reports_dir)
        _tracker = QuestTracker(_quest_db, _chat_parser, _inventory_parser)

        logger.info("Quest tracker components initialized")
        return _quest_db, _chat_parser, _inventory_parser, _tracker

    except Exception as e:
        logger.error(f"Failed to initialize tracker: {e}")
        return None, None, None, None


def require_configured(f: Callable) -> Callable:
    """
    Decorator to ensure app is configured before accessing quest data.

    Sets g.quest_db, g.chat_parser, g.inventory_parser, g.tracker
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = get_config()

        if not config.get_status()['configured']:
            return not_configured()

        # Get or initialize tracker components
        quest_db, chat_parser, inventory_parser, tracker = get_tracker_components()

        if tracker is None:
            return internal_error("Failed to initialize quest tracker")

        # Store in Flask g object for request context
        g.quest_db = quest_db
        g.chat_parser = chat_parser
        g.inventory_parser = inventory_parser
        g.tracker = tracker
        g.config = config

        return f(*args, **kwargs)

    return decorated_function


def reinitialize_tracker():
    """Force reinitialization of tracker components (after config change)"""
    global _quest_db, _chat_parser, _inventory_parser, _tracker
    _quest_db = None
    _chat_parser = None
    _inventory_parser = None
    _tracker = None
