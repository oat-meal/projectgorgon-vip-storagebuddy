#!/usr/bin/env bash
# Update quest and item data from Project Gorgon CDN

cd "$(dirname "$0")"

echo "Updating Project Gorgon quest data..."

# Check for latest version
LATEST_VERSION=$(curl -s https://cdn.projectgorgon.com/ | grep -oP 'V#\d+' | head -1 | grep -oP '\d+')

if [ -z "$LATEST_VERSION" ]; then
    echo "Error: Could not determine latest version"
    exit 1
fi

echo "Latest version: v$LATEST_VERSION"

# Download quests.json
echo "Downloading quests.json..."
curl -s "http://cdn.projectgorgon.com/v$LATEST_VERSION/data/quests.json" -o quests.json

# Download items.json
echo "Downloading items.json..."
curl -s "http://cdn.projectgorgon.com/v$LATEST_VERSION/data/items.json" -o items.json

echo "Update complete!"
echo ""
echo "Files updated:"
ls -lh quests.json items.json
