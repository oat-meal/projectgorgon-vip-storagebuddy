"""
Quest-related API routes
"""

import logging
from flask import Blueprint, request, g

from config import get_config
from ..utils.responses import api_response, api_error, not_found
from ..utils.validation import validate_search_query, ValidationError
from ..utils.constants import MAX_SEARCH_RESULTS
from ..services.character_service import CharacterService
from ..services.vendor_service import get_vendor_service
from ..services.item_resolution_service import get_item_resolution_service
from .decorators import require_configured

logger = logging.getLogger(__name__)

quests_bp = Blueprint('quests', __name__)


@quests_bp.route('/active_quests')
@require_configured
def get_active_quests():
    """Get list of active quests from character data"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    # Get optional character filter from query parameter
    character_name = request.args.get('character')

    active_quest_internals = char_service.get_active_quests(character_name)
    if not active_quest_internals:
        return api_response(data={'quests': []})

    # Get quest details (exclude guild quests and quests without collect objectives)
    active_quests = []
    for quest_internal in active_quest_internals:
        quest = g.quest_db.get_quest(quest_internal)
        if quest and not quest.is_guild_quest() and quest.has_collect_objectives():
            active_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return api_response(data={'quests': active_quests})


@quests_bp.route('/quest/<quest_internal_name>')
@require_configured
def get_quest_checklist(quest_internal_name):
    """Get checklist for a specific quest"""
    checklist = g.tracker.get_quest_checklist(quest_internal_name)

    if not checklist:
        return not_found(f"Quest '{quest_internal_name}' not found")

    # Update from chat log
    log_file = g.chat_parser.get_latest_log_file()
    if log_file:
        g.tracker.update_checklist_from_log(checklist, log_file)

    # Get current character from query param
    current_character = request.args.get('character')

    # Add multi-character favor checking for items that need favor
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())
    all_characters_favor = char_service.get_all_characters_favor()
    vendor_service = get_vendor_service()

    for item in checklist.get('items', []):
        # Check if item needs favor (has vendor_data but isn't completed)
        if item.get('vendor_data') and not item.get('completed', False):
            favor_result = vendor_service.check_vendor_favor_all_characters_from_dicts(
                item['vendor_data'],
                all_characters_favor,
                current_character
            )

            item['favor_check'] = {
                'can_buy': favor_result['can_buy'],
                'current_can_buy': favor_result['current_can_buy'],
                'buyer': favor_result['buyer'],
                'buyer_favor': favor_result['buyer_favor'],
                'vendor_name': favor_result['vendor_name'],
                'required_favor': favor_result['required_favor']
            }

    return api_response(data=checklist)


@quests_bp.route('/search_quests')
@require_configured
def search_quests():
    """Search for quests by name"""
    try:
        query = validate_search_query(request.args.get('q', ''))
    except ValidationError as e:
        return api_error(e.message, code="VALIDATION_ERROR", status_code=400)

    if len(query) < 2:
        return api_response(data={'quests': []})

    query_lower = query.lower()
    matching_quests = []

    for quest in g.quest_db.quests.values():
        if query_lower in quest.name.lower():
            if not quest.is_guild_quest() and quest.has_collect_objectives():
                matching_quests.append({
                    'internal_name': quest.internal_name,
                    'name': quest.name,
                    'location': quest.displayed_location or 'Unknown'
                })

                if len(matching_quests) >= MAX_SEARCH_RESULTS:
                    break

    return api_response(data={'quests': matching_quests})


@quests_bp.route('/completable_quests')
@require_configured
def get_completable_quests():
    """Get list of quests that can be completed right now"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    # Get optional character filter from query parameter
    character_name = request.args.get('character')

    active_quest_internals = char_service.get_active_quests(character_name)
    if not active_quest_internals:
        return api_response(data={'quests': []})

    log_file = g.chat_parser.get_latest_log_file()
    completable_quests = []

    for quest_internal in active_quest_internals:
        quest = g.quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        checklist = g.tracker.get_quest_checklist(quest_internal)
        if log_file:
            g.tracker.update_checklist_from_log(checklist, log_file)

        if checklist.get('is_completable', False):
            completable_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return api_response(data={'quests': completable_quests})


@quests_bp.route('/purchasable_quests')
@require_configured
def get_purchasable_quests():
    """Get list of quests that can be completed by buying items"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    # Get optional character filter from query parameter
    character_name = request.args.get('character')

    active_quest_internals = char_service.get_active_quests(character_name)
    if not active_quest_internals:
        return api_response(data={'quests': []})

    log_file = g.chat_parser.get_latest_log_file()
    purchasable_quests = []

    for quest_internal in active_quest_internals:
        quest = g.quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        checklist = g.tracker.get_quest_checklist(quest_internal)
        if log_file:
            g.tracker.update_checklist_from_log(checklist, log_file)

        if checklist.get('is_purchasable', False):
            purchasable_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return api_response(data={'quests': purchasable_quests})


@quests_bp.route('/needs_favor_quests')
@require_configured
def get_needs_favor_quests():
    """Get list of quests where items are buyable but player lacks favor"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    # Get optional character filter from query parameter
    character_name = request.args.get('character')

    active_quest_internals = char_service.get_active_quests(character_name)
    if not active_quest_internals:
        return api_response(data={'quests': []})

    # Get player data for resolution
    player_favor = char_service.get_favor()
    player_skills = char_service.get_effective_skill_levels()

    # Get inventory data
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
        logger.warning(f"Could not load inventory for needs_favor check: {e}")

    item_resolver = get_item_resolution_service()
    log_file = g.chat_parser.get_latest_log_file()
    needs_favor_quests = []

    for quest_internal in active_quest_internals:
        quest = g.quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        checklist = g.tracker.get_quest_checklist(quest_internal)
        if log_file:
            g.tracker.update_checklist_from_log(checklist, log_file)

        # Skip if already completable or purchasable
        if checklist.get('is_completable', False) or checklist.get('is_purchasable', False):
            continue

        # Check if any missing item needs favor
        has_needs_favor = False
        for item in checklist.get('items', []):
            item_name = item['display_name']
            required = item['required']

            resolution = item_resolver.resolve_item(
                item_name,
                required,
                player_inventory,
                inventory_details,
                player_skills,
                player_favor
            )

            # Item needs favor if: missing, buyable, but favor not met
            if resolution.quantity_missing > 0 and resolution.is_buyable and resolution.needs_favor:
                has_needs_favor = True
                break

        if has_needs_favor:
            needs_favor_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return api_response(data={'quests': needs_favor_quests})


@quests_bp.route('/overlay_data')
@require_configured
def overlay_data():
    """Get simplified quest data for overlay display"""
    view = request.args.get('view', 'completable')
    character_name = request.args.get('character')

    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    active_quest_internals = char_service.get_active_quests(character_name)
    if not active_quest_internals:
        return api_response(data={'quests': []})

    # Get player data for resolution
    player_favor = char_service.get_favor()
    player_skills = char_service.get_effective_skill_levels()

    # Get AGGREGATED inventory data from all characters
    player_inventory = {}
    inventory_details = {}
    try:
        from .decorators import get_tracker_components
        _, _, inventory_parser, _ = get_tracker_components()
        if inventory_parser:
            # Use aggregated inventory from all characters
            aggregated = inventory_parser.parse_all_characters()
            for item_name, agg_data in aggregated.items():
                # Calculate totals across all characters
                total_inventory = 0
                total_storage = 0
                combined_storage = {}

                for char_name, char_data in agg_data.get('byCharacter', {}).items():
                    char_inv = char_data.get('inventory', 0)
                    total_inventory += char_inv
                    # Treat inventory as a storage location with character name prefix
                    if char_inv > 0:
                        inv_key = f"{char_name}: Inventory"
                        combined_storage[inv_key] = combined_storage.get(inv_key, 0) + char_inv
                    char_storage = char_data.get('storage', {})
                    for loc, count in char_storage.items():
                        # Include character name in storage location
                        loc_key = f"{char_name}: {loc}"
                        combined_storage[loc_key] = combined_storage.get(loc_key, 0) + count
                        total_storage += count

                player_inventory[item_name] = total_inventory + total_storage
                inventory_details[item_name] = {
                    'total': total_inventory + total_storage,
                    'inventory': total_inventory,
                    'storage': combined_storage
                }
    except Exception as e:
        logger.warning(f"Could not load inventory for quest resolution: {e}")

    # Get item resolution service
    item_resolver = get_item_resolution_service()

    # Get multi-character favor for vendor checking
    all_characters_favor = char_service.get_all_characters_favor()
    vendor_service = get_vendor_service()

    log_file = g.chat_parser.get_latest_log_file()
    simplified_quests = []

    for quest_internal in active_quest_internals:
        quest = g.quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        checklist = g.tracker.get_quest_checklist(quest_internal)
        if log_file:
            g.tracker.update_checklist_from_log(checklist, log_file)

        # Filter by view type
        include_quest = False
        if view == 'completable' and checklist.get('is_completable', False):
            include_quest = True
        elif view == 'purchasable' and checklist.get('is_purchasable', False):
            include_quest = True
        elif view == 'active':
            include_quest = True

        if not include_quest:
            continue

        simplified_quest = {
            'internal_name': quest_internal,
            'name': quest.name,
            'location': quest.displayed_location or 'Unknown',
            'turn_in_npc': quest.turn_in_npc,
            'is_completable': checklist.get('is_completable', False),
            'is_purchasable': checklist.get('is_purchasable', False),
            'items': []
        }

        for item in checklist.get('items', []):
            item_name = item['display_name']
            required = item['required']

            # Use ItemResolutionService to get full resolution
            resolution = item_resolver.resolve_item(
                item_name,
                required,
                player_inventory,
                inventory_details,
                player_skills,
                player_favor
            )

            # Build vendor_info as formatted string from possible_vendors
            vendor_info_str = None
            vendor_data = item.get('possible_vendors', [])
            if vendor_data:
                v = vendor_data[0]
                # Handle both dict and string formats for vendor data
                if isinstance(v, dict):
                    vendor_name = v.get('vendor') or v.get('name', 'Unknown')
                    vendor_info_str = f"{vendor_name} ({v.get('location', 'Unknown')}) - {v.get('favor', 'Unknown')}"
                elif isinstance(v, str):
                    # Some vendor data may be pre-formatted strings
                    vendor_info_str = v

            # Check multi-character favor for vendor purchases
            favor_check = None
            # Filter vendor_data to only include dicts (some may be pre-formatted strings)
            vendor_dicts = [v for v in vendor_data if isinstance(v, dict)]
            if vendor_dicts and not item.get('completed', False):
                favor_result = vendor_service.check_vendor_favor_all_characters_from_dicts(
                    vendor_dicts,
                    all_characters_favor,
                    None  # No current character context in overlay
                )
                favor_check = {
                    'can_buy': favor_result['can_buy'],
                    'buyer': favor_result['buyer'],
                    'buyer_favor': favor_result['buyer_favor'],
                    'vendor_name': favor_result['vendor_name'],
                    'required_favor': favor_result['required_favor']
                }

            # Build item data with crafting info
            item_data = {
                'name': item_name,
                'have': resolution.quantity_have,
                'need': required,
                'missing': resolution.quantity_missing,
                'in_inventory': resolution.in_inventory,
                'in_storage': resolution.in_storage,
                'storage_locations': resolution.storage_locations,
                'source': resolution.source,
                # Vendor info as formatted string
                'vendor_info': vendor_info_str,
                'is_buyable': resolution.is_buyable,
                'needs_favor': resolution.needs_favor,
                'favor_met': resolution.favor_met,
                # Multi-character favor check
                'favor_check': favor_check,
                # Crafting info
                'is_craftable': resolution.is_craftable,
                'recipe_id': resolution.recipe_id
            }

            # Add recipe details if craftable
            if resolution.recipe_info:
                item_data['recipe'] = {
                    'id': resolution.recipe_info.recipe_id,
                    'name': resolution.recipe_info.recipe_name,
                    'skill': resolution.recipe_info.skill,
                    'level': resolution.recipe_info.level,
                    'has_skill': resolution.recipe_info.has_skill,
                    'skill_gap': resolution.recipe_info.skill_gap,
                    'crafts_needed': resolution.recipe_info.crafts_needed,
                    'ingredients': resolution.recipe_info.ingredients
                }

            simplified_quest['items'].append(item_data)

        simplified_quests.append(simplified_quest)

    return api_response(data={'quests': simplified_quests})


@quests_bp.route('/log_status')
@require_configured
def get_log_status():
    """Get status of chat log monitoring"""
    log_file = g.chat_parser.get_latest_log_file()

    if not log_file:
        return api_response(data={
            'status': 'error',
            'message': 'No chat log files found'
        })

    return api_response(data={
        'status': 'ok',
        'log_file': log_file.name,
        'last_modified': log_file.stat().st_mtime
    })
