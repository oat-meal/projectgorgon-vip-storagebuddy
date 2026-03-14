# Project Gorgon VIP StorageBuddy

A local web-based tool for Project Gorgon that helps track quest objectives, crafting materials, and inventory across all storage locations.

## Quick Reference

- **Version**: 0.7.4
- **Stack**: Python 3 / Flask / HTML+CSS+JS (vanilla)
- **Run**: `python3 web_server.py` (opens browser to http://127.0.0.1:5000)
- **GitHub**: https://github.com/oat-meal/projectgorgon-vip-storagebuddy

## Architecture

```
quest-tracker/
├── web_server.py          # Flask app entry point
├── app/
│   ├── factory.py         # Flask app factory
│   ├── routes/            # API endpoints
│   │   ├── main.py        # Page routes (/, /overlay)
│   │   ├── quests.py      # Quest API endpoints
│   │   ├── crafting.py    # Crafting/recipe endpoints
│   │   ├── data.py        # Data loading endpoints
│   │   └── config_routes.py # Configuration endpoints
│   ├── services/          # Business logic
│   │   ├── character_service.py  # Character data handling
│   │   ├── vendor_service.py     # Vendor/favor logic
│   │   ├── npc_service.py        # NPC data
│   │   ├── item_resolution_service.py
│   │   └── cache_service.py      # Data caching
│   └── utils/             # Utilities
│       ├── paths.py       # File path resolution
│       ├── security.py    # Input validation
│       ├── validation.py  # Data validation
│       └── constants.py   # App constants
├── quest_parser.py        # Quest and inventory parsing
├── vendor_hints.py        # Vendor information system
├── config.py              # Configuration management
├── templates/
│   ├── index.html         # Main web interface
│   └── overlay.html       # Pop-out overlay window
├── static/
│   └── themes.css         # Theme definitions
└── Data files:
    ├── quests.json        # Game quest data (from CDN)
    ├── items.json         # Game item data (from CDN)
    ├── recipes.json       # Crafting recipes (from CDN)
    ├── npcs.json          # NPC data (from CDN)
    └── vendor_inventory.json  # Curated vendor data
```

## Key Concepts

### Multi-Character Support
- Users can switch between characters via dropdown
- Character selection syncs to overlay via `localStorage` key: `storagebuddy-character`
- Favor checking shows which characters can purchase vendor items

### Overlay System
- Pop-out window at `/overlay` for in-game reference
- Syncs with main page via localStorage:
  - `storagebuddy-character` - Selected character
  - `storagebuddy-pinned-quests` - Pinned quest IDs
  - `storagebuddy-pinned-recipes` - Pinned recipe IDs
  - `storagebuddy-theme` - Theme selection
- Auto-refreshes every 5 seconds

### Quest/Recipe Status Colors
- **Green** (`ready`/`completable`) - Have all required items
- **Orange** (`buyable`/`purchasable`) - Can buy from vendor
- **Purple** (`needs-favor`) - Need higher NPC favor
- **Blue** (`craft`) - Need to craft sub-components
- **Gray** (`gather`) - Need to farm/find items

### Data Sources
- **CDN Data**: `quests.json`, `items.json`, `recipes.json`, `npcs.json` - Updated via `./update_data.sh`
- **User Data**: Read from `~/Documents/Project Gorgon Data/Reports/` (Character/Storage JSON exports)
- **Chat Logs**: `~/Documents/Project Gorgon Data/ChatLogs/`

## Development

### Running Locally
```bash
python3 web_server.py
```

### Dependencies
```
Flask>=2.3.0
Flask-Cors>=4.0.0
pywebview>=4.0.0
beautifulsoup4>=4.12.0
requests>=2.31.0
```

### Building Executable
```bash
python3 build_executable.py
```
Creates standalone executables in `QuestHelper-Windows/` and `QuestHelper-Linux/`.

### Updating Game Data
```bash
./update_data.sh
```
Downloads latest quest/item/recipe data from Project Gorgon CDN.

## API Endpoints

Key endpoints (see `docs/API.md` for full reference):

- `GET /api/quests` - Active quests with item requirements
- `GET /api/recipes` - All crafting recipes
- `GET /api/overlay_data` - Combined data for overlay (quests + recipes + materials)
- `GET /api/characters` - Available character list
- `GET /api/character/<name>` - Character details (skills, favor, currencies)

## Recent Development Context

### v0.7.x Series (March 2026)
- Multi-character inventory attribution
- Overlay tooltips showing item locations
- Character selection sync between main page and overlay
- `is_completable` and `is_purchasable` flags in overlay API
- Empty state handling for "No character selected"
- localStorage-based state sync (replaced unreliable `storage` events)

## Notes

- **VIP Required**: Project Gorgon VIP access needed for JSON exports
- **Port**: Runs on 5000 by default
- **Browser**: Auto-opens on startup
- **Always-on-top**: Users need PowerToys (Windows) or window manager (Linux) to keep overlay visible over game
