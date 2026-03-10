#!/usr/bin/env python3
"""Test parsing logic on Fletching page"""

import requests
from bs4 import BeautifulSoup
import re

url = "https://wiki.projectgorgon.com/wiki/Fletching/Recipes"

print(f"Fetching: {url}")
response = requests.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Find tables with 'sortable' class
all_tables = soup.find_all('table')
tables = [t for t in all_tables if t.get('class') and 'sortable' in t.get('class')]

print(f"\nFound {len(tables)} sortable table(s)")

for table in tables:
    # Get headers
    header_row = table.find('tr')
    if not header_row:
        print("  No header row!")
        continue

    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
    print(f"\nHeaders: {headers}")

    # Find column indices
    name_idx = None
    ing_idx = None
    level_idx = None

    for idx, header in enumerate(headers):
        header_lower = header.lower()
        if 'name' in header_lower:
            name_idx = idx
        elif 'ingredient' in header_lower:
            ing_idx = idx
        elif 'lvl' in header_lower or 'level' in header_lower:
            level_idx = idx

    print(f"Level idx: {level_idx}, Name idx: {name_idx}, Ingredients idx: {ing_idx}")

    # Parse first data row
    rows = table.find_all('tr')[1:]  # Skip header
    print(f"\nTotal data rows: {len(rows)}")

    if rows:
        print("\nFirst row analysis:")
        first_row = rows[0]
        cols = first_row.find_all('td')
        print(f"  Columns in row: {len(cols)}")

        if level_idx is not None and level_idx < len(cols):
            print(f"  Level: {cols[level_idx].get_text(strip=True)}")

        if name_idx is not None and name_idx < len(cols):
            print(f"  Name: {cols[name_idx].get_text(strip=True)}")

        if ing_idx is not None and ing_idx < len(cols):
            ing_cell = cols[ing_idx]
            ing_text = ing_cell.get_text(separator='\n')
            print(f"  Ingredients text: {repr(ing_text[:200])}")

            # Try parsing
            ing_lines = [line.strip() for line in ing_text.split('\n') if line.strip()]
            print(f"  Ingredients lines: {ing_lines}")

            # Check for "x" pattern
            for line in ing_lines:
                if ' x' in line or ' X' in line:
                    print(f"    Found 'x' in: {line}")
