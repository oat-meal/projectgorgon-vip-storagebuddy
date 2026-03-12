"""
Crafting and recipe API routes
"""

import json
import logging
import threading
from flask import Blueprint, request, g

from config import get_config
from ..utils.responses import api_response, api_error, not_found
from ..utils.validation import validate_recipe_selections, ValidationError
from ..utils.constants import MAX_CRAFTING_DEPTH
from ..services.character_service import CharacterService
from ..services.vendor_service import get_vendor_service
from ..services.item_resolution_service import get_item_resolution_service
from .decorators import require_configured

logger = logging.getLogger(__name__)

crafting_bp = Blueprint('crafting', __name__)

# In-memory store for recipe selections (synced from web app)
_recipe_selections = {}
_recipe_selections_lock = threading.Lock()


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
            with _recipe_selections_lock:
                _recipe_selections.clear()
                _recipe_selections.update(validated)
                count = len(_recipe_selections)

            return api_response(
                data={'count': count},
                message="Recipe selections updated"
            )
        except ValidationError as e:
            return api_error(e.message, code="VALIDATION_ERROR", status_code=400)

    # GET - return shopping list
    return _build_shopping_list()


def _build_shopping_list():
    """Build shopping list from current recipe selections"""
    config = get_config()

    # Get player skills and favor
    char_service = CharacterService(config.get_reports_dir())
    player_skills = char_service.get_effective_skill_levels()
    player_favor = char_service.get_favor()

    # Load recipes via ItemResolutionService (consolidated, cached)
    item_resolution = get_item_resolution_service()
    all_recipes = item_resolution.get_all_recipes()

    if not all_recipes:
        return api_response(data={'recipes': []})

    # Get lookups from ItemResolutionService (consolidated)
    recipe_lookup = item_resolution.get_recipe_lookup()
    recipes_by_output = item_resolution.get_recipes_by_output()

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

    # Copy selections under lock to avoid race conditions
    with _recipe_selections_lock:
        selections_copy = dict(_recipe_selections)

    for recipe_id, quantity in selections_copy.items():
        recipe = recipe_lookup.get(recipe_id)
        if not recipe:
            continue

        recipe_result = _process_recipe(
            recipe, recipe_id, quantity,
            player_skills, player_inventory, inventory_details,
            vendor_items, recipes_by_output, player_favor
        )
        result_recipes.append(recipe_result)

    return api_response(data={'recipes': result_recipes})


def _process_recipe(
    recipe, recipe_id, quantity,
    player_skills, player_inventory, inventory_details,
    vendor_items, recipes_by_output, player_favor=None
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

        # Check if material needs favor to buy
        if mat_result.get('vendors') and player_favor and mat_have < mat_qty:
            vendor_service = get_vendor_service()
            _, needs_favor = vendor_service.check_vendor_favor_from_dicts(
                mat_result['vendors'], player_favor
            )
            mat_result['needs_favor'] = needs_favor
        else:
            mat_result['needs_favor'] = False

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
    """Load vendor item data via VendorService (consolidated)"""
    vendor_service = get_vendor_service()
    return vendor_service.get_vendor_items_as_dicts()


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


@crafting_bp.route('/character_info')
@require_configured
def get_character_info():
    """Get combined character info (skills + favor) for overlay display"""
    from ..utils.constants import FAVOR_LEVELS

    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    skills = char_service.get_skills()
    favor = char_service.get_favor()

    return api_response(data={
        'character': char_service.get_character_name(),
        'skills': skills,
        'favor': favor,
        'favor_levels': FAVOR_LEVELS,
        'source_file': char_service.get_source_file_name(),
        'timestamp': char_service.get_timestamp()
    })


@crafting_bp.route('/characters')
@require_configured
def get_all_characters():
    """Get list of all available characters"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    characters = char_service.get_all_characters()

    return api_response(data={
        'characters': characters
    })


@crafting_bp.route('/characters/<name>')
@require_configured
def get_character_details(name):
    """Get detailed info for a specific character"""
    from ..utils.constants import FAVOR_LEVELS

    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    details = char_service.get_character_details(name)

    if not details:
        return api_error(f"Character '{name}' not found", code="NOT_FOUND", status_code=404)

    # Include favor levels for UI
    details['favor_levels'] = FAVOR_LEVELS

    return api_response(data=details)


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


@crafting_bp.route('/inventory/all')
def get_all_characters_inventory():
    """Get aggregated inventory across all characters with character attribution"""
    try:
        from .decorators import get_tracker_components
        _, _, inventory_parser, _ = get_tracker_components()

        if not inventory_parser:
            return api_response(data={'items': {}, 'characters': []}, message="Inventory parser not initialized")

        # Get aggregated inventory from all characters
        aggregated_items = inventory_parser.parse_all_characters()

        # Get list of characters that have inventory data
        char_files = inventory_parser.get_latest_items_file_per_character()
        characters = list(char_files.keys())

        return api_response(data={
            'items': aggregated_items,
            'characters': characters,
            'item_count': len(aggregated_items)
        })
    except Exception as e:
        logger.error(f"Error loading aggregated inventory: {e}")
        return api_error(str(e), status_code=500)


@crafting_bp.route('/ready_recipes')
def get_ready_recipes():
    """Get all recipes that are ready to craft or buyable (have all materials, can craft, or can buy with favor)"""
    config = get_config()

    # Get player skills and favor
    char_service = CharacterService(config.get_reports_dir())
    player_skills = char_service.get_effective_skill_levels()
    player_favor = char_service.get_favor()

    # Load recipes via ItemResolutionService (consolidated, cached)
    item_resolution = get_item_resolution_service()
    all_recipes = item_resolution.get_all_recipes()

    if not all_recipes:
        return api_response(data={'recipes': []})

    # Get recipes-by-output lookup from ItemResolutionService (consolidated)
    recipes_by_output = item_resolution.get_recipes_by_output()

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
    vendor_service = get_vendor_service()

    # Check each recipe for readiness
    ready_recipes = []

    for idx, recipe in enumerate(all_recipes):
        recipe_skill = recipe.get('skill', '')
        recipe_level = recipe.get('level', 0)
        player_level = player_skills.get(recipe_skill, 0)

        # Skip if player lacks skill
        if player_level < recipe_level:
            continue

        # Check all ingredients using same logic as main UI
        all_ready = True  # All materials available (in storage or craftable)
        has_gather = False  # Any ingredient requires gathering
        has_buy = False  # Any ingredient requires buying (with favor)
        has_buy_needs_favor = False  # Any ingredient needs more favor to buy
        materials = []

        for ingredient in recipe.get('ingredients', []):
            mat_name = ingredient.get('item') or ingredient.get('name', 'Unknown')
            mat_qty = ingredient.get('quantity', 1)
            mat_have = player_inventory.get(mat_name, 0)

            # Get storage details
            details = inventory_details.get(mat_name, {})
            in_inventory = details.get('in_inventory', 0) if isinstance(details, dict) else 0
            in_storage = 0
            storage_locations = {}

            if isinstance(details, dict):
                for k, v in details.items():
                    if k not in ['total', 'in_inventory'] and isinstance(v, (int, float)) and v > 0:
                        in_storage += v
                        storage_locations[k] = v

            mat_result = {
                'name': mat_name,
                'need': mat_qty,
                'have': min(mat_have, mat_qty),
                'in_inventory': in_inventory,
                'in_storage': in_storage,
                'storage_locations': storage_locations
            }
            materials.append(mat_result)

            if mat_have >= mat_qty:
                # Have enough in storage
                continue

            # Missing items - categorize them
            missing = mat_qty - mat_have

            # Check if craftable
            can_craft, _ = _can_craft_item(
                mat_name, missing,
                player_inventory, player_skills,
                recipes_by_output
            )
            if can_craft:
                # Can craft with available materials - still "ready"
                continue

            # Check if buyable from vendor
            if mat_name in vendor_items:
                # Check favor
                has_favor, _ = vendor_service.check_vendor_favor_from_dicts(
                    vendor_items[mat_name], player_favor
                )
                if has_favor:
                    has_buy = True
                    all_ready = False
                else:
                    has_buy_needs_favor = True
                    all_ready = False
            else:
                # Must gather
                has_gather = True
                all_ready = False

        # Apply same hierarchy as main UI:
        # - craftable: all materials ready (green)
        # - buyable: all missing can be bought with current favor, no gather needed (orange)
        # Include both in ready recipes
        is_craftable = all_ready
        is_buyable = not has_gather and not has_buy_needs_favor and has_buy

        if is_craftable or is_buyable:
            recipe_id = f"{recipe.get('skill', 'Unknown')}_{recipe.get('name', 'Unknown')}_{idx}"
            status = 'ready' if is_craftable else 'buyable'
            ready_recipes.append({
                'id': recipe_id,
                'name': recipe.get('name', 'Unknown'),
                'skill': recipe_skill,
                'level': recipe_level,
                'quantity': 1,
                'materials': materials,
                'status': status
            })

    return api_response(data={'recipes': ready_recipes})
