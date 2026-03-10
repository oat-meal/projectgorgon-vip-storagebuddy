#!/usr/bin/env python3
"""Debug script to inspect Fletching recipe page structure"""

import requests
from bs4 import BeautifulSoup

url = "https://wiki.projectgorgon.com/wiki/Fletching/Recipes"

print(f"Fetching: {url}")
response = requests.get(url, timeout=10)
soup = BeautifulSoup(response.content, 'html.parser')

# Find ALL tables
print("\n=== ALL TABLES ===")
tables = soup.find_all('table')
print(f"Found {len(tables)} total tables\n")

for i, table in enumerate(tables):
    print(f"Table {i+1}:")
    print(f"  Classes: {table.get('class', 'No class')}")
    print(f"  ID: {table.get('id', 'No ID')}")

    # Count rows
    rows = table.find_all('tr')
    print(f"  Rows: {len(rows)}")

    # Show first row (headers)
    if rows:
        first_row = rows[0]
        headers = [th.get_text(strip=True) for th in first_row.find_all(['th', 'td'])]
        print(f"  First row: {headers}")

        # Show second row (first data row) if it exists
        if len(rows) > 1:
            data_row = rows[1]
            data = [td.get_text(strip=True)[:50] for td in data_row.find_all('td')]
            print(f"  Second row: {data[:3]}... (showing first 3 cells)")

    print()

# Look for wikitable class specifically
print("\n=== WIKITABLE CLASS ===")
wikitables = soup.find_all('table', {'class': 'wikitable'})
print(f"Found {len(wikitables)} wikitable(s)\n")

# Look for sortable class
print("\n=== SORTABLE CLASS ===")
sortable = soup.find_all('table', {'class': 'sortable'})
print(f"Found {len(sortable)} sortable table(s)\n")
