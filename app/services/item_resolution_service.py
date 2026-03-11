"""
Item resolution service - determines how items can be obtained

This service provides a unified way to check if an item is:
- Available in inventory/storage
- Buyable from vendors (with favor requirements)
- Craftable (with skill requirements)

Used by both the crafting and quest systems.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..utils.paths import get_bundled_path
from ..utils.security import safe_read_json
from ..utils.constants import MAX_CRAFTING_DEPTH
from .cache_service import get_cache
from .vendor_service import get_vendor_service

logger = logging.getLogger(__name__)


@dataclass
class RecipeInfo:
    """Information about a recipe that can craft an item"""
    recipe_id: str
    recipe_name: str
    skill: str
    level: int
    output_quantity: int
    crafts_needed: int
    has_skill: bool
    skill_gap: int
    ingredients: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ItemResolution:
    """Resolution result for an item"""
    item_name: str
    quantity_needed: int
    quantity_have: int
    quantity_missing: int

    # Location breakdown
    in_inventory: int = 0
    in_storage: int = 0
    storage_locations: Dict[str, int] = field(default_factory=dict)

    # Acquisition options
    is_craftable: bool = False
    recipe_info: Optional[RecipeInfo] = None
    recipe_id: Optional[str] = None  # For easy pinning

    is_buyable: bool = False
    vendors: List[Dict[str, Any]] = field(default_factory=list)
    needs_favor: bool = False
    favor_met: bool = True

    # Final status
    source: str = 'gather'  # 'have', 'craft', 'buy', 'gather'


class ItemResolutionService:
    """
    Service for resolving how items can be obtained.

    Consolidates item resolution logic used by both crafting and quest systems.
    """

    def __init__(self):
        self._cache = get_cache()
        self._recipes = None
        self._recipe_lookup = None
        self._recipes_by_output = None
        self._vendor_items = None

    def _load_recipes(self) -> None:
        """Load and index recipe data"""
        if self._recipes is not None:
            return

        recipes_file = get_bundled_path('recipes.json')
        if not recipes_file.exists():
            self._recipes = []
            self._recipe_lookup = {}
            self._recipes_by_output = {}
            return

        self._recipes = self._cache.get_or_compute(
            'recipes:all',
            lambda: safe_read_json(recipes_file),
            ttl=60.0,
            file_path=recipes_file
        ) or []

        # Build lookups
        self._recipe_lookup = {}
        self._recipes_by_output = {}

        for idx, recipe in enumerate(self._recipes):
            recipe_id = f"{recipe.get('skill', 'Unknown')}_{recipe.get('name', 'Unknown')}_{idx}"
            self._recipe_lookup[recipe_id] = recipe

            for result in recipe.get('results', []):
                output_name = result.get('item', '')
                if output_name:
                    if output_name not in self._recipes_by_output:
                        self._recipes_by_output[output_name] = []
                    self._recipes_by_output[output_name].append({
                        'recipe_id': recipe_id,
                        'recipe': recipe,
                        'output_qty': result.get('quantity', 1)
                    })

    def _load_vendor_items(self) -> Dict[str, List[Dict]]:
        """Load vendor item data"""
        if self._vendor_items is not None:
            return self._vendor_items

        vendor_file = get_bundled_path('vendor_inventory.json')
        if not vendor_file.exists():
            self._vendor_items = {}
            return self._vendor_items

        vendor_data = self._cache.get_or_compute(
            'vendors:all',
            lambda: safe_read_json(vendor_file),
            ttl=60.0,
            file_path=vendor_file
        )

        if not vendor_data:
            self._vendor_items = {}
            return self._vendor_items

        self._vendor_items = {}
        vendors_dict = vendor_data.get('vendors', vendor_data)

        for vendor_name, vendor_info in vendors_dict.items():
            if isinstance(vendor_info, dict) and 'items' in vendor_info:
                location = vendor_info.get('location', '')
                for item_name, item_data in vendor_info.get('items', {}).items():
                    if item_name not in self._vendor_items:
                        self._vendor_items[item_name] = []
                    self._vendor_items[item_name].append({
                        'vendor': vendor_name,
                        'location': location,
                        'favor': item_data.get('favor', 'Unknown') if isinstance(item_data, dict) else 'Unknown',
                        'price': item_data.get('price', 0) if isinstance(item_data, dict) else 0
                    })

        return self._vendor_items

    def resolve_item(
        self,
        item_name: str,
        quantity_needed: int,
        player_inventory: Dict[str, int],
        inventory_details: Dict[str, Dict],
        player_skills: Dict[str, int],
        player_favor: Dict[str, Dict]
    ) -> ItemResolution:
        """
        Resolve how an item can be obtained.

        Args:
            item_name: Name of the item to resolve
            quantity_needed: How many are needed
            player_inventory: Dict mapping item name to total count
            inventory_details: Dict with detailed location info per item
            player_skills: Dict mapping skill name to effective level
            player_favor: Dict mapping NPC name to favor data

        Returns:
            ItemResolution with all acquisition options
        """
        self._load_recipes()
        vendor_items = self._load_vendor_items()

        # Get current inventory
        have = player_inventory.get(item_name, 0)
        missing = max(0, quantity_needed - have)

        # Get location details
        details = inventory_details.get(item_name, {})
        in_inventory = 0
        in_storage = 0
        storage_locations = {}

        if isinstance(details, dict):
            # Handle both formats:
            # Format 1: { 'inventory': X, 'storage': { 'Location': Y }, 'total': Z }
            # Format 2: { 'in_inventory': X, 'Location1': Y, 'Location2': Z }
            if 'inventory' in details:
                in_inventory = details.get('inventory', 0)
                storage_dict = details.get('storage', {})
                if isinstance(storage_dict, dict):
                    for loc, count in storage_dict.items():
                        if isinstance(count, (int, float)) and count > 0:
                            storage_locations[loc] = int(count)
                            in_storage += int(count)
            else:
                # Legacy format
                in_inventory = details.get('in_inventory', 0)
                for k, v in details.items():
                    if k not in ['total', 'in_inventory'] and isinstance(v, (int, float)) and v > 0:
                        in_storage += int(v)
                        storage_locations[k] = int(v)

        resolution = ItemResolution(
            item_name=item_name,
            quantity_needed=quantity_needed,
            quantity_have=min(have, quantity_needed),
            quantity_missing=missing,
            in_inventory=in_inventory,
            in_storage=in_storage,
            storage_locations=storage_locations
        )

        # If we have enough, we're done
        if missing <= 0:
            resolution.source = 'have'
            return resolution

        # Check if craftable
        recipe_info = self._find_craftable_recipe(item_name, missing, player_skills)
        if recipe_info:
            resolution.is_craftable = True
            resolution.recipe_info = recipe_info
            resolution.recipe_id = recipe_info.recipe_id

        # Check if buyable
        if item_name in vendor_items:
            resolution.vendors = vendor_items[item_name]
            vendor_service = get_vendor_service()
            has_buyable, needs_favor = vendor_service.check_vendor_favor_from_dicts(
                resolution.vendors, player_favor
            )
            resolution.is_buyable = len(resolution.vendors) > 0
            resolution.needs_favor = needs_favor
            resolution.favor_met = not needs_favor

        # Determine primary source
        if resolution.is_craftable and resolution.recipe_info.has_skill:
            resolution.source = 'craft'
        elif resolution.is_buyable and resolution.favor_met:
            resolution.source = 'buy'
        elif resolution.is_buyable:
            resolution.source = 'buy'  # Still buyable, just needs favor
        elif resolution.is_craftable:
            resolution.source = 'craft'  # Craftable but needs skill
        else:
            resolution.source = 'gather'

        return resolution

    def _find_craftable_recipe(
        self,
        item_name: str,
        quantity_needed: int,
        player_skills: Dict[str, int],
        depth: int = 0,
        visited: Optional[set] = None
    ) -> Optional[RecipeInfo]:
        """
        Find the best recipe that can craft the item.

        Prioritizes:
        1. Recipes the player has skill for
        2. Recipes with higher output quantity (more efficient)

        Returns the best recipe or None.
        """
        if visited is None:
            visited = set()

        if item_name in visited or depth > MAX_CRAFTING_DEPTH:
            return None

        visited.add(item_name)

        if item_name not in self._recipes_by_output:
            return None

        # Collect all candidate recipes with their info
        candidates = []
        for recipe_data in self._recipes_by_output[item_name]:
            recipe = recipe_data['recipe']
            recipe_id = recipe_data['recipe_id']
            output_qty = recipe_data['output_qty']

            recipe_skill = recipe.get('skill', '')
            recipe_level = recipe.get('level', 0)
            player_level = player_skills.get(recipe_skill, 0)
            has_skill = player_level >= recipe_level

            crafts_needed = (quantity_needed + output_qty - 1) // output_qty

            # Build ingredient list
            ingredients = []
            for ing in recipe.get('ingredients', []):
                ing_name = ing.get('item') or ing.get('name', '')
                ing_qty = ing.get('quantity', 1) * crafts_needed
                ingredients.append({
                    'name': ing_name,
                    'quantity': ing_qty
                })

            candidates.append(RecipeInfo(
                recipe_id=recipe_id,
                recipe_name=recipe.get('name', 'Unknown'),
                skill=recipe_skill,
                level=recipe_level,
                output_quantity=output_qty,
                crafts_needed=crafts_needed,
                has_skill=has_skill,
                skill_gap=max(0, recipe_level - player_level),
                ingredients=ingredients
            ))

        if not candidates:
            return None

        # Sort by: has_skill (True first), then by output_quantity (higher first)
        # This prioritizes recipes player can craft, then most efficient ones
        candidates.sort(key=lambda r: (not r.has_skill, -r.output_quantity))

        return candidates[0]

    def get_recipe_by_id(self, recipe_id: str) -> Optional[Dict]:
        """Get recipe data by ID"""
        self._load_recipes()
        return self._recipe_lookup.get(recipe_id)

    def find_recipes_for_item(self, item_name: str) -> List[Dict]:
        """Find all recipes that produce an item"""
        self._load_recipes()
        return self._recipes_by_output.get(item_name, [])


# Module-level singleton
_item_resolution_service: Optional[ItemResolutionService] = None


def get_item_resolution_service() -> ItemResolutionService:
    """Get singleton ItemResolutionService instance"""
    global _item_resolution_service
    if _item_resolution_service is None:
        _item_resolution_service = ItemResolutionService()
    return _item_resolution_service
