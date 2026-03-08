#!/usr/bin/env python3
"""
Project Gorgon VIP Quest Tracker - Web Server
Flask-based web interface for quest tracking
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
from quest_parser import QuestDatabase, ChatLogParser, QuestTracker, InventoryParser

app = Flask(__name__)

# Initialize quest tracker
base_dir = Path.home() / 'quest-tracker'
chat_log_dir = Path.home() / 'Documents' / 'Project Gorgon Data' / 'ChatLogs'
character_file = Path.home() / 'Documents' / 'Project Gorgon Data' / 'Reports'

quest_db = QuestDatabase(
    base_dir / 'quests.json',
    base_dir / 'items.json'
)

chat_parser = ChatLogParser(chat_log_dir)
inventory_parser = InventoryParser(character_file)
tracker = QuestTracker(quest_db, chat_parser, inventory_parser)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


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


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
