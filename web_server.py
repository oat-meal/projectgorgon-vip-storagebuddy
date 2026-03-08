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
from quest_parser import QuestDatabase, ChatLogParser, QuestTracker, InventoryParser
from config import get_config
from data_updater import ensure_quest_data
from version import __version__

app = Flask(__name__)

# Initialize configuration
config = get_config()
base_dir = config.get_base_dir()

# Debug information
print(f"\n=== Project Gorgon VIP Quest Helper v{__version__} ===")
print(f"Running as executable: {getattr(sys, 'frozen', False)}")
print(f"Data directory: {base_dir}")

# Ensure quest data files exist (copy from bundle or download if needed)
bundled_dir = config.get_bundled_resource_dir()
if bundled_dir:
    print(f"Bundled resource directory: {bundled_dir}")
    print(f"  quests.json exists: {(bundled_dir / 'quests.json').exists()}")
    print(f"  items.json exists: {(bundled_dir / 'items.json').exists()}")
else:
    print("No bundled resources found (running from source)")

if not ensure_quest_data(base_dir, bundled_dir):
    print("\nWARNING: Failed to obtain game data files")
    print("The Quest Helper may not work correctly")
    print("Please check your internet connection and try again\n")
else:
    print(f"\n✓ Game data loaded from {base_dir}")
    print(f"  quests.json: {(base_dir / 'quests.json').stat().st_size / 1024 / 1024:.1f} MB")
    print(f"  items.json: {(base_dir / 'items.json').stat().st_size / 1024 / 1024:.1f} MB")

config_status = config.get_status()

# Initialize quest tracker only if configured
quest_db = None
chat_parser = None
inventory_parser = None
tracker = None

if config_status['configured']:
    chat_log_dir = config.get_chat_log_dir()
    character_file = config.get_reports_dir()

    print(f"Using game data from: {config.config.get('detected_path', 'custom configuration')}")
    print(f"  Chat logs: {chat_log_dir}")
    print(f"  Reports: {character_file}")

    quest_db = QuestDatabase(
        base_dir / 'quests.json',
        base_dir / 'items.json'
    )

    chat_parser = ChatLogParser(chat_log_dir)
    inventory_parser = InventoryParser(character_file)
    tracker = QuestTracker(quest_db, chat_parser, inventory_parser)
else:
    print("\nQuest Helper starting in setup mode.")
    print("Open your browser to http://127.0.0.1:5000/setup to configure.\n")


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
def get_active_quests():
    """Get list of active quests from character data"""
    # Find the most recent character file
    report_files = list(character_file.glob('Character_*.json'))
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
def get_completable_quests():
    """Get list of quests that can be completed right now"""
    # Find the most recent character file
    report_files = list(character_file.glob('Character_*.json'))
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
def get_purchasable_quests():
    """Get list of quests that can be completed by buying items"""
    # Find the most recent character file
    report_files = list(character_file.glob('Character_*.json'))
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
    detected = config._auto_detect_game_data()

    if detected:
        # Save the detected paths
        config.config.update(detected)
        config._save_config()

        # Get stats about what was found
        chat_dir = Path(detected['chat_log_dir'])
        reports_dir = Path(detected['reports_dir'])

        return jsonify({
            'success': True,
            'detected_path': detected['detected_path'],
            'chat_log_dir': str(chat_dir),
            'reports_dir': str(reports_dir),
            'chat_log_count': len(list(chat_dir.glob('Chat-*.log'))),
            'character_files_count': len(list(reports_dir.glob('Character_*.json')))
        })
    else:
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
        'frozen': getattr(sys, 'frozen', False)
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
