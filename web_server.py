#!/usr/bin/env python3
"""
Project Gorgon VIP StorageBuddy - Web Server
Flask-based web interface for quest tracking, inventory management, and crafting
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pathlib import Path
import json
import sys
import os
import logging
import traceback
import argparse
from datetime import datetime
from quest_parser import QuestDatabase, ChatLogParser, QuestTracker, InventoryParser
from config import get_config
from data_updater import ensure_quest_data
from version import __version__


def get_bundled_path(relative_path):
    """Get the path to a bundled resource (works for PyInstaller and normal execution)"""
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running as normal Python script
        base_path = Path(__file__).parent
    return base_path / relative_path

# Parse command-line arguments (only parse known args to allow launcher.py args like --overlay)
parser = argparse.ArgumentParser(description='Project Gorgon VIP Quest Helper')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args, unknown = parser.parse_known_args()

app = Flask(__name__)

# Enable CORS for browser extension access
CORS(app, resources={r"/api/*": {"origins": ["moz-extension://*", "chrome-extension://*"]}})

# In-memory store for recipe selections (synced from web app localStorage)
recipe_selections = {}

# Initialize configuration
config = get_config()
base_dir = config.get_base_dir()

# Set up logging to file (level based on --debug flag)
log_file = base_dir / 'questhelper.log'
log_level = logging.DEBUG if args.debug else logging.INFO

logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),  # Overwrite on each start
        logging.StreamHandler(sys.stdout)  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

logger.info("=" * 80)
logger.info(f"Quest Helper Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info("=" * 80)
logger.info(f"Log level: {'DEBUG' if args.debug else 'INFO'}")
logger.info(f"Log file location: {log_file}")
logger.info(f"Version: {__version__}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Running as executable: {getattr(sys, 'frozen', False)}")
logger.info(f"Data directory: {base_dir}")

# Ensure quest data files exist (copy from bundle or download if needed)
bundled_dir = config.get_bundled_resource_dir()
if bundled_dir:
    logger.info(f"Bundled resource directory: {bundled_dir}")
    logger.info(f"  quests.json exists: {(bundled_dir / 'quests.json').exists()}")
    logger.info(f"  items.json exists: {(bundled_dir / 'items.json').exists()}")
else:
    logger.info("No bundled resources found (running from source)")

if not ensure_quest_data(base_dir, bundled_dir):
    logger.warning("Failed to obtain game data files")
    logger.warning("The Quest Helper may not work correctly")
    logger.warning("Please check your internet connection and try again")
else:
    logger.info(f"Game data loaded from {base_dir}")
    logger.info(f"  quests.json: {(base_dir / 'quests.json').stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"  items.json: {(base_dir / 'items.json').stat().st_size / 1024 / 1024:.1f} MB")

config_status = config.get_status()
logger.info(f"Configuration status: {config_status}")

# Initialize quest tracker only if configured
quest_db = None
chat_parser = None
inventory_parser = None
tracker = None

def initialize_tracker():
    """Initialize quest tracker components"""
    global quest_db, chat_parser, inventory_parser, tracker

    config_status = config.get_status()
    if not config_status['configured']:
        return False

    chat_log_dir = config.get_chat_log_dir()
    reports_dir = config.get_reports_dir()

    logger.info(f"Using game data from: {config.config.get('detected_path', 'custom configuration')}")
    logger.info(f"  Chat logs: {chat_log_dir}")
    logger.info(f"  Reports: {reports_dir}")

    try:
        quest_db = QuestDatabase(
            base_dir / 'quests.json',
            base_dir / 'items.json'
        )
        logger.info("QuestDatabase initialized successfully")

        chat_parser = ChatLogParser(chat_log_dir)
        logger.info("ChatLogParser initialized successfully")

        inventory_parser = InventoryParser(reports_dir)
        logger.info("InventoryParser initialized successfully")

        tracker = QuestTracker(quest_db, chat_parser, inventory_parser)
        logger.info("QuestTracker initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing quest tracker: {e}")
        logger.error(traceback.format_exc())
        return False

if config_status['configured']:
    logger.info("App is configured, initializing quest tracker...")
    initialize_tracker()
else:
    logger.info("Quest Helper starting in setup mode")
    logger.info("User needs to complete setup at http://127.0.0.1:5000/setup")


# Flask request/response logging
@app.before_request
def log_request():
    logger.info(f">>> {request.method} {request.path}")
    if request.args:
        logger.info(f"    Query params: {dict(request.args)}")
    if request.is_json:
        logger.info(f"    JSON body: {request.get_json()}")


@app.after_request
def log_response(response):
    logger.info(f"<<< {response.status_code} {request.method} {request.path}")
    return response


# Error handler for all exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception in {request.method} {request.path}")
    logger.error(f"Exception type: {type(e).__name__}")
    logger.error(f"Exception message: {str(e)}")
    logger.error(f"Full traceback:\n{traceback.format_exc()}")

    # Return JSON error for API endpoints
    if request.path.startswith('/api/'):
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'type': type(e).__name__
        }), 500

    # Return HTML error for regular pages
    return f"<h1>Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", 500


def require_configured(f):
    """Decorator to ensure app is configured before accessing quest data"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not config.get_status()['configured']:
            return jsonify({
                'error': 'App not configured',
                'message': 'Please complete setup at /setup before accessing quest data'
            }), 503

        # Initialize tracker if not already initialized
        if quest_db is None or chat_parser is None or tracker is None:
            logger.info("Tracker not initialized, initializing now...")
            if not initialize_tracker():
                return jsonify({
                    'error': 'Failed to initialize quest tracker',
                    'message': 'Check debug log for details'
                }), 500

        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    """Main page"""
    # Redirect to setup if not configured
    if not config.get_status()['configured']:
        from flask import redirect
        return redirect('/setup')
    return render_template('index.html')


@app.route('/setup')
def setup():
    """Setup wizard page"""
    return render_template('setup.html')


@app.route('/overlay')
def overlay():
    """Overlay mode for in-game display"""
    return render_template('overlay.html')


@app.route('/api/active_quests')
@require_configured
def get_active_quests():
    """Get list of active quests from character data"""
    # Find the most recent character file
    reports_dir = config.get_reports_dir()
    report_files = list(reports_dir.glob('Character_*.json'))
    if not report_files:
        return jsonify({'error': 'No character data found'}), 404

    latest_char_file = max(report_files, key=lambda p: p.stat().st_mtime)

    with open(latest_char_file, 'r') as f:
        char_data = json.load(f)

    active_quest_internals = char_data.get('ActiveQuests', [])

    # Get quest names (exclude guild quests and quests without collect objectives)
    active_quests = []
    for quest_internal in active_quest_internals:
        quest = quest_db.get_quest(quest_internal)
        if quest and not quest.is_guild_quest() and quest.has_collect_objectives():
            active_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return jsonify({'quests': active_quests})


@app.route('/api/quest/<quest_internal_name>')
@require_configured
def get_quest_checklist(quest_internal_name):
    """Get checklist for a specific quest"""
    checklist = tracker.get_quest_checklist(quest_internal_name)

    if not checklist:
        return jsonify({'error': 'Quest not found'}), 404

    # Update from chat log
    log_file = chat_parser.get_latest_log_file()
    if log_file:
        tracker.update_checklist_from_log(checklist, log_file)

    return jsonify(checklist)


@app.route('/api/search_quests')
@require_configured
def search_quests():
    """Search for quests by name"""
    query = request.args.get('q', '').lower()

    if len(query) < 2:
        return jsonify({'quests': []})

    matching_quests = []
    for quest in quest_db.quests.values():
        if query in quest.name.lower() and not quest.is_guild_quest() and quest.has_collect_objectives():
            matching_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    # Limit results
    matching_quests = matching_quests[:20]

    return jsonify({'quests': matching_quests})


@app.route('/api/completable_quests')
@require_configured
def get_completable_quests():
    """Get list of quests that can be completed right now"""
    # Find the most recent character file
    reports_dir = config.get_reports_dir()
    report_files = list(reports_dir.glob('Character_*.json'))
    if not report_files:
        return jsonify({'quests': []})

    latest_char_file = max(report_files, key=lambda p: p.stat().st_mtime)

    with open(latest_char_file, 'r') as f:
        char_data = json.load(f)

    active_quest_internals = char_data.get('ActiveQuests', [])

    # Check each quest for completability
    completable_quests = []
    log_file = chat_parser.get_latest_log_file()

    for quest_internal in active_quest_internals:
        quest = quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        # Get checklist and update from inventory
        checklist = tracker.get_quest_checklist(quest_internal)
        if log_file:
            tracker.update_checklist_from_log(checklist, log_file)

        # Add to completable list if ready
        if checklist.get('is_completable', False):
            completable_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return jsonify({'quests': completable_quests})


@app.route('/api/purchasable_quests')
@require_configured
def get_purchasable_quests():
    """Get list of quests that can be completed by buying items"""
    # Find the most recent character file
    reports_dir = config.get_reports_dir()
    report_files = list(reports_dir.glob('Character_*.json'))
    if not report_files:
        return jsonify({'quests': []})

    latest_char_file = max(report_files, key=lambda p: p.stat().st_mtime)

    with open(latest_char_file, 'r') as f:
        char_data = json.load(f)

    active_quest_internals = char_data.get('ActiveQuests', [])

    # Check each quest for purchasability
    purchasable_quests = []
    log_file = chat_parser.get_latest_log_file()

    for quest_internal in active_quest_internals:
        quest = quest_db.get_quest(quest_internal)
        if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
            continue

        # Get checklist and update from inventory
        checklist = tracker.get_quest_checklist(quest_internal)
        if log_file:
            tracker.update_checklist_from_log(checklist, log_file)

        # Add to purchasable list if items can be bought
        if checklist.get('is_purchasable', False):
            purchasable_quests.append({
                'internal_name': quest.internal_name,
                'name': quest.name,
                'location': quest.displayed_location or 'Unknown'
            })

    return jsonify({'quests': purchasable_quests})


@app.route('/api/log_status')
@require_configured
def get_log_status():
    """Get status of chat log monitoring"""
    log_file = chat_parser.get_latest_log_file()

    if not log_file:
        return jsonify({
            'status': 'error',
            'message': 'No chat log files found'
        })

    return jsonify({
        'status': 'ok',
        'log_file': log_file.name,
        'last_modified': log_file.stat().st_mtime
    })


@app.route('/api/config_status')
def get_config_status():
    """Get configuration status for troubleshooting"""
    return jsonify(config.get_status())


@app.route('/api/auto_detect', methods=['POST'])
def auto_detect_paths():
    """Try to auto-detect game data paths"""
    logger.info("Auto-detect requested")
    logger.info(f"Platform: {platform.system()}")

    detected = config._auto_detect_game_data()

    if detected:
        logger.info(f"Auto-detect succeeded: {detected['detected_path']}")

        # Save the detected paths
        config.config.update(detected)
        config._save_config()

        # Get stats about what was found
        chat_dir = Path(detected['chat_log_dir'])
        reports_dir = Path(detected['reports_dir'])

        chat_log_count = len(list(chat_dir.glob('Chat-*.log')))
        character_files_count = len(list(reports_dir.glob('Character_*.json')))

        logger.info(f"  Chat logs: {chat_dir} ({chat_log_count} files)")
        logger.info(f"  Reports: {reports_dir} ({character_files_count} files)")

        return jsonify({
            'success': True,
            'detected_path': detected['detected_path'],
            'chat_log_dir': str(chat_dir),
            'reports_dir': str(reports_dir),
            'chat_log_count': chat_log_count,
            'character_files_count': character_files_count
        })
    else:
        logger.warning("Auto-detect failed: Could not find Project Gorgon game data")
        logger.warning(f"Searched paths: {config._get_search_paths()}")
        return jsonify({
            'success': False,
            'error': 'Could not find Project Gorgon game data in common locations'
        })


@app.route('/api/save_config', methods=['POST'])
def save_configuration():
    """Save custom configuration from user"""
    data = request.get_json()

    chat_log_dir = data.get('chat_log_dir', '').strip()
    reports_dir = data.get('reports_dir', '').strip()

    if not chat_log_dir or not reports_dir:
        return jsonify({
            'success': False,
            'error': 'Both paths are required'
        })

    try:
        config.set_custom_paths(chat_log_dir, reports_dir)
        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully'
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/version')
def get_version():
    """Get application version"""
    return jsonify({
        'version': __version__,
        'frozen': getattr(sys, 'frozen', False),
        'log_file': str(log_file)
    })


@app.route('/api/update_data', methods=['POST'])
def update_game_data():
    """Manually download latest game data from CDN"""
    from data_updater import download_file, QUEST_DATA_URL, ITEMS_DATA_URL

    success = True
    messages = []

    quests_file = base_dir / 'quests.json'
    items_file = base_dir / 'items.json'

    # Download quests
    if download_file(QUEST_DATA_URL, quests_file):
        messages.append("✓ Downloaded quests.json")
    else:
        messages.append("✗ Failed to download quests.json")
        success = False

    # Download items
    if download_file(ITEMS_DATA_URL, items_file):
        messages.append("✓ Downloaded items.json")
    else:
        messages.append("✗ Failed to download items.json")
        success = False

    return jsonify({
        'success': success,
        'messages': messages
    })


@app.route('/api/overlay_data')
@require_configured
def overlay_data():
    """Get simplified quest data for overlay display"""
    view = request.args.get('view', 'completable')  # completable, purchasable, or active

    try:
        # Find the most recent character file
        reports_dir = config.get_reports_dir()
        report_files = list(reports_dir.glob('Character_*.json'))
        if not report_files:
            return jsonify({'quests': []})

        latest_char_file = max(report_files, key=lambda p: p.stat().st_mtime)

        with open(latest_char_file, 'r') as f:
            char_data = json.load(f)

        active_quest_internals = char_data.get('ActiveQuests', [])
        log_file = chat_parser.get_latest_log_file()

        # Filter quests based on view type
        simplified_quests = []
        for quest_internal in active_quest_internals:
            quest = quest_db.get_quest(quest_internal)
            if not quest or quest.is_guild_quest() or not quest.has_collect_objectives():
                continue

            # Get checklist and update from inventory
            checklist = tracker.get_quest_checklist(quest_internal)
            if log_file:
                tracker.update_checklist_from_log(checklist, log_file)

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

            # Simplify data for overlay - only include quest name and items with progress
            simplified_quest = {
                'name': quest.name,
                'items': []
            }

            for item in checklist.get('items', []):
                # Calculate total items available (inventory + storage)
                total_have = item.get('in_inventory', 0) + item.get('in_storage', 0)
                simplified_quest['items'].append({
                    'name': item['display_name'],
                    'have': total_have,
                    'need': item['required'],
                    'in_inventory': item.get('in_inventory', 0),
                    'in_storage': item.get('in_storage', 0),
                    'storage_locations': item.get('storage_locations', {})
                })

            simplified_quests.append(simplified_quest)

        return jsonify({'quests': simplified_quests})
    except Exception as e:
        logger.error(f"Error getting overlay data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/shopping_list', methods=['GET', 'POST'])
def shopping_list():
    """Get or update shopping list for selected recipes (for browser extension)"""
    global inventory_parser, recipe_selections

    if request.method == 'POST':
        # Update recipe selections from web app
        try:
            data = request.get_json()
            recipe_selections.clear()
            recipe_selections.update(data.get('recipes', {}))
            return jsonify({'success': True, 'count': len(recipe_selections)})
        except Exception as e:
            logger.error(f"Error updating recipe selections: {e}")
            return jsonify({'error': str(e)}), 400

    # GET - return shopping list based on stored selections
    try:
        # Extract quantities from recipe_selections (which may contain objects with quantity, name, skill, level)
        recipe_quantities = {}
        for recipe_id, data in recipe_selections.items():
            if isinstance(data, dict):
                recipe_quantities[recipe_id] = data.get('quantity', 1)
            else:
                recipe_quantities[recipe_id] = data

        # Load recipes
        recipes_file = get_bundled_path('recipes.json')
        if not recipes_file.exists():
            return jsonify({'recipes': [], 'error': 'Recipes file not found'})

        with open(recipes_file, 'r') as f:
            all_recipes = json.load(f)

        # Build recipe lookup by ID - must match the ID format from the web app
        # Web app uses: `${recipe.skill}_${recipe.name}_${idx}` where idx is the array index
        recipe_lookup = {}
        for idx, recipe in enumerate(all_recipes):
            recipe_id = f"{recipe.get('skill', 'Unknown')}_{recipe.get('name', 'Unknown')}_{idx}"
            recipe_lookup[recipe_id] = recipe

        # Get player inventory with full location details
        player_inventory = {}
        inventory_details = {}
        if inventory_parser:
            items_file = inventory_parser.get_latest_items_file()
            if items_file:
                inventory_data = inventory_parser.parse_items(items_file)
                for name, data in inventory_data.items():
                    player_inventory[name] = data['total']
                    inventory_details[name] = data

        # Load vendor data - build item->vendor lookup
        vendor_items = {}
        vendor_file = get_bundled_path('vendor_inventory.json')
        if vendor_file.exists():
            with open(vendor_file, 'r') as f:
                vendor_data = json.load(f)
                # Handle the format: { "vendors": { "VendorName": { "location": ..., "items": {...} } } }
                vendors_dict = vendor_data.get('vendors', vendor_data)
                for vendor_name, vendor_info in vendors_dict.items():
                    if isinstance(vendor_info, dict) and 'items' in vendor_info:
                        location = vendor_info.get('location', '')
                        for item_name in vendor_info.get('items', {}):
                            if item_name not in vendor_items:
                                vendor_items[item_name] = f"{vendor_name} ({location})"

        # Build shopping list
        result_recipes = []
        for recipe_id, quantity in recipe_quantities.items():
            recipe = recipe_lookup.get(recipe_id)
            if not recipe:
                continue

            recipe_result = {
                'id': recipe_id,
                'name': recipe.get('name', 'Unknown'),
                'skill': recipe.get('skill', 'Unknown'),
                'level': recipe.get('level', 0),
                'quantity': quantity,
                'materials': []
            }

            for ingredient in recipe.get('ingredients', []):
                mat_name = ingredient.get('item') or ingredient.get('name', 'Unknown')
                mat_qty = ingredient.get('quantity', 1) * quantity
                mat_have = player_inventory.get(mat_name, 0)

                # Get detailed location info
                details = inventory_details.get(mat_name, {})
                in_inventory = details.get('in_inventory', 0) if isinstance(details, dict) else 0
                # Safely sum storage values
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

                # Add vendor info if available
                if mat_name in vendor_items and mat_have < mat_qty:
                    mat_result['vendor_info'] = vendor_items[mat_name]

                recipe_result['materials'].append(mat_result)

            result_recipes.append(recipe_result)

        return jsonify({'recipes': result_recipes})
    except Exception as e:
        logger.error(f"Error getting shopping list: {e}")
        return jsonify({'error': str(e), 'recipes': []}), 500


@app.route('/recipes.json')
def get_recipes():
    """Serve recipes.json file for crafting tab"""
    try:
        recipes_file = get_bundled_path('recipes.json')
        if not recipes_file.exists():
            return jsonify({'error': 'Recipes file not found'}), 404

        with open(recipes_file, 'r') as f:
            recipes = json.load(f)
        return jsonify(recipes)
    except Exception as e:
        logger.error(f"Error loading recipes: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory')
def get_player_inventory():
    """Get full player inventory with storage locations"""
    global inventory_parser

    if not inventory_parser:
        return jsonify({'error': 'Inventory parser not initialized', 'items': {}}), 200

    try:
        items_file = inventory_parser.get_latest_items_file()
        if not items_file:
            return jsonify({'error': 'No inventory export found', 'items': {}}), 200

        inventory_data = inventory_parser.parse_items(items_file)

        # Return with file info for debugging
        return jsonify({
            'items': inventory_data,
            'source_file': items_file.name,
            'item_count': len(inventory_data)
        })
    except Exception as e:
        logger.error(f"Error loading player inventory: {e}")
        return jsonify({'error': str(e), 'items': {}}), 500


@app.route('/api/items')
def get_items_index():
    """Get global item index with game data, vendor info, and crafting recipes"""
    try:
        items_file = get_bundled_path('items.json')
        recipes_file = get_bundled_path('recipes.json')
        vendor_file = get_bundled_path('vendor_inventory.json')

        # Load items database
        items = {}
        if items_file.exists():
            with open(items_file, 'r') as f:
                items = json.load(f)

        # Load recipes and index by output item
        recipes_by_item = {}
        if recipes_file.exists():
            with open(recipes_file, 'r') as f:
                recipes = json.load(f)
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
            with open(vendor_file, 'r') as f:
                vendor_data = json.load(f)
                for vendor_name, vendor_info in vendor_data.items():
                    for item_name in vendor_info.get('items', []):
                        if item_name not in vendors_by_item:
                            vendors_by_item[item_name] = []
                        vendors_by_item[item_name].append({
                            'vendor': vendor_name,
                            'location': vendor_info.get('location', 'Unknown')
                        })

        # Build combined index keyed by display name
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

        return jsonify({
            'items': item_index,
            'item_count': len(item_index)
        })
    except Exception as e:
        logger.error(f"Error building item index: {e}")
        return jsonify({'error': str(e), 'items': {}}), 500


@app.route('/api/vendors')
def get_vendor_items():
    """Get items available from vendors"""
    try:
        vendor_file = get_bundled_path('vendor_inventory.json')

        if not vendor_file.exists():
            return jsonify({'error': 'Vendor file not found', 'vendor_items': {}}), 200

        with open(vendor_file, 'r') as f:
            vendor_data = json.load(f)

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

        return jsonify({
            'vendor_items': vendor_items,
            'item_count': len(vendor_items)
        })
    except Exception as e:
        logger.error(f"Error loading vendor items: {e}")
        return jsonify({'error': str(e), 'vendor_items': {}}), 500


@app.route('/api/keywords')
def get_item_keywords():
    """Get keyword to item mappings for ingredient matching"""
    try:
        items_file = get_bundled_path('items.json')

        if not items_file.exists():
            return jsonify({'error': 'Items file not found', 'keywords': {}}), 200

        with open(items_file, 'r') as f:
            items = json.load(f)

        # Build keyword -> item names mapping
        keyword_map = {}
        for item_id, item_data in items.items():
            display_name = item_data.get('Name', '')
            if not display_name:
                continue

            for keyword in item_data.get('Keywords', []):
                # Normalize keyword by removing "=value" suffix (e.g., "Bone=50" -> "Bone")
                normalized_keyword = keyword.split('=')[0]
                if normalized_keyword not in keyword_map:
                    keyword_map[normalized_keyword] = []
                if display_name not in keyword_map[normalized_keyword]:
                    keyword_map[normalized_keyword].append(display_name)

        return jsonify({
            'keywords': keyword_map,
            'keyword_count': len(keyword_map)
        })
    except Exception as e:
        logger.error(f"Error building keyword map: {e}")
        return jsonify({'error': str(e), 'keywords': {}}), 500


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Browser heartbeat to detect when window closes"""
    from datetime import datetime
    app.last_heartbeat = datetime.now()
    return jsonify({'status': 'ok'})


@app.route('/api/launch_overlay', methods=['POST'])
def launch_overlay():
    """Launch overlay mode in a separate process"""
    import subprocess
    import platform

    try:
        # Determine the executable path
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            exe_path = sys.executable
        else:
            # Running as Python script
            exe_path = sys.executable
            script_path = Path(__file__).parent / 'launcher.py'

        # Launch overlay in a new process
        if getattr(sys, 'frozen', False):
            # For compiled executable
            if platform.system() == 'Windows':
                subprocess.Popen([exe_path, '--overlay'],
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([exe_path, '--overlay'])
        else:
            # For Python script (use -B to bypass bytecode caching)
            # Check if we're in a nix-shell environment
            project_root = Path(__file__).parent
            if (project_root / 'shell.nix').exists() or os.environ.get('IN_NIX_SHELL'):
                # Running in nix-shell, wrap the command
                subprocess.Popen(['nix-shell', '--run', f'python3 -B {script_path} --overlay'],
                               cwd=str(project_root))
            else:
                # Regular Python environment
                subprocess.Popen([exe_path, '-B', str(script_path), '--overlay'])

        return jsonify({'success': True, 'message': 'Overlay launched'})
    except Exception as e:
        logger.error(f"Error launching overlay: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
