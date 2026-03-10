"""
Game data API routes (items, vendors, keywords, recipes)
"""

import logging
from flask import Blueprint

from config import get_config
from ..utils.responses import api_response, api_error
from ..utils.paths import get_bundled_path
from ..utils.security import safe_read_json
from ..services.cache_service import get_cache

logger = logging.getLogger(__name__)

data_bp = Blueprint('data', __name__)


@data_bp.route('/recipes.json')
def get_recipes():
    """Serve recipes.json file for crafting tab"""
    recipes_file = get_bundled_path('recipes.json')
    if not recipes_file.exists():
        return api_error("Recipes file not found", status_code=404)

    cache = get_cache()
    recipes = cache.get_or_compute(
        'recipes:all',
        lambda: safe_read_json(recipes_file),
        ttl=60.0,
        file_path=recipes_file
    )

    # Return raw JSON array for backwards compatibility
    from flask import jsonify
    return jsonify(recipes)


@data_bp.route('/items')
def get_items_index():
    """Get global item index with game data, vendor info, and crafting recipes"""
    cache = get_cache()

    # Try to get from cache
    cached = cache.get('items:index')
    if cached:
        return api_response(data=cached)

    items_file = get_bundled_path('items.json')
    recipes_file = get_bundled_path('recipes.json')
    vendor_file = get_bundled_path('vendor_inventory.json')

    # Load items database
    items = {}
    if items_file.exists():
        items = safe_read_json(items_file)

    # Load recipes and index by output item
    recipes_by_item = {}
    if recipes_file.exists():
        recipes = safe_read_json(recipes_file)
        for recipe in recipes:
            output_name = recipe.get('name', '')
            if output_name not in recipes_by_item:
                recipes_by_item[output_name] = []
            recipes_by_item[output_name].append({
                'id': recipe.get('id'),
                'skill': recipe.get('skill'),
                'level': recipe.get('level'),
                'ingredients': recipe.get('ingredients', [])
            })

    # Load vendor data
    vendors_by_item = {}
    if vendor_file.exists():
        vendor_data = safe_read_json(vendor_file)
        for vendor_name, vendor_info in vendor_data.items():
            for item_name in vendor_info.get('items', []):
                if item_name not in vendors_by_item:
                    vendors_by_item[item_name] = []
                vendors_by_item[item_name].append({
                    'vendor': vendor_name,
                    'location': vendor_info.get('location', 'Unknown')
                })

    # Build combined index
    item_index = {}
    for item_id, item_data in items.items():
        name = item_data.get('Name', 'Unknown')
        item_index[name] = {
            'id': item_id,
            'internal_name': item_data.get('InternalName', ''),
            'description': item_data.get('Description', ''),
            'value': item_data.get('Value', 0),
            'keywords': item_data.get('Keywords', []),
            'max_stack': item_data.get('MaxStackSize', 1),
            'icon_id': item_data.get('IconId'),
            'crafted_by': recipes_by_item.get(name, []),
            'sold_by': vendors_by_item.get(name, [])
        }

    result = {
        'items': item_index,
        'item_count': len(item_index)
    }

    # Cache for 60 seconds
    cache.set('items:index', result, ttl=60.0)

    return api_response(data=result)


@data_bp.route('/vendors')
def get_vendor_items():
    """Get items available from vendors"""
    vendor_file = get_bundled_path('vendor_inventory.json')

    if not vendor_file.exists():
        return api_response(data={'vendor_items': {}}, message="Vendor file not found")

    vendor_data = safe_read_json(vendor_file)

    # Build item -> vendor info mapping
    vendor_items = {}
    vendors = vendor_data.get('vendors', {})

    for vendor_name, vendor_info in vendors.items():
        location = vendor_info.get('location', 'Unknown')
        items = vendor_info.get('items', {})

        for item_name, item_info in items.items():
            if item_name not in vendor_items:
                vendor_items[item_name] = []
            vendor_items[item_name].append({
                'vendor': vendor_name,
                'location': location,
                'price': item_info.get('price', 0),
                'favor': item_info.get('favor', 'Unknown')
            })

    return api_response(data={
        'vendor_items': vendor_items,
        'item_count': len(vendor_items)
    })


@data_bp.route('/keywords')
def get_item_keywords():
    """Get keyword to item mappings for ingredient matching"""
    items_file = get_bundled_path('items.json')

    if not items_file.exists():
        return api_response(data={'keywords': {}}, message="Items file not found")

    cache = get_cache()
    cached = cache.get('keywords:map')
    if cached:
        return api_response(data=cached)

    items = safe_read_json(items_file)

    # Build keyword -> item names mapping
    keyword_map = {}
    for item_id, item_data in items.items():
        display_name = item_data.get('Name', '')
        if not display_name:
            continue

        for keyword in item_data.get('Keywords', []):
            # Normalize keyword by removing "=value" suffix
            normalized_keyword = keyword.split('=')[0]
            if normalized_keyword not in keyword_map:
                keyword_map[normalized_keyword] = []
            if display_name not in keyword_map[normalized_keyword]:
                keyword_map[normalized_keyword].append(display_name)

    result = {
        'keywords': keyword_map,
        'keyword_count': len(keyword_map)
    }

    cache.set('keywords:map', result, ttl=60.0)

    return api_response(data=result)


@data_bp.route('/update_data', methods=['POST'])
def update_game_data():
    """Manually download latest game data from CDN"""
    from data_updater import download_file, QUEST_DATA_URL, ITEMS_DATA_URL

    config = get_config()
    base_dir = config.get_base_dir()

    success = True
    messages = []

    quests_file = base_dir / 'quests.json'
    items_file = base_dir / 'items.json'

    # Download quests
    if download_file(QUEST_DATA_URL, quests_file):
        messages.append("Downloaded quests.json")
    else:
        messages.append("Failed to download quests.json")
        success = False

    # Download items
    if download_file(ITEMS_DATA_URL, items_file):
        messages.append("Downloaded items.json")
    else:
        messages.append("Failed to download items.json")
        success = False

    # Invalidate caches
    cache = get_cache()
    cache.invalidate_prefix('items:')
    cache.invalidate_prefix('keywords:')

    if success:
        return api_response(data={'messages': messages}, message="Game data updated")
    else:
        return api_error(
            "Some downloads failed",
            details={'messages': messages},
            status_code=500
        )
