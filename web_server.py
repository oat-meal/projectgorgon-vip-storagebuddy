#!/usr/bin/env python3
"""
Project Gorgon VIP Quest Helper - Web Server
Flask-based web interface for quest tracking
"""

from flask import Flask, render_template, jsonify, request
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

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Project Gorgon VIP Quest Helper')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args = parser.parse_args()

app = Flask(__name__)

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


@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Browser heartbeat to detect when window closes"""
    from datetime import datetime
    app.last_heartbeat = datetime.now()
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
