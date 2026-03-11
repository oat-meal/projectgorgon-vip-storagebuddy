#!/usr/bin/env python3
"""
Project Gorgon VIP Quest Helper
Parses quest data and monitors chat logs for item collection
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

try:
    from vendor_hints import VendorHints
    VENDOR_HINTS_AVAILABLE = True
except ImportError:
    VENDOR_HINTS_AVAILABLE = False


@dataclass
class QuestObjective:
    """Represents a quest objective"""
    description: str
    obj_type: str
    item_name: Optional[str] = None
    number: int = 1
    target: Optional[str] = None


@dataclass
class Quest:
    """Represents a quest with objectives"""
    internal_name: str
    name: str
    description: str
    objectives: List[QuestObjective]
    displayed_location: Optional[str] = None
    keywords: List[str] = None

    def is_guild_quest(self) -> bool:
        """Check if this is a guild quest"""
        return self.keywords and 'GuildGroup' in self.keywords

    def has_collect_objectives(self) -> bool:
        """Check if this quest has any item collection objectives"""
        return any(obj.obj_type == 'Collect' for obj in self.objectives)


class QuestDatabase:
    """Manages quest data from Project Gorgon JSON"""

    def __init__(self, quests_file: Path, items_file: Path):
        self.quests_file = quests_file
        self.items_file = items_file
        self.quests: Dict[str, Quest] = {}
        self.items: Dict[str, str] = {}  # ItemCode -> Name
        self.load_data()

    def load_data(self):
        """Load quests and items from JSON files"""
        # Load items with prices and descriptions
        self.item_prices: Dict[str, float] = {}  # InternalName -> Price
        self.item_descriptions: Dict[str, str] = {}  # InternalName -> Description
        self.item_keywords: Dict[str, List[str]] = {}  # Keyword -> List of item display names
        with open(self.items_file, 'r') as f:
            items_data = json.load(f)
            for item_id, item_info in items_data.items():
                if 'Name' in item_info and 'InternalName' in item_info:
                    internal_name = item_info['InternalName']
                    display_name = item_info['Name']
                    self.items[internal_name] = display_name
                    self.item_prices[internal_name] = item_info.get('Value', 0)
                    self.item_descriptions[internal_name] = item_info.get('Description', '')

                    # Build keyword index
                    for keyword in item_info.get('Keywords', []):
                        # Normalize keyword by removing "=value" suffix (e.g., "SnailShell=50" -> "SnailShell")
                        normalized_keyword = keyword.split('=')[0]
                        if normalized_keyword not in self.item_keywords:
                            self.item_keywords[normalized_keyword] = []
                        self.item_keywords[normalized_keyword].append(display_name)

        # Load quests
        with open(self.quests_file, 'r') as f:
            quests_data = json.load(f)
            for quest_id, quest_info in quests_data.items():
                if 'InternalName' not in quest_info:
                    continue

                objectives = []
                if 'Objectives' in quest_info:
                    for obj in quest_info['Objectives']:
                        # Fall back to Target if ItemName is not present
                        item_name = obj.get('ItemName') or obj.get('Target')
                        objectives.append(QuestObjective(
                            description=obj.get('Description', ''),
                            obj_type=obj.get('Type', ''),
                            item_name=item_name,
                            number=obj.get('Number', 1),
                            target=obj.get('Target')
                        ))

                quest = Quest(
                    internal_name=quest_info['InternalName'],
                    name=quest_info.get('Name', quest_info['InternalName']),
                    description=quest_info.get('Description', ''),
                    objectives=objectives,
                    displayed_location=quest_info.get('DisplayedLocation'),
                    keywords=quest_info.get('Keywords', [])
                )

                self.quests[quest.internal_name] = quest

    def get_quest(self, internal_name: str) -> Optional[Quest]:
        """Get quest by internal name"""
        return self.quests.get(internal_name)

    def get_item_display_name(self, internal_name: str) -> str:
        """Get display name for item"""
        return self.items.get(internal_name, internal_name)

    def get_item_price(self, internal_name: str) -> float:
        """Get item price (vendor value)"""
        return self.item_prices.get(internal_name, 0)

    def get_item_description(self, internal_name: str) -> str:
        """Get item description"""
        return self.item_descriptions.get(internal_name, '')

    def get_collect_objectives(self, quest: Quest) -> List[QuestObjective]:
        """Get all 'Collect' type objectives from a quest"""
        return [obj for obj in quest.objectives if obj.obj_type == 'Collect']


class ChatLogParser:
    """Parses Project Gorgon chat logs for item collection"""

    # Patterns for parsing chat log
    ITEM_PATTERN = re.compile(r'^\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\t\[Status\] (.+?) (?:x(\d+) )?added to inventory\.$')

    def __init__(self, chat_log_dir: Path):
        self.chat_log_dir = chat_log_dir

    def get_latest_log_file(self) -> Optional[Path]:
        """Get the most recent chat log file"""
        log_files = list(self.chat_log_dir.glob('Chat-*.log'))
        if not log_files:
            return None
        return max(log_files, key=lambda p: p.stat().st_mtime)

    def parse_log_file(self, log_file: Path) -> List[tuple]:
        """Parse a log file and return list of (item_name, quantity, timestamp)"""
        items_collected = []

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = self.ITEM_PATTERN.match(line.strip())
                if match:
                    item_name = match.group(1)
                    quantity = int(match.group(2)) if match.group(2) else 1
                    timestamp = line.split('\t')[0]
                    items_collected.append((item_name, quantity, timestamp))

        return items_collected

    def get_items_since_timestamp(self, log_file: Path, since: str) -> List[tuple]:
        """Get items collected since a specific timestamp"""
        all_items = self.parse_log_file(log_file)
        return [(item, qty, ts) for item, qty, ts in all_items if ts > since]


class InventoryParser:
    """Parses Project Gorgon item export files"""

    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir

    def get_latest_items_file(self) -> Optional[Path]:
        """Get the most recent items export file"""
        item_files = list(self.reports_dir.glob('*_items_*.json'))
        if not item_files:
            return None
        return max(item_files, key=lambda p: p.stat().st_mtime)

    def parse_items(self, items_file: Path) -> Dict[str, Dict]:
        """Parse items file and return inventory counts by location"""
        with open(items_file, 'r') as f:
            data = json.load(f)

        # Organize items by name and location
        items_by_name = {}

        for item in data.get('Items', []):
            item_name = item.get('Name', 'Unknown')
            stack_size = item.get('StackSize', 1)

            # Determine location
            if 'StorageVault' in item:
                location = item['StorageVault']
            else:
                location = 'Inventory'

            if item_name not in items_by_name:
                items_by_name[item_name] = {
                    'total': 0,
                    'inventory': 0,
                    'storage': {}
                }

            items_by_name[item_name]['total'] += stack_size

            if location == 'Inventory':
                items_by_name[item_name]['inventory'] += stack_size
            else:
                if location not in items_by_name[item_name]['storage']:
                    items_by_name[item_name]['storage'][location] = 0
                items_by_name[item_name]['storage'][location] += stack_size

        return items_by_name


class QuestTracker:
    """Main quest tracking functionality"""

    def __init__(self, quest_db: QuestDatabase, chat_parser: ChatLogParser, inventory_parser: Optional[InventoryParser] = None):
        self.quest_db = quest_db
        self.chat_parser = chat_parser
        self.inventory_parser = inventory_parser
        self.vendor_hints = VendorHints() if VENDOR_HINTS_AVAILABLE else None

    def get_quest_checklist(self, quest_internal_name: str) -> Dict:
        """Generate a checklist for a quest"""
        quest = self.quest_db.get_quest(quest_internal_name)
        if not quest:
            return None

        collect_objectives = self.quest_db.get_collect_objectives(quest)

        checklist = {
            'quest_name': quest.name,
            'description': quest.description,
            'location': quest.displayed_location,
            'items': [],
            'is_completable': False
        }

        for obj in collect_objectives:
            item_display_name = self.quest_db.get_item_display_name(obj.item_name)
            item_price = self.quest_db.get_item_price(obj.item_name)
            item_description = self.quest_db.get_item_description(obj.item_name)
            checklist['items'].append({
                'internal_name': obj.item_name,
                'display_name': item_display_name,
                'description': item_description,
                'required': obj.number,
                'collected': 0,
                'completed': False,
                'price': item_price
            })

        return checklist

    def update_checklist_from_log(self, checklist: Dict, log_file: Path) -> Dict:
        """Update checklist based on items in chat log"""
        items_collected = self.chat_parser.parse_log_file(log_file)

        # Count items by display name
        item_counts = {}
        for item_name, qty, _ in items_collected:
            item_counts[item_name] = item_counts.get(item_name, 0) + qty

        # Get inventory data if available
        inventory_data = {}
        if self.inventory_parser:
            items_file = self.inventory_parser.get_latest_items_file()
            if items_file:
                inventory_data = self.inventory_parser.parse_items(items_file)

        # Update checklist
        for item in checklist['items']:
            display_name = item['display_name']
            internal_name = item['internal_name']

            # Chat log collected count
            if display_name in item_counts:
                collected = min(item_counts[display_name], item['required'])
                item['collected'] = collected
                item['completed'] = collected >= item['required']

            # Inventory data - check for exact match first
            if display_name in inventory_data:
                inv_data = inventory_data[display_name]
                item['in_inventory'] = inv_data['inventory']
                item['in_storage'] = inv_data['total'] - inv_data['inventory']
                item['storage_locations'] = inv_data['storage']

                # Update completion based on total available
                total_available = inv_data['total']
                if total_available >= item['required']:
                    item['completed'] = True
            # If no exact match, check if this is a keyword-based objective (like Poetry, SnailShell)
            elif internal_name in self.quest_db.item_keywords:
                # Sum up all items with this keyword
                keyword_items = self.quest_db.item_keywords[internal_name]
                total_inventory = 0
                total_storage = 0
                combined_storage = {}

                for keyword_item_name in keyword_items:
                    if keyword_item_name in inventory_data:
                        inv_data = inventory_data[keyword_item_name]
                        total_inventory += inv_data['inventory']
                        total_storage += inv_data['total'] - inv_data['inventory']

                        # Combine storage locations
                        for loc, count in inv_data['storage'].items():
                            combined_storage[loc] = combined_storage.get(loc, 0) + count

                if total_inventory + total_storage > 0:
                    item['in_inventory'] = total_inventory
                    item['in_storage'] = total_storage
                    item['storage_locations'] = combined_storage
                    item['keyword_match'] = True
                    item['matching_items'] = keyword_items[:5]  # Show first 5 matching items

                    # Update completion based on total available
                    total_available = total_inventory + total_storage
                    if total_available >= item['required']:
                        item['completed'] = True

            # Add vendor hints (only for confirmed vendors)
            if self.vendor_hints and not item.get('completed', False):
                hints = self.vendor_hints.get_acquisition_hint(display_name)
                if hints['confirmed'] and hints['vendors']:
                    item['vendor_hint'] = hints['general_hint']
                    item['possible_vendors'] = [
                        f"{v['name']} ({v['location']}) - {v.get('note', 'Confirmed vendor')}"
                        for v in hints['vendors'][:3]  # Limit to 3 vendors
                    ]
                    # Store raw vendor data for favor checking (using 'vendor' key for consistency)
                    item['vendor_data'] = [
                        {'vendor': v['name'], 'favor': v.get('favor', 'Neutral')}
                        for v in hints['vendors'][:3]
                    ]
                    # Use vendor price if available (might differ from item value)
                    if hints['vendors'] and 'vendor_price' in hints['vendors'][0]:
                        item['vendor_price'] = hints['vendors'][0]['vendor_price']

        # Check if quest is completable (all items completed)
        if checklist['items']:
            checklist['is_completable'] = all(item.get('completed', False) for item in checklist['items'])

            # Check if quest is purchasable (all missing items can be bought)
            checklist['is_purchasable'] = False
            if not checklist['is_completable'] and self.vendor_hints:
                missing_items = [item for item in checklist['items'] if not item.get('completed', False)]
                all_purchasable = all(
                    item.get('possible_vendors') and len(item.get('possible_vendors', [])) > 0
                    for item in missing_items
                )
                checklist['is_purchasable'] = all_purchasable and len(missing_items) > 0

            # Calculate total cost to buy missing items (only for items with confirmed vendors)
            total_cost = 0
            for item in checklist['items']:
                if not item.get('completed', False) and item.get('possible_vendors'):
                    items_needed = item['required'] - item.get('collected', 0)
                    # Use vendor price if available, otherwise use item value
                    price = item.get('vendor_price', item.get('price', 0))
                    total_cost += price * items_needed
            checklist['total_cost'] = total_cost
        else:
            # Quest with no collect objectives is considered completable
            checklist['is_completable'] = True
            checklist['is_purchasable'] = False
            checklist['total_cost'] = 0

        return checklist


def main():
    """Test the quest tracker"""
    base_dir = Path.home() / 'quest-tracker'
    chat_log_dir = Path.home() / 'Documents' / 'Project Gorgon Data' / 'ChatLogs'

    # Initialize
    quest_db = QuestDatabase(
        base_dir / 'quests.json',
        base_dir / 'items.json'
    )

    chat_parser = ChatLogParser(chat_log_dir)
    tracker = QuestTracker(quest_db, chat_parser)

    # Test with a quest
    test_quest = 'GetCatEyeballsForJoeh'
    checklist = tracker.get_quest_checklist(test_quest)

    if checklist:
        print(f"Quest: {checklist['quest_name']}")
        print(f"Location: {checklist['location']}")
        print(f"Description: {checklist['description']}")
        print("\nItems needed:")
        for item in checklist['items']:
            print(f"  - {item['display_name']}: 0/{item['required']}")

    # Update from log
    log_file = chat_parser.get_latest_log_file()
    if log_file:
        print(f"\nChecking log file: {log_file.name}")
        tracker.update_checklist_from_log(checklist, log_file)
        print("\nUpdated checklist:")
        for item in checklist['items']:
            status = "✓" if item['completed'] else " "
            print(f"  [{status}] {item['display_name']}: {item['collected']}/{item['required']}")


if __name__ == '__main__':
    main()
