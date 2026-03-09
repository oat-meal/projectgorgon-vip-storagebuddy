#!/usr/bin/env python3
"""
Scrape Project Gorgon Wiki recipes to build comprehensive recipes.json
Scrapes all skill recipe pages from wiki.projectgorgon.com
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from pathlib import Path

# Wiki URLs
CATEGORY_URL = "https://wiki.projectgorgon.com/wiki/Category:Recipes"
WIKI_BASE = "https://wiki.projectgorgon.com"

def get_skill_pages():
    """Get list of all skill recipe pages from Category:Recipes"""
    print("Fetching skill recipe pages from wiki...")

    try:
        response = requests.get(CATEGORY_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all links in the category page
        skill_pages = []

        # Look for links in the mw-category div
        category_div = soup.find('div', {'class': 'mw-category'})
        if category_div:
            links = category_div.find_all('a')
            for link in links:
                href = link.get('href', '')
                title = link.get('title', '')
                if '/Recipes' in title and title:
                    skill_name = title.replace('/Recipes', '')
                    skill_pages.append({
                        'skill': skill_name,
                        'url': WIKI_BASE + href
                    })

        print(f"Found {len(skill_pages)} skill recipe pages")
        return skill_pages

    except Exception as e:
        print(f"Error fetching skill pages: {e}")
        return []

def parse_ingredient(ingredient_text):
    """Parse ingredient text to extract name and quantity

    Examples:
    - "Spider Egg x1" -> ("Spider Egg", 1)
    - "Basic Fish Scales x2" -> ("Basic Fish Scales", 2)
    - "Any Bone x1" -> ("Any Bone", 1)
    """
    # Strip whitespace
    ingredient_text = ingredient_text.strip()

    # Match pattern "name xN" or just "name"
    match = re.match(r'^(.+?)\s+x(\d+)$', ingredient_text)
    if match:
        name = match.group(1).strip()
        quantity = int(match.group(2))
        return (name, quantity)
    else:
        # No quantity specified, assume 1
        return (ingredient_text, 1)

def parse_recipe_table(soup, skill_name):
    """Parse recipe table from a skill page"""
    recipes = []

    # Find the recipe table - look for tables that have 'sortable' as one of their classes
    all_tables = soup.find_all('table')
    tables = [t for t in all_tables if t.get('class') and 'sortable' in t.get('class')]

    for table in tables:
        # Get header row to find column indices
        header_row = table.find('tr')
        if not header_row:
            continue

        headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

        # Find column indices
        level_idx = None
        name_idx = None
        ing_idx = None
        res_idx = None

        for idx, header in enumerate(headers):
            header_lower = header.lower()
            if 'lvl' in header_lower or 'level' in header_lower:
                level_idx = idx
            elif 'name' in header_lower:
                name_idx = idx
            elif 'ingredient' in header_lower:
                ing_idx = idx
            elif 'result' in header_lower:
                res_idx = idx

        # Parse data rows
        rows = table.find_all('tr')[1:]  # Skip header row

        for row in rows:
            cols = row.find_all('td')

            if len(cols) < 2:  # Need at least name and something else
                continue

            try:
                # Extract data
                level = 0
                name = ""
                ingredients = []
                results = []

                if level_idx is not None and level_idx < len(cols):
                    level_text = cols[level_idx].get_text(strip=True)
                    if level_text.isdigit():
                        level = int(level_text)

                if name_idx is not None and name_idx < len(cols):
                    name = cols[name_idx].get_text(strip=True)

                # Parse ingredients
                if ing_idx is not None and ing_idx < len(cols):
                    ing_cell = cols[ing_idx]

                    # Get all text, split by newlines
                    ing_text = ing_cell.get_text(separator='\n')
                    ing_lines = [line.strip() for line in ing_text.split('\n') if line.strip()]

                    # Join ingredient names with quantities (they're on separate lines)
                    # Pattern: "Item Name" on one line, "x2" on next line
                    i = 0
                    while i < len(ing_lines):
                        line = ing_lines[i]

                        # Check if next line is a quantity (starts with 'x' or 'X')
                        if i + 1 < len(ing_lines) and re.match(r'^x\d+$', ing_lines[i + 1], re.IGNORECASE):
                            # Join item name with quantity
                            combined = f"{line} {ing_lines[i + 1]}"
                            item_name, quantity = parse_ingredient(combined)
                            if item_name:
                                ingredients.append({
                                    'item': item_name,
                                    'quantity': quantity
                                })
                            i += 2  # Skip both lines
                        else:
                            # Try parsing this line as-is (might already have "item x quantity")
                            if 'x' in line.lower():
                                item_name, quantity = parse_ingredient(line)
                                if item_name:
                                    ingredients.append({
                                        'item': item_name,
                                        'quantity': quantity
                                    })
                            i += 1

                # Parse results (same logic as ingredients)
                if res_idx is not None and res_idx < len(cols):
                    res_cell = cols[res_idx]
                    res_text = res_cell.get_text(separator='\n')
                    res_lines = [line.strip() for line in res_text.split('\n') if line.strip()]

                    # Join result names with quantities
                    i = 0
                    while i < len(res_lines):
                        line = res_lines[i]

                        # Check if next line is a quantity
                        if i + 1 < len(res_lines) and re.match(r'^x\d+$', res_lines[i + 1], re.IGNORECASE):
                            combined = f"{line} {res_lines[i + 1]}"
                            item_name, quantity = parse_ingredient(combined)
                            if item_name:
                                results.append({
                                    'item': item_name,
                                    'quantity': quantity
                                })
                            i += 2
                        else:
                            if 'x' in line.lower():
                                item_name, quantity = parse_ingredient(line)
                                if item_name:
                                    results.append({
                                        'item': item_name,
                                        'quantity': quantity
                                    })
                            i += 1

                # Only add recipe if we have a name and ingredients
                if name and ingredients:
                    recipe = {
                        'name': name,
                        'skill': skill_name,
                        'level': level,
                        'ingredients': ingredients,
                        'results': results if results else [{'item': name, 'quantity': 1}]
                    }
                    recipes.append(recipe)

            except Exception as e:
                print(f"  Warning: Could not parse recipe row: {e}")
                continue

    return recipes

def scrape_skill_recipes(skill_info):
    """Scrape recipes for a single skill"""
    skill_name = skill_info['skill']
    url = skill_info['url']

    print(f"Scraping {skill_name}...")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        recipes = parse_recipe_table(soup, skill_name)
        print(f"  Found {len(recipes)} recipes")

        return recipes

    except Exception as e:
        print(f"  Error scraping {skill_name}: {e}")
        return []

def main():
    print("="*60)
    print("Project Gorgon Wiki Recipe Scraper")
    print("="*60)
    print()

    # Get all skill pages
    skill_pages = get_skill_pages()

    if not skill_pages:
        print("No skill pages found. Exiting.")
        return

    print()
    print(f"Starting to scrape {len(skill_pages)} skills...")
    print()

    # Scrape all recipes
    all_recipes = []

    for skill_info in skill_pages:
        recipes = scrape_skill_recipes(skill_info)
        all_recipes.extend(recipes)

        # Be polite to the wiki server
        time.sleep(0.5)

    print()
    print("="*60)
    print(f"Total recipes scraped: {len(all_recipes)}")
    print("="*60)

    # Show breakdown by skill
    skill_counts = {}
    for recipe in all_recipes:
        skill = recipe['skill']
        skill_counts[skill] = skill_counts.get(skill, 0) + 1

    print("\nRecipes by skill:")
    for skill, count in sorted(skill_counts.items()):
        print(f"  {skill}: {count}")

    # Save to recipes.json
    output_file = Path(__file__).parent / 'recipes.json'

    print()
    print(f"Saving to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_recipes, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved {len(all_recipes)} recipes to recipes.json")

    # Show file size
    size_kb = output_file.stat().st_size / 1024
    print(f"File size: {size_kb:.1f} KB")
    print()

if __name__ == '__main__':
    main()
