# Project Gorgon VIP Quest Helper

A local web-based quest helper for Project Gorgon that helps you track quest objectives, inventory, and find items you need.

## Features

- **Active Quest Tracking** - Automatically detects active quests from character reports
- **Inventory Detection** - Monitors chat logs and character reports to track collected items
- **Storage Location Tracking** - Shows where items are stored (Inventory, Bank, Saddlebag, Dream World Chest)
- **Vendor Information** - Displays confirmed vendors and favor requirements for purchasable items
- **Completable Quest Detection** - Highlights quests you can complete with current inventory
- **Buyable Quest Filter** - Shows quests where all missing items can be purchased
- **Auto-refresh** - Updates quest progress every 5 seconds
- **Keyword-based Items** - Supports quests requiring item categories (e.g., "Poetry", "SnailShell")
- **Interactive checklist** with manual checkboxes for items
- **Search functionality** to find any quest in the game

## How It Works

The tracker monitors your Project Gorgon chat logs and automatically detects when you collect items. It cross-references this with the official quest data to show you exactly what items you need for each quest and what you've already collected.

## Requirements

- **Project Gorgon VIP Access** - Required for character reports and chat logging
- **Nix Package Manager** - For easy dependency management
- **Chat Logging Enabled** - Must be enabled in Project Gorgon settings (V.I.P. section)

## Installation

1. Clone this repository:
```bash
git clone https://github.com/oat-meal/projectgorgon-vip-questhelper.git
cd projectgorgon-vip-questhelper
```

2. Start the tracker:
```bash
./start.sh
```

3. Open your browser to:
```
http://127.0.0.1:5000
```

## Setup

1. **Enable Chat Logging in Project Gorgon**:
   - Open Settings in-game
   - Go to V.I.P. section
   - Enable "Chat Logs"

2. **Generate Character Report** (for auto-detecting active quests):
   - In-game, use the character report feature
   - This creates files in `~/Documents/Project Gorgon Data/Reports/`

## Usage

See [QUICKSTART.md](QUICKSTART.md) for detailed usage instructions.

### Quick Overview

1. **Enable chat logging** in Project Gorgon (V.I.P. settings)
2. **Generate character reports** in-game to update inventory
3. **Accept quests** in-game and they'll appear in the tracker
4. **Track progress** automatically as you collect items
5. **Check vendor hints** for items you can purchase

### Features by Tab

- **Active Quests** - Shows quests from your character data
- **Ready** - Quests you can complete with current inventory
- **Buyable** - Quests where all missing items can be purchased
- **Search** - Find any quest in the game database

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
- Generate a fresh character report in-game
- Make sure chat logging is enabled
- Check that Status messages are visible in your chat tab

### Vendor items not appearing?
- **IMPORTANT**: Uncheck "Hide Unusable" in the vendor window
- This filter hides items like seeds, ingredients, and crafting materials
- The filter is overly aggressive and will hide quest items you're looking for

### No active quests showing?
- Make sure you've generated a character report in-game
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
