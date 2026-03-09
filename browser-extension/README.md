# Project Gorgon Quest Tracker - Browser Extension

A cross-platform browser extension for tracking Project Gorgon VIP quests while you play.

## Features

- Quest tracking popup window
- Adjustable zoom (50% to 200%)
- Three view modes: Ready, Buyable, and Active quests
- Auto-refreshes every 3 seconds
- Works on Windows, Linux, and macOS
- Compatible with Chrome, Brave, Edge, and Firefox

## Installation

### Prerequisites

1. Make sure `launcher.py` is running in the background to provide quest data
2. The Flask server should be accessible at `http://127.0.0.1:5000`

### Loading the Extension

#### Chrome / Brave / Edge

1. Open your browser and navigate to the extensions page:
   - Chrome: `chrome://extensions/`
   - Brave: `brave://extensions/`
   - Edge: `edge://extensions/`

2. Enable "Developer mode" using the toggle in the top right

3. Click "Load unpacked"

4. Navigate to the `browser-extension` folder in your quest-tracker directory

5. Select the folder and click "Select Folder"

6. The Quest Tracker extension should now appear in your extensions list

#### Firefox

1. Open Firefox and navigate to: `about:debugging#/runtime/this-firefox`

2. Click "Load Temporary Add-on"

3. Navigate to the `browser-extension` folder

4. Select the `manifest.json` file

5. The extension will be loaded temporarily (will need to be reloaded each time you restart Firefox)

## Usage

1. Click the Quest Tracker icon in your browser toolbar

2. The popup will show your current quests

3. Use the dropdown to switch between:
   - **Ready**: Quests you can complete now
   - **Buyable**: Quests you can complete by purchasing items
   - **Active**: All active quests

4. Use the +/- buttons to adjust zoom level

5. **Tip**: Pin the popup window to keep it visible while you play. Use Alt+Tab to quickly switch between the game and quest tracker.

6. The tracker auto-updates every 3 seconds

## Troubleshooting

### Extension shows "Cannot connect to Quest Helper"

- Make sure `launcher.py` is running
- Verify the server is accessible at `http://127.0.0.1:5000`
- Check your browser's console for CORS or network errors

### Extension disappeared after browser restart (Firefox)

- Firefox temporary add-ons are removed on restart
- You'll need to reload the extension each time using the steps above
- For permanent installation, the extension would need to be signed by Mozilla

## Files

- `manifest.json` - Extension configuration
- `popup.html` - Extension popup interface
- `popup.js` - Popup functionality and data loading
- `icons/` - Extension icons (16px, 48px, 128px)

## Version

Current version: 0.2.8

## Cross-Platform Compatibility

This extension works identically on:
- Windows
- Linux
- macOS

All major Chromium-based browsers and Firefox are supported.
