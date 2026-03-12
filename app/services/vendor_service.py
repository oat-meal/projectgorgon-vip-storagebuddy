"""
Vendor data service - unified vendor data handling for quests and crafting
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from ..utils.constants import FAVOR_LEVELS
from ..utils.security import safe_read_json
from ..utils.paths import get_bundled_path
from .cache_service import get_cache

logger = logging.getLogger(__name__)


@dataclass
class VendorInfo:
    """Standardized vendor information"""
    vendor: str
    location: str
    favor: str
    price: int = 0
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'vendor': self.vendor,
            'location': self.location,
            'favor': self.favor,
            'price': self.price,
            'note': self.note
        }

    def format_display(self) -> str:
        """Format for display in UI"""
        note = self.note or f"Requires {self.favor} favor"
        return f"{self.vendor} ({self.location}) - {note}"

    @classmethod
    def from_vendor_inventory(cls, vendor_name: str, location: str,
                               item_data: Dict) -> 'VendorInfo':
        """Create from vendor_inventory.json format"""
        return cls(
            vendor=vendor_name,
            location=location,
            favor=item_data.get('favor', 'Neutral'),
            price=item_data.get('price', 0),
            note=f"Requires {item_data.get('favor', 'Neutral')} favor"
        )


class VendorService:
    """
    Unified vendor data access and favor checking.

    Provides consistent vendor data handling for both quests and crafting modules.
    """

    def __init__(self):
        self._cache = get_cache()
        self._vendor_file = get_bundled_path('vendor_inventory.json')

    def _load_vendor_data(self) -> Dict[str, Any]:
        """Load raw vendor inventory data with caching"""
        if not self._vendor_file.exists():
            return {}

        return self._cache.get_or_compute(
            'vendors:raw',
            lambda: safe_read_json(self._vendor_file),
            ttl=60.0,
            file_path=self._vendor_file
        )

    def get_vendor_items_lookup(self) -> Dict[str, List[VendorInfo]]:
        """
        Get lookup table: item_name -> list of VendorInfo.

        Returns:
            Dict mapping item names to list of vendors that sell them
        """
        def build_lookup():
            vendor_data = self._load_vendor_data()
            vendors_dict = vendor_data.get('vendors', vendor_data)

            items_lookup: Dict[str, List[VendorInfo]] = {}

            for vendor_name, vendor_info in vendors_dict.items():
                if not isinstance(vendor_info, dict) or 'items' not in vendor_info:
                    continue

                location = vendor_info.get('location', 'Unknown')

                for item_name, item_data in vendor_info.get('items', {}).items():
                    if item_name not in items_lookup:
                        items_lookup[item_name] = []

                    items_lookup[item_name].append(
                        VendorInfo.from_vendor_inventory(
                            vendor_name, location, item_data
                        )
                    )

            return items_lookup

        return self._cache.get_or_compute(
            'vendors:items_lookup',
            build_lookup,
            ttl=60.0,
            file_path=self._vendor_file
        )

    def get_vendors_for_item(self, item_name: str) -> List[VendorInfo]:
        """
        Get all vendors that sell a specific item.

        Args:
            item_name: Display name of the item

        Returns:
            List of VendorInfo for vendors selling this item
        """
        lookup = self.get_vendor_items_lookup()
        return lookup.get(item_name, [])

    def check_vendor_favor(
        self,
        vendors: List[VendorInfo],
        player_favor: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, bool]:
        """
        Check if player has favor with any vendor.

        Args:
            vendors: List of VendorInfo for potential vendors
            player_favor: Player's favor dict from CharacterService.get_favor()

        Returns:
            (has_buyable_vendor, all_need_favor) tuple:
            - has_buyable_vendor: True if at least one vendor can sell to player
            - all_need_favor: True if vendors exist but ALL require more favor
        """
        if not vendors:
            return False, False

        has_any_vendor = False
        has_buyable_vendor = False

        for vendor in vendors:
            has_any_vendor = True
            vendor_name = vendor.vendor
            required_favor = vendor.favor

            # Get player's favor with this vendor
            player_vendor_favor = player_favor.get(vendor_name, {})
            player_favor_rank = player_vendor_favor.get('rank', -1)

            # Get required favor rank (default to 0/Neutral if unknown)
            try:
                required_rank = FAVOR_LEVELS.index(required_favor)
            except ValueError:
                required_rank = 0

            # Player can buy if their favor rank >= required rank
            if player_favor_rank >= required_rank:
                has_buyable_vendor = True
                break

        # all_need_favor is True if vendors exist but none are buyable
        all_need_favor = has_any_vendor and not has_buyable_vendor

        return has_buyable_vendor, all_need_favor

    def check_vendor_favor_from_dicts(
        self,
        vendor_dicts: List[Dict[str, Any]],
        player_favor: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, bool]:
        """
        Check vendor favor from raw dict format (for backwards compatibility).

        Accepts vendor dicts with either 'vendor' or 'name' keys.

        Args:
            vendor_dicts: List of vendor dicts
            player_favor: Player's favor dict

        Returns:
            (has_buyable_vendor, all_need_favor) tuple
        """
        vendors = []
        for v in vendor_dicts:
            # Support both 'vendor' and 'name' keys for backwards compatibility
            vendor_name = v.get('vendor') or v.get('name', '')
            vendors.append(VendorInfo(
                vendor=vendor_name,
                location=v.get('location', 'Unknown'),
                favor=v.get('favor', 'Neutral'),
                price=v.get('price', 0)
            ))

        return self.check_vendor_favor(vendors, player_favor)

    def get_favor_levels(self) -> List[str]:
        """Get ordered list of favor levels"""
        return FAVOR_LEVELS.copy()

    def check_vendor_favor_all_characters(
        self,
        vendors: List[VendorInfo],
        all_characters_favor: Dict[str, Dict[str, Dict[str, Any]]],
        current_character: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if any character has favor with vendors.

        Args:
            vendors: List of VendorInfo for potential vendors
            all_characters_favor: Dict mapping character name to their favor data
            current_character: Name of the currently selected character (to prioritize)

        Returns:
            Dict with:
            - can_buy: True if any character can buy
            - current_can_buy: True if current character can buy
            - buyer: Name of character who can buy (current character prioritized)
            - buyer_favor: The favor level the buyer has with the vendor
            - vendor_name: Name of the vendor they can buy from
            - required_favor: The favor level required
        """
        if not vendors:
            return {
                'can_buy': False,
                'current_can_buy': False,
                'buyer': None,
                'buyer_favor': None,
                'vendor_name': None,
                'required_favor': None
            }

        # First check if current character can buy
        if current_character and current_character in all_characters_favor:
            current_favor = all_characters_favor[current_character]
            for vendor in vendors:
                vendor_name = vendor.vendor
                required_favor = vendor.favor

                player_vendor_favor = current_favor.get(vendor_name, {})
                player_favor_rank = player_vendor_favor.get('rank', -1)

                try:
                    required_rank = FAVOR_LEVELS.index(required_favor)
                except ValueError:
                    required_rank = 0

                if player_favor_rank >= required_rank:
                    return {
                        'can_buy': True,
                        'current_can_buy': True,
                        'buyer': current_character,
                        'buyer_favor': player_vendor_favor.get('level', 'Unknown'),
                        'vendor_name': vendor_name,
                        'required_favor': required_favor
                    }

        # Check other characters
        for char_name, char_favor in all_characters_favor.items():
            if char_name == current_character:
                continue  # Already checked

            for vendor in vendors:
                vendor_name = vendor.vendor
                required_favor = vendor.favor

                player_vendor_favor = char_favor.get(vendor_name, {})
                player_favor_rank = player_vendor_favor.get('rank', -1)

                try:
                    required_rank = FAVOR_LEVELS.index(required_favor)
                except ValueError:
                    required_rank = 0

                if player_favor_rank >= required_rank:
                    return {
                        'can_buy': True,
                        'current_can_buy': False,
                        'buyer': char_name,
                        'buyer_favor': player_vendor_favor.get('level', 'Unknown'),
                        'vendor_name': vendor_name,
                        'required_favor': required_favor
                    }

        # No character can buy
        return {
            'can_buy': False,
            'current_can_buy': False,
            'buyer': None,
            'buyer_favor': None,
            'vendor_name': vendors[0].vendor if vendors else None,
            'required_favor': vendors[0].favor if vendors else None
        }

    def check_vendor_favor_all_characters_from_dicts(
        self,
        vendor_dicts: List[Dict[str, Any]],
        all_characters_favor: Dict[str, Dict[str, Dict[str, Any]]],
        current_character: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check vendor favor across all characters from raw dict format.

        Args:
            vendor_dicts: List of vendor dicts
            all_characters_favor: Dict mapping character name to their favor data
            current_character: Name of the currently selected character

        Returns:
            Same as check_vendor_favor_all_characters
        """
        vendors = []
        for v in vendor_dicts:
            vendor_name = v.get('vendor') or v.get('name', '')
            vendors.append(VendorInfo(
                vendor=vendor_name,
                location=v.get('location', 'Unknown'),
                favor=v.get('favor', 'Neutral'),
                price=v.get('price', 0)
            ))

        return self.check_vendor_favor_all_characters(
            vendors, all_characters_favor, current_character
        )

    def get_vendor_items_as_dicts(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get vendor item lookup as raw dicts (for backward compatibility).

        Returns dict mapping item_name -> list of vendor dicts with:
        - vendor: vendor name
        - location: vendor location
        - favor: required favor level
        - price: item price
        """
        def build_lookup():
            vendor_data = self._load_vendor_data()
            vendors_dict = vendor_data.get('vendors', vendor_data)

            items_lookup: Dict[str, List[Dict[str, Any]]] = {}

            for vendor_name, vendor_info in vendors_dict.items():
                if not isinstance(vendor_info, dict) or 'items' not in vendor_info:
                    continue

                location = vendor_info.get('location', 'Unknown')

                for item_name, item_data in vendor_info.get('items', {}).items():
                    if item_name not in items_lookup:
                        items_lookup[item_name] = []

                    items_lookup[item_name].append({
                        'vendor': vendor_name,
                        'location': location,
                        'favor': item_data.get('favor', 'Unknown') if isinstance(item_data, dict) else 'Unknown',
                        'price': item_data.get('price', 0) if isinstance(item_data, dict) else 0
                    })

            return items_lookup

        return self._cache.get_or_compute(
            'vendors:items_dict_lookup',
            build_lookup,
            ttl=60.0,
            file_path=self._vendor_file
        )


# Module-level singleton for easy access
_vendor_service: Optional[VendorService] = None


def get_vendor_service() -> VendorService:
    """Get singleton VendorService instance"""
    global _vendor_service
    if _vendor_service is None:
        _vendor_service = VendorService()
    return _vendor_service
