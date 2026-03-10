# Quick Start Guide - StorageBuddy

## 1. First-Time Setup

1. **Enable VIP exports** in Project Gorgon:
   - Open the **VIP Menu** in-game
   - Enable **Logs Export**

2. **Export your data**:
   - In the VIP Menu, export **Storage JSON** (inventory & storage)
   - Export **Character JSON** (quests & skill levels)

3. **Start StorageBuddy**:
   - Run the executable, or use `./start.sh` from source
   - Your browser opens to `http://127.0.0.1:5000`

## 2. Using StorageBuddy

### Quests Tab
- Shows active quests that need item collection
- **Filters**: All, Ready (can complete now), Pinned
- **Pin quests** by clicking the checkbox for quick access
- **Region dropdown** filters by turn-in location
- Quest details show item locations, vendor info, and wiki links

### Crafting Tab
- Browse recipes by skill using the dropdown
- **Pin recipes** (up to 20) to build a shopping list
- Use +/− to set quantities
- **Color coding**: Green (ready), Orange (buyable), Purple (needs favor), Blue (gather), Gray (need skill)
- Materials panel shows aggregated requirements with sources

### Pop-Out Overlay
- Click **"Pop Out Overlay"** for a compact in-game tracker
- Use PowerToys (Windows) or window manager (Linux) to keep it on top
- Syncs theme and pinned items automatically

### Themes
- Click theme buttons in the header to change colors
- Choice persists across sessions

## 3. Keeping Data Current

Re-export from the VIP Menu after:
- Looting or crafting items
- Banking or moving items between storage
- Gaining skill levels
- Accepting or completing quests

## 4. Troubleshooting

**No quests showing?**
- Export Character JSON from VIP Menu

**Items not updating?**
- Export Storage JSON from VIP Menu

**Can't find vendor items?**
- Uncheck "Hide Unusable" in vendor windows

**Server won't start?**
- Ensure port 5000 is available
- Check Python/Nix installation

## 5. Updating Game Data

To refresh quest/item/recipe data from the wiki:
```bash
./update_data.sh
```

Use sparingly - this scrapes the wiki.
