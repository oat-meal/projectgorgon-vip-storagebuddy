"""
NPC data service - provides NPC name mapping and lookup
"""

import logging
from typing import Dict, Optional

from ..utils.paths import get_bundled_path
from ..utils.security import safe_read_json
from .cache_service import get_cache

logger = logging.getLogger(__name__)


class NpcService:
    """
    Service for NPC data including name mapping.

    The game uses internal names like 'NPC_Joe' in character exports,
    but display names like 'Joeh' in the UI and vendor data.
    This service provides the mapping between them.
    """

    def __init__(self):
        self._cache = get_cache()
        self._npc_file = get_bundled_path('npcs.json')

    def _load_npc_data(self) -> Dict:
        """Load raw NPC data with caching"""
        if not self._npc_file.exists():
            logger.warning(f"NPC file not found: {self._npc_file}")
            return {}

        return self._cache.get_or_compute(
            'npcs:raw',
            lambda: safe_read_json(self._npc_file),
            ttl=300.0,  # 5 minutes - NPC data rarely changes
            file_path=self._npc_file
        )

    def get_display_name(self, internal_name: str) -> str:
        """
        Get display name for an NPC internal name.

        Args:
            internal_name: Internal name like 'NPC_Joe'

        Returns:
            Display name like 'Joeh', or the internal name if not found
        """
        npc_data = self._load_npc_data()
        if internal_name in npc_data:
            return npc_data[internal_name].get('Name', internal_name)
        return internal_name

    def get_internal_name(self, display_name: str) -> Optional[str]:
        """
        Get internal name for an NPC display name.

        Args:
            display_name: Display name like 'Joeh'

        Returns:
            Internal name like 'NPC_Joe', or None if not found
        """
        def build_reverse_lookup():
            npc_data = self._load_npc_data()
            return {v.get('Name', ''): k for k, v in npc_data.items() if v.get('Name')}

        reverse_lookup = self._cache.get_or_compute(
            'npcs:reverse_lookup',
            build_reverse_lookup,
            ttl=300.0,
            file_path=self._npc_file
        )

        return reverse_lookup.get(display_name)

    def get_name_mappings(self) -> Dict[str, str]:
        """
        Get all internal -> display name mappings.

        Returns:
            Dict mapping internal names to display names
        """
        def build_mappings():
            npc_data = self._load_npc_data()
            return {k: v.get('Name', k) for k, v in npc_data.items() if v.get('Name')}

        return self._cache.get_or_compute(
            'npcs:name_mappings',
            build_mappings,
            ttl=300.0,
            file_path=self._npc_file
        )


# Module-level singleton
_npc_service: Optional[NpcService] = None


def get_npc_service() -> NpcService:
    """Get singleton NpcService instance"""
    global _npc_service
    if _npc_service is None:
        _npc_service = NpcService()
    return _npc_service
