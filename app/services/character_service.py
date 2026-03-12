"""
Character data service - handles reading and caching character/storage JSON
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..utils.security import safe_read_json, validate_path, SecurityError
from ..utils.constants import CHARACTER_FILE_PATTERN, STORAGE_FILE_PATTERN, FAVOR_LEVELS, normalize_favor_level
from .cache_service import get_cache

logger = logging.getLogger(__name__)


class CharacterService:
    """
    Service for reading character data from VIP JSON exports.

    Centralizes all character file reading with:
    - Caching (invalidated when file changes)
    - Security validation
    - Consistent error handling
    - Multi-character support
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

    def _get_all_files(self, pattern: str) -> List[Path]:
        """
        Get all files matching pattern.

        Args:
            pattern: Glob pattern (e.g., 'Character_*.json')

        Returns:
            List of paths sorted by modification time (newest first)
        """
        try:
            files = list(self._reports_dir.glob(pattern))
            return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError as e:
            logger.error(f"Error finding files matching {pattern}: {e}")
            return []

    def get_all_characters(self) -> List[Dict[str, Any]]:
        """
        Get list of all available characters with summary info.

        Returns:
            List of character summaries:
            [
                {
                    'name': 'Boricha',
                    'server': 'Arisetsu',
                    'race': 'Elf',
                    'questCount': 87,
                    'timestamp': '2026-03-08 04:12:59Z',
                    'fileName': 'Character_Boricha_Arisetsu.json'
                }
            ]
        """
        characters = []
        char_files = self._get_all_files(CHARACTER_FILE_PATTERN)

        for char_file in char_files:
            try:
                data = safe_read_json(
                    char_file,
                    basedir=self._reports_dir,
                    max_size_mb=50
                )
                if data:
                    characters.append({
                        'name': data.get('Character', 'Unknown'),
                        'server': data.get('ServerName', 'Unknown'),
                        'race': data.get('Race', 'Unknown'),
                        'questCount': len(data.get('ActiveQuests', [])),
                        'timestamp': data.get('Timestamp', ''),
                        'fileName': char_file.name
                    })
            except (SecurityError, json.JSONDecodeError) as e:
                logger.error(f"Error loading character file {char_file.name}: {e}")

        return characters

    def get_character_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get character data by character name.

        Args:
            name: Character name (e.g., 'Boricha')

        Returns:
            Character data dict or None if not found
        """
        # Look for Character_<name>_*.json
        pattern = f"Character_{name}_*.json"
        char_file = self._get_latest_file(pattern)

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

    def get_character_details(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed character info for the Character tab.

        Args:
            name: Character name

        Returns:
            Detailed character data including skills, favor, currencies, etc.
        """
        char_data = self.get_character_by_name(name)
        if not char_data:
            return None

        from .npc_service import get_npc_service
        npc_service = get_npc_service()

        # Process skills
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

        # Process favor
        raw_npcs = char_data.get('NPCs', {})
        favor = {}
        for internal_name, npc_data in raw_npcs.items():
            favor_level = npc_data.get('FavorLevel')
            if favor_level:
                display_name = npc_service.get_display_name(internal_name)
                normalized_level = normalize_favor_level(favor_level)
                favor[display_name] = {
                    'level': normalized_level,
                    'rank': FAVOR_LEVELS.index(normalized_level) if normalized_level in FAVOR_LEVELS else -1
                }

        # Process currencies
        currencies = char_data.get('Currencies', {})

        # Process recipe completions
        recipe_completions = char_data.get('RecipeCompletions', {})

        return {
            'name': char_data.get('Character', 'Unknown'),
            'server': char_data.get('ServerName', 'Unknown'),
            'race': char_data.get('Race', 'Unknown'),
            'timestamp': char_data.get('Timestamp', ''),
            'skills': skills,
            'favor': favor,
            'currencies': currencies,
            'recipeCompletions': recipe_completions,
            'activeQuests': char_data.get('ActiveQuests', []),
            'activeWorkOrders': char_data.get('ActiveWorkOrders', [])
        }

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

    def get_active_quests(self, character_name: Optional[str] = None) -> List[str]:
        """
        Get list of active quest internal names.

        Args:
            character_name: Optional character name to filter by.
                           If None, uses the latest character file.

        Returns:
            List of quest internal names
        """
        if character_name:
            char_data = self.get_character_by_name(character_name)
        else:
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
        Get NPC favor levels using display names.

        Returns:
            Dict mapping NPC display name to favor data:
            {
                'Joeh': {
                    'level': 'BestFriends',
                    'rank': 4
                }
            }
        """
        from .npc_service import get_npc_service

        char_data = self.get_character_data()
        if not char_data:
            return {}

        npc_service = get_npc_service()
        raw_npcs = char_data.get('NPCs', {})
        favor = {}

        for internal_name, npc_data in raw_npcs.items():
            favor_level = npc_data.get('FavorLevel')
            if favor_level:
                # Convert internal name (NPC_Joe) to display name (Joeh)
                display_name = npc_service.get_display_name(internal_name)
                # Normalize favor level (BestFriends -> Best Friends)
                normalized_level = normalize_favor_level(favor_level)
                favor[display_name] = {
                    'level': normalized_level,
                    'rank': FAVOR_LEVELS.index(normalized_level) if normalized_level in FAVOR_LEVELS else -1
                }

        return favor

    def get_all_characters_favor(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get NPC favor levels for all characters.

        Returns:
            Dict mapping character name to their favor data:
            {
                'Boricha': {
                    'Joeh': {'level': 'Best Friends', 'rank': 4},
                    'Marna': {'level': 'Friends', 'rank': 2}
                },
                'Bergheim': {
                    'Joeh': {'level': 'Close Friends', 'rank': 3},
                    ...
                }
            }
        """
        from .npc_service import get_npc_service

        npc_service = get_npc_service()
        all_favor = {}

        for char_info in self.get_all_characters():
            char_name = char_info['name']
            char_data = self.get_character_by_name(char_name)
            if not char_data:
                continue

            raw_npcs = char_data.get('NPCs', {})
            favor = {}

            for internal_name, npc_data in raw_npcs.items():
                favor_level = npc_data.get('FavorLevel')
                if favor_level:
                    display_name = npc_service.get_display_name(internal_name)
                    normalized_level = normalize_favor_level(favor_level)
                    favor[display_name] = {
                        'level': normalized_level,
                        'rank': FAVOR_LEVELS.index(normalized_level) if normalized_level in FAVOR_LEVELS else -1
                    }

            all_favor[char_name] = favor

        return all_favor

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
