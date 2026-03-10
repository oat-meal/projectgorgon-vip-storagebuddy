"""
Character data service - handles reading and caching character/storage JSON
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..utils.security import safe_read_json, validate_path, SecurityError
from ..utils.constants import CHARACTER_FILE_PATTERN, STORAGE_FILE_PATTERN, FAVOR_LEVELS
from .cache_service import get_cache

logger = logging.getLogger(__name__)


class CharacterService:
    """
    Service for reading character data from VIP JSON exports.

    Centralizes all character file reading with:
    - Caching (invalidated when file changes)
    - Security validation
    - Consistent error handling
    """

    def __init__(self, reports_dir: Path):
        """
        Initialize character service.

        Args:
            reports_dir: Directory containing character/storage JSON exports
        """
        self._reports_dir = reports_dir
        self._cache = get_cache()

    def _get_latest_file(self, pattern: str) -> Optional[Path]:
        """
        Get the most recently modified file matching pattern.

        Args:
            pattern: Glob pattern (e.g., 'Character_*.json')

        Returns:
            Path to latest file or None if not found
        """
        try:
            files = list(self._reports_dir.glob(pattern))
            if not files:
                return None
            return max(files, key=lambda p: p.stat().st_mtime)
        except OSError as e:
            logger.error(f"Error finding files matching {pattern}: {e}")
            return None

    def get_latest_character_file(self) -> Optional[Path]:
        """Get path to most recent Character JSON export"""
        return self._get_latest_file(CHARACTER_FILE_PATTERN)

    def get_latest_storage_file(self) -> Optional[Path]:
        """Get path to most recent Storage JSON export"""
        return self._get_latest_file(STORAGE_FILE_PATTERN)

    def get_character_data(self) -> Optional[Dict[str, Any]]:
        """
        Get character data from latest export with caching.

        Returns:
            Character data dict or None if not available
        """
        char_file = self.get_latest_character_file()
        if not char_file:
            return None

        cache_key = f"character:{char_file.name}"

        def load_character():
            try:
                return safe_read_json(
                    char_file,
                    basedir=self._reports_dir,
                    max_size_mb=50
                )
            except (SecurityError, json.JSONDecodeError) as e:
                logger.error(f"Error loading character data: {e}")
                return None

        return self._cache.get_or_compute(
            cache_key,
            load_character,
            ttl=5.0,
            file_path=char_file
        )

    def get_active_quests(self) -> List[str]:
        """
        Get list of active quest internal names.

        Returns:
            List of quest internal names
        """
        char_data = self.get_character_data()
        if not char_data:
            return []
        return char_data.get('ActiveQuests', [])

    def get_skills(self) -> Dict[str, Dict[str, Any]]:
        """
        Get character skills with effective levels.

        Returns:
            Dict mapping skill name to skill data:
            {
                'Cooking': {
                    'level': 50,
                    'bonusLevels': 5,
                    'effectiveLevel': 55,
                    'xpToNext': 1234,
                    'xpNeeded': 5000
                }
            }
        """
        char_data = self.get_character_data()
        if not char_data:
            return {}

        raw_skills = char_data.get('Skills', {})
        skills = {}

        for skill_name, skill_data in raw_skills.items():
            level = skill_data.get('Level', 0)
            bonus = skill_data.get('BonusLevels', 0)
            skills[skill_name] = {
                'level': level,
                'bonusLevels': bonus,
                'effectiveLevel': level + bonus,
                'xpToNext': skill_data.get('XpTowardNextLevel', 0),
                'xpNeeded': skill_data.get('XpNeededForNextLevel', 0)
            }

        return skills

    def get_effective_skill_levels(self) -> Dict[str, int]:
        """
        Get simplified skill -> effective level mapping.

        Returns:
            Dict mapping skill name to effective level
        """
        skills = self.get_skills()
        return {name: data['effectiveLevel'] for name, data in skills.items()}

    def get_favor(self) -> Dict[str, Dict[str, Any]]:
        """
        Get NPC favor levels.

        Returns:
            Dict mapping NPC name to favor data:
            {
                'Marna': {
                    'level': 'Friends',
                    'rank': 2
                }
            }
        """
        char_data = self.get_character_data()
        if not char_data:
            return {}

        raw_npcs = char_data.get('NPCs', {})
        favor = {}

        for npc_name, npc_data in raw_npcs.items():
            favor_level = npc_data.get('FavorLevel')
            if favor_level:
                favor[npc_name] = {
                    'level': favor_level,
                    'rank': FAVOR_LEVELS.index(favor_level) if favor_level in FAVOR_LEVELS else -1
                }

        return favor

    def get_character_name(self) -> str:
        """Get character name from latest export"""
        char_data = self.get_character_data()
        if not char_data:
            return 'Unknown'
        return char_data.get('Character', 'Unknown')

    def get_timestamp(self) -> str:
        """Get timestamp from latest export"""
        char_data = self.get_character_data()
        if not char_data:
            return ''
        return char_data.get('Timestamp', '')

    def get_source_file_name(self) -> Optional[str]:
        """Get the name of the source file being used"""
        char_file = self.get_latest_character_file()
        return char_file.name if char_file else None
