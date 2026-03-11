# Project Gorgon VIP StorageBuddy

A local web-based tool for Project Gorgon that helps you track quest objectives, crafting materials, and inventory across all your storage locations.

## Features

### Quest Tracking
- **Active Quest Tracking** - Automatically detects active quests from exported Character JSON
- **Quest Pinning** - Pin up to 20 quests for quick access
- **Inventory Detection** - Reads exported Storage/Character JSON to track collected items
- **Color-Coded Progress** - Green (ready), orange (buyable from vendor), purple (needs favor), gray (gather)
- **Storage Location Tracking** - Shows where items are stored (Inventory, Bank, Saddlebag, Dream World Chest, Community Chest)
- **Vendor Information** - Displays vendors, prices, and favor requirements for purchasable items
- **Favor Tracking** - Reads NPC favor levels from Character JSON to show which vendor items you can access
- **Wiki Links** - Quick links to Project Gorgon Wiki for items that need to be farmed/gathered
- **Region Filter** - Filter quests by turn-in location
- **Search** - Find any quest in the game

### Crafting
- **Recipe Browser** - Browse all crafting recipes by skill
- **Skill Level Tracking** - Recipes show level requirements; grayed-out recipes require higher skill
- **Smart Craftability** - Color-coded: green (ready), orange (buyable), purple (needs favor), blue (gather), gray (need skill)
- **Pinned Recipes** - Pin up to 20 recipes and see aggregated material requirements
- **Recursive Sub-components** - Automatically detects craftable sub-items (3 levels deep)
- **Inventory Integration** - Shows what materials you have and where they're stored
- **Material Sources** - Each ingredient shows its source: have, craft, buy, need favor, or gather
- **Quantity Selection** - Set how many of each recipe you want to craft (1-999)

### Pop-Out Overlay
- **Compact Window** - View quest progress and crafting materials in a separate window
- **Always-On-Top** - Keep visible over your game using PowerToys (Windows) or window manager (Linux)
- **Theme Sync** - Automatically matches your selected theme
- **Pinned Sync** - Pinned quests and recipes sync from main page
- **Aggregated Materials** - Shows all materials with storage locations, source info, and recipe associations
- **Auto-Refresh** - Updates every 3 seconds

### Themes
- **7 Color Themes** - Sepia, Catppuccin Latte, Catppuccin Mocha, Solarized Light, Nord, Gruvbox, High Contrast
- **High Contrast Mode** - Accessibility theme with maximum contrast, larger text, and bold colors for users with visual impairment
- **Persistent Selection** - Theme choice saved to browser
- **Synced Overlay** - Pop-out overlay matches main window theme

### General
- **Auto-refresh** - Updates every 5 seconds
- **Update Notifications** - Checks GitHub for new releases on launch and notifies when updates are available
- **Interactive Help** - Built-in documentation with color legends and setup instructions

## How It Works

The tracker monitors your Project Gorgon chat logs and automatically detects when you collect items. It cross-references this with the official quest data to show you exactly what items you need for each quest and what you've already collected.

## Requirements

- **Project Gorgon VIP Access** - Required for JSON exports and chat logging
- **Chat Logging Enabled** - Must be enabled in Project Gorgon settings (V.I.P. section)
- **JSON Export** - Export Storage and Character JSON from the VIP Menu

## Installation

### Option 1: Download Executable (Windows)

1. Go to [Releases](https://github.com/oat-meal/projectgorgon-vip-storagebuddy/releases)
2. Download `StorageBuddy-Windows-x.x.x.exe`
3. Double-click to run
4. Your browser will open automatically to the setup wizard

> **Windows Security Warning**
>
> This application is **unsigned**, which means Windows will show security warnings when you try to run it. This is normal for open-source software distributed outside the Microsoft Store.
>
> **Windows Defender SmartScreen**: "Windows protected your PC"
> - Click **"More info"**
> - Click **"Run anyway"**
>
> **Windows Defender Antivirus**: May flag the executable
> - This is a false positive due to PyInstaller packaging
> - You can verify the source code in this repository
> - Or run from source (Option 2) to avoid this entirely
>
> Code signing certificates cost $200-500/year, which is impractical for a free community tool. If you're uncomfortable running unsigned software, use Option 2 to run from source.

### Option 2: Run from Source (Windows/Linux)

```bash
git clone https://github.com/oat-meal/projectgorgon-vip-storagebuddy.git
cd projectgorgon-vip-storagebuddy
pip install -r requirements.txt
python3 web_server.py
```

Your browser will open to `http://127.0.0.1:5000`

## Setup

1. **Enable Chat Logging in Project Gorgon**:
   - Open Settings in-game
   - Go to V.I.P. section
   - Enable "Chat Logs"

2. **Export Character and Storage JSON** (for inventory, quests, and skill levels):
   - Open the **VIP Menu** in-game
   - Export **Storage JSON** (updates inventory and storage locations)
   - Export **Character JSON** (updates active quests and crafting skill levels)
   - This creates files in `~/Documents/Project Gorgon Data/Reports/`

## Usage

See [QUICKSTART.md](QUICKSTART.md) for detailed usage instructions.

### Quick Overview

1. **Enable chat logging** in Project Gorgon (V.I.P. settings)
2. **Export Storage and Character JSON** from the VIP Menu to update inventory
3. **Accept quests** in-game and they'll appear in the tracker
4. **Track progress** automatically as you collect items
5. **Check vendor hints** for items you can purchase

### Features by Tab

- **Quests** - Shows active quests from your character data, filterable by region
- **Crafting** - Browse recipes by skill, see skill requirements, build shopping lists with color-coded status
- **Help** - Built-in documentation, color legend, and setup instructions

### Pop-Out Overlay

Use the built-in overlay for in-game reference:

1. Click **"Pop Out Overlay"** button in the header
2. A compact window opens with quest progress and crafting materials
3. Position it over your game window
4. Use an always-on-top tool to keep it visible:
   - **Windows**: [PowerToys Always on Top](https://learn.microsoft.com/en-us/windows/powertoys/always-on-top) (Win+Ctrl+T)
   - **Linux**: Right-click title bar → "Always on Top"
5. Theme and pinned items sync automatically from main window

## Project Structure

```
projectgorgon-vip-storagebuddy/
├── web_server.py          # Flask web server
├── quest_parser.py        # Quest and inventory parsing
├── vendor_hints.py        # Vendor information system
├── vendor_inventory.json  # Confirmed vendor data with favor levels
├── templates/
│   ├── index.html         # Main web interface
│   └── overlay.html       # Pop-out overlay interface
├── quests.json            # Game quest data
├── items.json             # Game item data
├── recipes.json           # Crafting recipe data
├── start.sh               # Startup script (Linux)
└── update_data.sh         # Data update script
```

## Game Data Locations

- **Chat Logs**: `~/Documents/Project Gorgon Data/ChatLogs/`
- **Character Reports**: `~/Documents/Project Gorgon Data/Reports/`

## Updating Quest Data

To get the latest quest and item data from the official Project Gorgon CDN:

```bash
./update_data.sh
```

## Troubleshooting

### Items not showing in inventory?
- Export fresh Storage and Character JSON from the VIP Menu
- Make sure chat logging is enabled
- Check that Status messages are visible in your chat tab

### Vendor items not appearing?
- **IMPORTANT**: Uncheck "Hide Unusable" in the vendor window
- This filter hides items like seeds, ingredients, and crafting materials
- The filter is overly aggressive and will hide quest items you're looking for

### No active quests showing?
- Make sure you've exported Character JSON from the VIP Menu
- Use the Search tab to find quests manually

### Server won't start?
- Ensure port 5000 is available
- Check Python dependencies: `pip install -r requirements.txt`

## Contributing

Contributions are welcome! This project specifically needs:

- Verified vendor inventory data (items, prices, favor requirements)
- Bug reports and feature requests
- UI/UX improvements
- Documentation improvements

Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for the Project Gorgon community
- Quest and item data from the official Project Gorgon CDN
- Vendor information sourced from the Project Gorgon Wiki
- Some portions copyright 2026 Elder Game, LLC

## Support

If you find this tool useful, consider supporting its development!

---

**Note**: This is a community tool and is not affiliated with or endorsed by Elder Game, LLC.
