# Project Gorgon VIP Quest Helper

A local web-based quest helper for Project Gorgon that helps you track quest objectives, inventory, and find items you need.

## Features

### Quest Tracking
- **Active Quest Tracking** - Automatically detects active quests from exported Character JSON
- **Inventory Detection** - Monitors chat logs and exported Storage/Character JSON to track collected items
- **Storage Location Tracking** - Shows where items are stored (Inventory, Bank, Saddlebag, Dream World Chest)
- **Vendor Information** - Displays confirmed vendors and favor requirements for purchasable items
- **Completable Quest Detection** - Highlights quests you can complete with current inventory
- **Buyable Quest Filter** - Shows quests where all missing items can be purchased
- **Keyword-based Items** - Supports quests requiring item categories (e.g., "Poetry", "SnailShell")
- **Search functionality** to find any quest in the game

### Crafting
- **Recipe Browser** - Browse all crafting recipes by skill
- **Shopping List** - Select recipes and see aggregated material requirements
- **Inventory Integration** - Shows what materials you have and where they're stored
- **Quantity Selection** - Set how many of each recipe you want to craft
- **Persistent Selections** - Shopping list persists when switching tabs

### Browser Extension
- **Compact Overlay** - View quest progress and shopping lists in a browser popup
- **Pop-Out Window** - Pin overlay on screen while gaming for quick reference
- **Auto-Refresh** - Updates every 3 seconds
- **Quests & Crafting Tabs** - Switch between quest progress and crafting materials

### General
- **Auto-refresh** - Updates quest progress every 5 seconds
- **Interactive Help** - Built-in documentation with setup instructions

## How It Works

The tracker monitors your Project Gorgon chat logs and automatically detects when you collect items. It cross-references this with the official quest data to show you exactly what items you need for each quest and what you've already collected.

## Requirements

- **Project Gorgon VIP Access** - Required for JSON exports and chat logging
- **Chat Logging Enabled** - Must be enabled in Project Gorgon settings (V.I.P. section)
- **JSON Export** - Export Storage and Character JSON from the VIP Menu

## Installation

### Option 1: Download Executable (Easiest - Recommended for Most Users)

**No Python installation needed!**

1. Go to [Releases](https://github.com/oat-meal/projectgorgon-vip-questhelper/releases)
2. Download the executable for your platform:
   - **Windows**: `QuestHelper-Windows.exe`
   - **Linux**: `QuestHelper-Linux`
3. Double-click to run!
4. Your browser will open automatically to the setup wizard
5. Follow the on-screen instructions to configure your game data paths

**First-time Windows users**: You may see a "Windows protected your PC" warning. Click "More info" → "Run anyway". This is normal for unsigned executables.

### Option 2: Run from Source (Advanced Users)

**For developers or users who want to modify the code:**

#### With Nix (Linux):
```bash
git clone https://github.com/oat-meal/projectgorgon-vip-questhelper.git
cd projectgorgon-vip-questhelper
./start.sh
```

#### With Python (Windows/Linux/Mac):
```bash
git clone https://github.com/oat-meal/projectgorgon-vip-questhelper.git
cd projectgorgon-vip-questhelper

# Install dependencies
pip install -r requirements.txt

# Windows users:
START_QUEST_HELPER.bat

# Linux/Mac users:
python3 web_server.py
```

The server will start and open your browser to `http://127.0.0.1:5000`

## Setup

1. **Enable Chat Logging in Project Gorgon**:
   - Open Settings in-game
   - Go to V.I.P. section
   - Enable "Chat Logs"

2. **Export Character and Storage JSON** (for auto-detecting active quests and inventory):
   - Open the **VIP Menu** in-game
   - Export **Storage JSON** and **Character JSON**
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
- **Crafting** - Browse recipes by skill, build shopping lists with quantity selection
- **Help** - Built-in documentation and setup instructions

### Browser Extension

A companion browser extension provides a compact overlay for in-game reference:

1. Load the extension from `browser-extension/` folder in Chrome/Edge (developer mode)
2. Click the extension icon to see quest progress or crafting materials
3. Use **Pop Out** to pin the overlay on screen while gaming
4. Data syncs automatically with the main app

## Project Structure

```
projectgorgon-vip-questhelper/
├── web_server.py          # Flask web server
├── quest_parser.py        # Quest and inventory parsing
├── vendor_hints.py        # Vendor information system
├── vendor_inventory.json  # Confirmed vendor data with favor levels
├── templates/
│   └── index.html         # Web interface
├── quests.json           # Game quest data (downloaded)
├── items.json            # Game item data (downloaded)
├── start.sh              # Startup script
├── update_data.sh        # Data update script
└── shell.nix             # Nix environment
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
- Make sure you're running `./start.sh` from the project directory
- Verify Nix is installed: `nix --version`

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
