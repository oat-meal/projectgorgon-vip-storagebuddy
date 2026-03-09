#!/usr/bin/env python3
"""
Recipe scraper for Gorgon Codex
Pulls all crafting recipes and saves to recipes.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urljoin

BASE_URL = "https://www.gorgoncodex.com"
RECIPES_URL = f"{BASE_URL}/recipes"

def get_all_recipe_links():
    """Fetch all recipe links from the main recipes page"""
    print("Fetching recipe list from Gorgon Codex...")

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(RECIPES_URL, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all recipe links - adjust selector based on actual page structure
    # This is a placeholder - we'll need to inspect the actual page
    recipe_links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if href.startswith('/recipes/') and href != '/recipes':
            full_url = urljoin(BASE_URL, href)
            recipe_links.append(full_url)

    # Remove duplicates
    recipe_links = list(set(recipe_links))
    print(f"Found {len(recipe_links)} recipe links")

    return recipe_links

def scrape_recipe(url):
    """Scrape a single recipe page"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    recipe = {
        "id": url.split('/')[-1],
        "url": url,
        "name": "",
        "skill": "",
        "level_required": 0,
        "ingredients": []
    }

    # Extract recipe name from title or h1
    title_tag = soup.find('h1')
    if title_tag:
        recipe["name"] = title_tag.get_text().strip()

    # Extract structured data if available
    script_tags = soup.find_all('script', type='application/ld+json')
    for script in script_tags:
        try:
            data = json.loads(script.string)
            if data.get('@type') == 'Thing':
                recipe["name"] = data.get('name', recipe["name"])
        except:
            pass

    # Extract skill from link to /skills/
    skill_links = soup.find_all('a', href=re.compile(r'^/skills/'))
    if skill_links:
        # Get the first skill link
        skill_href = skill_links[0]['href']
        skill_name = skill_href.replace('/skills/', '').replace('-', ' ').title()
        recipe["skill"] = skill_name

        # Extract level from the skill link text (e.g., "Fletching Lv 6")
        skill_text = skill_links[0].get_text().strip()
        level_match = re.search(r'Lv\s*(\d+)', skill_text)
        if level_match:
            recipe["level_required"] = int(level_match.group(1))

    # Extract ingredients
    # Look for ingredient items - they typically have item icons and quantities
    # Find all links that point to /items/
    item_links = soup.find_all('a', href=re.compile(r'^/items/'))

    for link in item_links:
        item_name = link.get_text().strip()
        if not item_name:
            continue

        # Look for quantity in nearby text
        # Quantities are typically in format "×N"
        parent = link.parent
        quantity = 1  # default quantity

        if parent:
            text = parent.get_text()
            qty_match = re.search(r'×\s*(\d+)', text)
            if qty_match:
                quantity = int(qty_match.group(1))

        recipe["ingredients"].append({
            "name": item_name,
            "quantity": quantity
        })

    return recipe

def main():
    print("Gorgon Codex Recipe Scraper")
    print("=" * 50)

    # Get all recipe links
    recipe_links = get_all_recipe_links()

    if not recipe_links:
        print("No recipe links found. The page structure may have changed.")
        print("Please check the Gorgon Codex recipes page manually.")
        return

    # Scrape all recipes
    print(f"\nScraping {len(recipe_links)} recipes...")

    recipes = []
    for i, url in enumerate(recipe_links, 1):
        print(f"[{i}/{len(recipe_links)}] Scraping: {url}")

        try:
            recipe = scrape_recipe(url)
            recipes.append(recipe)

            # Be respectful - don't hammer the server
            time.sleep(0.5)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

    # Save to recipes.json
    output_file = "recipes.json"
    with open(output_file, 'w') as f:
        json.dump(recipes, f, indent=2)

    print(f"\nSaved {len(recipes)} recipes to {output_file}")
    print("\nSample recipe:")
    if recipes:
        print(json.dumps(recipes[0], indent=2))

if __name__ == "__main__":
    main()
