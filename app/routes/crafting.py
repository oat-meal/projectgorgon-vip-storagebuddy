"""
Crafting and recipe API routes
"""

import json
import logging
from flask import Blueprint, request, g

from config import get_config
from ..utils.responses import api_response, api_error, not_found
from ..utils.validation import validate_recipe_selections, ValidationError
from ..utils.paths import get_bundled_path
from ..utils.security import safe_read_json
from ..utils.constants import MAX_CRAFTING_DEPTH
from ..services.character_service import CharacterService
from ..services.cache_service import get_cache
from .decorators import require_configured

logger = logging.getLogger(__name__)

crafting_bp = Blueprint('crafting', __name__)

# In-memory store for recipe selections (synced from web app)
_recipe_selections = {}


@crafting_bp.route('/shopping_list', methods=['GET', 'POST'])
def shopping_list():
    """Get or update shopping list for selected recipes"""
    global _recipe_selections

    if request.method == 'POST':
        try:
            data = request.get_json()
            if not data:
                return api_error("No data provided", status_code=400)

            validated = validate_recipe_selections(data.get('recipes', {}))
            _recipe_selections.clear()
            _recipe_selections.update(validated)

            return api_response(
                data={'count': len(_recipe_selections)},
                message="Recipe selections updated"
            )
        except ValidationError as e:
            return api_error(e.message, code="VALIDATION_ERROR", status_code=400)

    # GET - return shopping list
    return _build_shopping_list()


def _build_shopping_list():
    """Build shopping list from current recipe selections"""
    config = get_config()
    cache = get_cache()

    # Get player skills
    char_service = CharacterService(config.get_reports_dir())
    player_skills = char_service.get_effective_skill_levels()

    # Load recipes (cached)
    recipes_file = get_bundled_path('recipes.json')
    if not recipes_file.exists():
        return api_response(data={'recipes': []}, message="No recipes file found")

    all_recipes = cache.get_or_compute(
        'recipes:all',
        lambda: safe_read_json(recipes_file),
        ttl=60.0,
        file_path=recipes_file
    )

    if not all_recipes:
        return api_response(data={'recipes': []})

    # Build lookups
    recipe_lookup = {}
    recipes_by_output = {}

    for idx, recipe in enumerate(all_recipes):
        recipe_id = f"{recipe.get('skill', 'Unknown')}_{recipe.get('name', 'Unknown')}_{idx}"
        recipe_lookup[recipe_id] = recipe

        for result in recipe.get('results', []):
            output_name = result.get('item', '')
            if output_name:
                if output_name not in recipes_by_output:
                    recipes_by_output[output_name] = []
                recipes_by_output[output_name].append({
                    'recipe': recipe,
                    'output_qty': result.get('quantity', 1)
                })

    # Get player inventory
    player_inventory = {}
    inventory_details = {}

    try:
        from .decorators import get_tracker_components
        _, _, inventory_parser, _ = get_tracker_components()

        if inventory_parser:
            items_file = inventory_parser.get_latest_items_file()
            if items_file:
                inventory_data = inventory_parser.parse_items(items_file)
                for name, data in inventory_data.items():
                    player_inventory[name] = data['total']
                    inventory_details[name] = data
    except Exception as e:
        logger.warning(f"Could not load inventory: {e}")

    # Load vendor data
    vendor_items = _load_vendor_items()

    # Build shopping list
    result_recipes = []

    for recipe_id, quantity in _recipe_selections.items():
        recipe = recipe_lookup.get(recipe_id)
        if not recipe:
            continue

        recipe_result = _process_recipe(
            recipe, recipe_id, quantity,
            player_skills, player_inventory, inventory_details,
            vendor_items, recipes_by_output
        )
        result_recipes.append(recipe_result)

    return api_response(data={'recipes': result_recipes})


def _process_recipe(
    recipe, recipe_id, quantity,
    player_skills, player_inventory, inventory_details,
    vendor_items, recipes_by_output
):
    """Process a single recipe for the shopping list"""
    recipe_skill = recipe.get('skill', 'Unknown')
    recipe_level = recipe.get('level', 0)
    player_skill_level = player_skills.get(recipe_skill, 0)
    has_skill = player_skill_level >= recipe_level

    recipe_result = {
        'id': recipe_id,
        'name': recipe.get('name', 'Unknown'),
        'skill': recipe_skill,
        'level': recipe_level,
        'playerSkillLevel': player_skill_level,
        'hasSkill': has_skill,
        'skillGap': recipe_level - player_skill_level if not has_skill else 0,
        'quantity': quantity,
        'materials': [],
        'status': 'ready'
    }

    has_gather = False
    has_buy = False
    has_craft = False

    for ingredient in recipe.get('ingredients', []):
        mat_name = ingredient.get('item') or ingredient.get('name', 'Unknown')
        mat_qty = ingredient.get('quantity', 1) * quantity
        mat_have = player_inventory.get(mat_name, 0)

        # Get detailed location info
        details = inventory_details.get(mat_name, {})
        in_inventory = details.get('in_inventory', 0) if isinstance(details, dict) else 0
        in_storage = 0
        storage_locations = {}

        if isinstance(details, dict):
            for k, v in details.items():
                if k not in ['total', 'in_inventory'] and isinstance(v, (int, float)) and v > 0:
                    in_storage += v
                    storage_locations[k] = v

        # Categorize material source
        source, source_info = _categorize_material(
            mat_name, mat_qty, mat_have,
            player_inventory, player_skills,
            vendor_items, recipes_by_output
        )

        mat_result = {
            'name': mat_name,
            'need': mat_qty,
            'have': min(mat_have, mat_qty),
            'missing': max(0, mat_qty - mat_have),
            'in_inventory': in_inventory,
            'in_storage': in_storage,
            'storage_locations': storage_locations,
            'source': source
        }

        if source == 'gather':
            has_gather = True
        elif source == 'buy':
            has_buy = True
            mat_result['vendors'] = source_info
            if source_info:
                v = source_info[0]
                mat_result['vendor_info'] = f"{v['vendor']} ({v['location']}) - {v['favor']}, {v['price']}g"
        elif source == 'craft':
            has_craft = True
            mat_result['craft_info'] = source_info

        # Add vendor info even if craftable
        if mat_name in vendor_items and mat_have < mat_qty and source != 'buy':
            mat_result['vendors'] = vendor_items[mat_name]

        recipe_result['materials'].append(mat_result)

    # Determine overall status
    if not has_skill:
        recipe_result['status'] = 'no_skill'
    elif has_gather:
        recipe_result['status'] = 'gather'
    elif has_buy:
        recipe_result['status'] = 'buyable'
    elif has_craft:
        recipe_result['status'] = 'craftable'
    else:
        recipe_result['status'] = 'ready'

    return recipe_result


def _categorize_material(
    mat_name, mat_qty, mat_have,
    player_inventory, player_skills,
    vendor_items, recipes_by_output
):
    """Categorize how a material can be obtained"""
    missing = mat_qty - mat_have

    if missing <= 0:
        return 'storage', None

    # Check if craftable
    can_craft, craft_info = _can_craft_item(
        mat_name, missing,
        player_inventory, player_skills,
        recipes_by_output
    )
    if can_craft:
        return 'craft', craft_info

    # Check if buyable
    if mat_name in vendor_items:
        return 'buy', vendor_items[mat_name]

    return 'gather', None


def _can_craft_item(
    item_name, qty_needed,
    available_inventory, skills,
    recipes_by_output,
    depth=0, visited=None
):
    """Recursively check if an item can be crafted"""
    if visited is None:
        visited = set()

    if item_name in visited or depth > MAX_CRAFTING_DEPTH:
        return False, None

    visited.add(item_name)

    if item_name not in recipes_by_output:
        return False, None

    for recipe_info in recipes_by_output[item_name]:
        recipe = recipe_info['recipe']
        output_qty = recipe_info['output_qty']

        # Check skill requirement
        recipe_skill = recipe.get('skill', '')
        recipe_level = recipe.get('level', 0)
        player_level = skills.get(recipe_skill, 0)

        if player_level < recipe_level:
            continue

        crafts_needed = (qty_needed + output_qty - 1) // output_qty

        can_make = True
        sub_crafts = []

        for ingredient in recipe.get('ingredients', []):
            ing_name = ingredient.get('item') or ingredient.get('name', '')
            ing_qty = ingredient.get('quantity', 1) * crafts_needed
            ing_have = available_inventory.get(ing_name, 0)

            if ing_have >= ing_qty:
                continue

            missing = ing_qty - ing_have
            sub_can_craft, sub_info = _can_craft_item(
                ing_name, missing,
                available_inventory, skills,
                recipes_by_output,
                depth + 1, visited.copy()
            )

            if sub_can_craft:
                sub_crafts.append({
                    'item': ing_name,
                    'quantity': missing,
                    'recipe': sub_info
                })
            else:
                can_make = False
                break

        if can_make:
            return True, {
                'recipe_name': recipe.get('name'),
                'skill': recipe.get('skill'),
                'level': recipe.get('level', 0),
                'crafts_needed': crafts_needed,
                'sub_crafts': sub_crafts
            }

    return False, None


def _load_vendor_items():
    """Load vendor item data"""
    vendor_file = get_bundled_path('vendor_inventory.json')
    if not vendor_file.exists():
        return {}

    cache = get_cache()
    vendor_data = cache.get_or_compute(
        'vendors:all',
        lambda: safe_read_json(vendor_file),
        ttl=60.0,
        file_path=vendor_file
    )

    if not vendor_data:
        return {}

    vendor_items = {}
    vendors_dict = vendor_data.get('vendors', vendor_data)

    for vendor_name, vendor_info in vendors_dict.items():
        if isinstance(vendor_info, dict) and 'items' in vendor_info:
            location = vendor_info.get('location', '')
            for item_name, item_data in vendor_info.get('items', {}).items():
                if item_name not in vendor_items:
                    vendor_items[item_name] = []
                vendor_items[item_name].append({
                    'vendor': vendor_name,
                    'location': location,
                    'favor': item_data.get('favor', 'Unknown') if isinstance(item_data, dict) else 'Unknown',
                    'price': item_data.get('price', 0) if isinstance(item_data, dict) else 0
                })

    return vendor_items


@crafting_bp.route('/skills')
@require_configured
def get_player_skills():
    """Get character skills from the latest Character JSON export"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    skills = char_service.get_skills()
    if not skills:
        return api_response(data={
            'skills': {},
            'character': 'Unknown'
        })

    return api_response(data={
        'skills': skills,
        'character': char_service.get_character_name(),
        'source_file': char_service.get_source_file_name(),
        'timestamp': char_service.get_timestamp()
    })


@crafting_bp.route('/favor')
@require_configured
def get_player_favor():
    """Get character NPC favor levels from the latest Character JSON export"""
    from ..utils.constants import FAVOR_LEVELS

    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    favor = char_service.get_favor()

    return api_response(data={
        'favor': favor,
        'favor_levels': FAVOR_LEVELS,
        'character': char_service.get_character_name(),
        'source_file': char_service.get_source_file_name(),
        'timestamp': char_service.get_timestamp()
    })


@crafting_bp.route('/inventory')
def get_player_inventory():
    """Get full player inventory with storage locations"""
    try:
        from .decorators import get_tracker_components
        _, _, inventory_parser, _ = get_tracker_components()

        if not inventory_parser:
            return api_response(data={'items': {}}, message="Inventory parser not initialized")

        items_file = inventory_parser.get_latest_items_file()
        if not items_file:
            return api_response(data={'items': {}}, message="No inventory export found")

        inventory_data = inventory_parser.parse_items(items_file)

        return api_response(data={
            'items': inventory_data,
            'source_file': items_file.name,
            'item_count': len(inventory_data)
        })
    except Exception as e:
        logger.error(f"Error loading inventory: {e}")
        return api_error(str(e), status_code=500)
