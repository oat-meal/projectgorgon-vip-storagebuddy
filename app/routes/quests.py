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
from .decorators import require_configured

logger = logging.getLogger(__name__)

quests_bp = Blueprint('quests', __name__)


@quests_bp.route('/active_quests')
@require_configured
def get_active_quests():
    """Get list of active quests from character data"""
    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    active_quest_internals = char_service.get_active_quests()
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

    active_quest_internals = char_service.get_active_quests()
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

    active_quest_internals = char_service.get_active_quests()
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


@quests_bp.route('/overlay_data')
@require_configured
def overlay_data():
    """Get simplified quest data for overlay display"""
    view = request.args.get('view', 'completable')

    config = get_config()
    char_service = CharacterService(config.get_reports_dir())

    active_quest_internals = char_service.get_active_quests()
    if not active_quest_internals:
        return api_response(data={'quests': []})

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
            'items': []
        }

        for item in checklist.get('items', []):
            total_have = item.get('in_inventory', 0) + item.get('in_storage', 0)
            simplified_quest['items'].append({
                'name': item['display_name'],
                'have': total_have,
                'need': item['required'],
                'in_inventory': item.get('in_inventory', 0),
                'in_storage': item.get('in_storage', 0),
                'storage_locations': item.get('storage_locations', {}),
                'vendor_info': item.get('vendor_info')
            })

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
