# Quick Start Guide - VIP Quest Helper

## 1. Start the VIP Quest Helper

```bash
cd ~/quest-tracker
./start.sh
```

The server will start and display:
```
* Running on http://127.0.0.1:5000
```

## 2. Open in Your Browser

Open your web browser and go to:
```
http://127.0.0.1:5000
```

## 3. Using the Tracker

### Active Quests Tab
- Shows all quests from your character data
- Click any quest to see its checklist

### Search Tab
- Search for any quest in the game
- Type at least 2 characters to search

### Checklist Features
- **Auto-detected items**: Items you've collected (from chat logs) are shown in the progress
- **Manual checkboxes**: Check off items you already have in your inventory
- **Progress bars**: Visual indication of completion
- **Auto-refresh**: Updates every 5 seconds automatically
- **Manual refresh**: Click the "Refresh" button to update immediately

## 4. How Items Are Tracked

The tracker monitors your chat logs for messages like:
```
[Status] Red Apple x2 added to inventory.
[Status] Large Strawberry added to inventory.
```

When you pick up items in-game:
1. The chat log is updated
2. The tracker reads the new entries
3. Your checklist updates automatically

## 5. Important Notes

- **Chat logging must be enabled** in Project Gorgon settings (V.I.P. section)
- **Character reports** help auto-detect active quests (optional)
- **Manual checks are saved** in your browser's localStorage
- **The tracker runs locally** - no internet required (except for initial data download)

## Example Workflow

1. Accept a quest in-game
2. Open the quest tracker in your browser
3. Find the quest in the "Active" tab or use "Search"
4. See all required items listed
5. As you collect items in-game, watch them automatically check off!
6. Manually check items you already had in your inventory

## Troubleshooting

**Nothing showing in Active tab?**
- Generate a character report in-game
- Use the Search tab instead

**Items not updating?**
- Make sure chat logging is enabled
- Check that Status messages are visible in your chat tab
- Click the Refresh button manually

**Vendor says they sell an item but you can't see it in their shop?**
- **IMPORTANT**: Uncheck "Hide Unusable" in the vendor window
- This option hides items like seeds, ingredients, and crafting materials even when you can use them
- The filter is overly aggressive and will hide quest items you're looking for
- Keep "Hide Unusable" unchecked when shopping for quest items

**Server won't start?**
- Make sure you're running `./start.sh` from the `~/quest-tracker` directory
- Check that Nix is installed and working

## Updating Quest Data

To get the latest quest and item data:
```bash
cd ~/quest-tracker
./update_data.sh
```

This downloads fresh data from the official Project Gorgon CDN.

## Stopping the Server

Press `Ctrl+C` in the terminal where the server is running.

---

Enjoy tracking your quests!
