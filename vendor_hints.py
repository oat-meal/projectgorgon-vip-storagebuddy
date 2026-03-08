#!/usr/bin/env python3
"""
Vendor and item source hints for Project Gorgon VIP Quest Tracker
Based on wiki merchant data
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

# Merchant data scraped from wiki
MERCHANTS = {
    # Serbule
    'Azalak': {'location': 'Serbule', 'buys': ['potions', 'drugs', 'animal remnants', 'bounceweed']},
    'Charles Thompson': {'location': 'Serbule', 'buys': ['mushrooms', 'bones', 'potions', 'drugs', 'animal remnants']},
    'Elahil': {'location': 'Serbule', 'buys': ['weapons', 'off-hand items', 'arrows']},
    'Fainor': {'location': 'Serbule', 'buys': ['food', 'cooking ingredients', 'recipes']},
    'Flia': {'location': 'Serbule', 'buys': ['recipes', 'scrolls', 'poetry', 'books', 'spirit stones']},
    'Harry the Wolf': {'location': 'Serbule', 'buys': ['potions', 'food', 'gems', 'transmutation items']},
    'Hulon': {'location': 'Serbule', 'buys': ['recipes', 'books', 'scrolls']},
    'Joeh': {'location': 'Serbule', 'buys': ['weapons', 'armor']},
    'Larsan': {'location': 'Serbule', 'buys': ['crystals', 'gems', 'jewelry']},
    'Marna': {'location': 'Serbule', 'buys': ['everything']},
    'Mushroom Jack': {'location': 'Serbule', 'buys': ['skulls', 'mushrooms', 'animal remnants']},
    'Roshun the Traitor': {'location': 'Serbule', 'buys': ['weapons', 'armor', 'belts', 'jewelry', 'shields']},
    'Sir Coth': {'location': 'Serbule', 'buys': ['paintings', 'cookware', 'ancient coins', 'glass pieces', 'miscellaneous items']},
    'Therese': {'location': 'Serbule', 'buys': ['vegetables', 'miscellaneous items']},
    'Velkort': {'location': 'Serbule', 'buys': ['recipes', 'scrolls', 'books']},

    # Serbule Hills
    'Cleo Conyer': {'location': 'Serbule Hills', 'buys': ['everything']},
    'Durstin Tallow': {'location': 'Serbule Hills', 'buys': ['food', 'cooking ingredients']},
    'Sammie Grimspine': {'location': 'Serbule Hills', 'buys': ['armor', 'weapons', 'jewelry']},

    # Eltibule
    'Helena Veilmoor': {'location': 'Eltibule', 'buys': ['weapons', 'armor', 'recipes', 'skill books']},
    'Hogan': {'location': 'Eltibule', 'buys': ['weapons', 'armor']},
    'Jesina': {'location': 'Eltibule', 'buys': ['potions', 'food', 'cooking ingredients', 'alchemy ingredients']},
    'Kalaba': {'location': 'Eltibule', 'buys': ['weapons', 'armor']},
    'Kleave': {'location': 'Eltibule', 'buys': ['skins', 'leather rolls', 'skinning knives']},
    'Yetta': {'location': 'Eltibule', 'buys': ['everything']},
}

# Item keywords to vendor category mapping
ITEM_CATEGORIES = {
    'food': ['food', 'meat', 'cheese', 'bread', 'vegetable', 'fruit', 'apple', 'orange', 'cabbage', 'potato', 'onion'],
    'potion': ['potion', 'elixir', 'tonic'],
    'mushroom': ['mushroom', 'parasol', 'mycena', 'boletus', 'blusher', 'milk cap'],
    'gem': ['gem', 'diamond', 'ruby', 'emerald', 'sapphire', 'crystal'],
    'weapon': ['sword', 'staff', 'bow', 'hammer', 'knife', 'blade'],
    'armor': ['helmet', 'shirt', 'pants', 'boots', 'gloves', 'shield'],
    'jewelry': ['ring', 'necklace', 'amulet'],
    'recipe': ['recipe', 'scroll', 'book'],
    'cooking ingredient': ['sugar', 'salt', 'flour', 'butter', 'milk', 'egg'],
    'alchemy ingredient': ['acid', 'sulfur', 'saltpeter'],
}


class VendorHints:
    """Provides vendor and acquisition hints for items"""

    def __init__(self, vendor_inventory_file: Optional[Path] = None):
        self.merchants = MERCHANTS
        self.vendor_inventory = {}

        # Load vendor inventory database
        if vendor_inventory_file is None:
            vendor_inventory_file = Path(__file__).parent / 'vendor_inventory.json'

        if vendor_inventory_file.exists():
            with open(vendor_inventory_file, 'r') as f:
                data = json.load(f)
                self.vendor_inventory = data.get('vendors', {})
                self.favor_levels = data.get('metadata', {}).get('favor_levels', [])

    def get_item_category(self, item_name: str) -> Optional[str]:
        """Determine item category from name"""
        if not item_name:
            return None

        item_lower = item_name.lower()

        for category, keywords in ITEM_CATEGORIES.items():
            for keyword in keywords:
                if keyword in item_lower:
                    return category

        return None

    def find_vendors_exact(self, item_name: str) -> List[Dict[str, str]]:
        """Find vendors that definitely sell this item (from vendor inventory database)"""
        matching_vendors = []

        for vendor_name, vendor_info in self.vendor_inventory.items():
            # Check if item exists in vendor's items dict
            items = vendor_info.get('items', {})
            if item_name in items:
                item_data = items[item_name]
                favor_required = item_data.get('favor', 'Unknown')
                vendor_price = item_data.get('price', 0)

                matching_vendors.append({
                    'name': vendor_name,
                    'location': vendor_info['location'],
                    'note': f'Requires {favor_required} favor',
                    'favor': favor_required,
                    'vendor_price': vendor_price
                })

        return matching_vendors

    def find_vendors(self, item_name: str) -> List[Dict[str, str]]:
        """Find vendors for an item - first check exact matches, then fallback to category"""
        # First, check exact vendor inventory database
        exact_matches = self.find_vendors_exact(item_name)
        if exact_matches:
            return exact_matches

        # Fallback to category-based matching (for items not in database yet)
        category = self.get_item_category(item_name)

        if not category:
            return []

        matching_vendors = []

        for vendor_name, vendor_info in self.merchants.items():
            buys = vendor_info.get('buys', [])

            # Check if vendor buys this category
            if category in buys or 'everything' in buys:
                matching_vendors.append({
                    'name': vendor_name,
                    'location': vendor_info['location'],
                    'note': f"May sell {category}"
                })

        return matching_vendors

    def get_acquisition_hint(self, item_name: str) -> Dict[str, any]:
        """Get hints on how to acquire an item"""
        # Handle None item_name
        if not item_name:
            return {
                'category': 'unknown',
                'vendors': [],
                'general_hint': None,
                'confirmed': False
            }

        # Only use exact vendor matches from database
        exact_vendors = self.find_vendors_exact(item_name)
        is_confirmed = len(exact_vendors) > 0

        hint = {
            'category': 'unknown',
            'vendors': exact_vendors[:5] if is_confirmed else [],  # Only show confirmed vendors
            'general_hint': None,
            'confirmed': is_confirmed
        }

        # Only add hints for confirmed vendors
        if is_confirmed:
            hint['general_hint'] = f'Sold by {len(exact_vendors)} confirmed vendor(s)'
        else:
            # No vendor hints for items not in database
            hint['general_hint'] = None

        return hint


def main():
    """Test vendor hints"""
    vh = VendorHints()

    test_items = [
        'Cat Eyeball',
        'Cabbage',
        'Health Potion',
        'Iron Sword',
        'Parasol Mushroom'
    ]

    for item in test_items:
        print(f"\n{item}:")
        hint = vh.get_acquisition_hint(item)
        print(f"  Category: {hint['category']}")
        print(f"  Hint: {hint['general_hint']}")
        if hint['vendors']:
            print(f"  Possible vendors:")
            for v in hint['vendors']:
                print(f"    - {v['name']} ({v['location']})")
        else:
            print(f"  Vendors: None found (likely drop/craft only)")


if __name__ == '__main__':
    main()
