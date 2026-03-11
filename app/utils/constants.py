"""
Application constants - eliminates magic numbers throughout codebase
"""

# Search and pagination limits
MAX_SEARCH_RESULTS = 20
MAX_PINNED_ITEMS = 20

# Crafting recursion limits
MAX_CRAFTING_DEPTH = 3

# File size limits (in MB)
MAX_FILE_SIZE_MB = 50
MAX_JSON_DEPTH = 10

# Input validation limits
MAX_QUERY_LENGTH = 200
MAX_PATH_LENGTH = 500
MAX_RECIPE_QUANTITY = 999

# Heartbeat/timeout settings (in seconds)
HEARTBEAT_TIMEOUT_SECONDS = 6
AUTO_REFRESH_INTERVAL_SECONDS = 5
OVERLAY_REFRESH_INTERVAL_SECONDS = 3

# Favor levels in order (index = rank, higher = better)
# These are display names with spaces
FAVOR_LEVELS = [
    "Neutral",
    "Comfortable",
    "Friends",
    "Close Friends",
    "Best Friends",
    "Like Family",
    "Soul Mates"
]

# Mapping from game internal format (no spaces) to display format (with spaces)
FAVOR_LEVEL_ALIASES = {
    "CloseFriends": "Close Friends",
    "BestFriends": "Best Friends",
    "LikeFamily": "Like Family",
    "SoulMates": "Soul Mates",
}


def normalize_favor_level(favor_level: str) -> str:
    """
    Normalize favor level from game format to display format.

    Args:
        favor_level: Favor level string (e.g., "BestFriends" or "Best Friends")

    Returns:
        Normalized favor level with spaces (e.g., "Best Friends")
    """
    return FAVOR_LEVEL_ALIASES.get(favor_level, favor_level)

# Sensitive fields to redact from logs
SENSITIVE_LOG_FIELDS = [
    'password',
    'token',
    'secret',
    'api_key',
    'auth',
]

# File patterns for game data
CHARACTER_FILE_PATTERN = 'Character_*.json'
STORAGE_FILE_PATTERN = 'Storage_*.json'
CHAT_LOG_PATTERN = 'Chat-*.log'
