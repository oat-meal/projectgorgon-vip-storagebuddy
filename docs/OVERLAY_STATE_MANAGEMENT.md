# Overlay State Management Design

## Overview

This document describes the state management architecture for the StorageBuddy overlay,
including data sources, synchronization mechanisms, and design decisions.

## Architecture

### Components

1. **Main UI** (`index.html`) - Primary user interface for managing quests and recipes
2. **Overlay** (`overlay.html`) - Compact pop-out window for in-game reference
3. **Server** (`app/routes/crafting.py`) - Backend API providing recipe calculations

### State Locations

| State | Main UI | Server | Overlay | Persistence |
|-------|---------|--------|---------|-------------|
| Pinned Recipes | `recipeQuantities` | `_recipe_selections` | via API | localStorage |
| Pinned Quests | `pinnedQuests` | N/A | `pinnedQuests` | localStorage |
| Selected Character | `storagebuddy-character` | via query param | synced from main | localStorage |
| View Preferences | N/A | N/A | `overlayPrefs` | localStorage |
| Inventory/Skills | via API | Computed | via API | Game files |

## Data Flow

### Pinned Recipes Flow

```
┌─────────────────┐     POST /api/shopping_list      ┌─────────────┐
│    Main UI      │ ─────────────────────────────────► │   Server    │
│ (localStorage)  │                                    │ (in-memory) │
└─────────────────┘                                    └─────────────┘
                                                              │
                                                              │ GET /api/shopping_list
                                                              ▼
                                                       ┌─────────────┐
                                                       │   Overlay   │
                                                       │ (transient) │
                                                       └─────────────┘
```

**Current Behavior:**
1. Main UI stores pinned recipes in `localStorage['recipeQuantities']`
2. Main UI POSTs selections to server when shopping list updates
3. Server stores in `_recipe_selections` (in-memory, lost on restart)
4. Overlay GETs from `/api/shopping_list` endpoint

**Issue:** Server restart loses pin state. Overlay shows empty until main UI syncs.

### Ready Recipes Flow

```
┌─────────────────┐                                   ┌─────────────┐
│    Main UI      │  (computed client-side from       │   Server    │
│                 │   all recipes + inventory)        │             │
└─────────────────┘                                   └─────────────┘
                                                              │
                                                              │ GET /api/ready_recipes
                                                              ▼
                                                       ┌─────────────┐
                                                       │   Overlay   │
                                                       └─────────────┘
```

**Current Behavior:**
1. Server computes ready recipes on-demand from inventory + recipes
2. Includes both "craftable" (have all materials) and "buyable" (can buy from vendor)
3. No client-side state required

## View Modes

### Crafting Tab Views

| View | Data Source | API Endpoint | Description |
|------|-------------|--------------|-------------|
| Pinned | Server memory | `/api/shopping_list` | User-selected recipes to craft |
| Ready | Server computed | `/api/ready_recipes` | All recipes ready to craft now |

### Display Format (v0.7.0+)

Both views now display an **aggregated materials list** showing:
- All unique materials across all recipes
- Storage locations with icons
- Source information (vendor or gather)
- Which recipes need each material

### Switching Views

When user switches between Pinned/Ready views:
1. Save preference to `localStorage['overlayPrefs']`
2. Fetch fresh data from appropriate endpoint
3. Render the aggregated materials view

## Material Display

### Storage Location Icons

| Icon | Location |
|------|----------|
| 📦 | Inventory |
| 🏦 | Bank Storage |
| 🎒 | Saddlebag |
| 💤 | Dream Vault |
| 🏠 | Community Chest |

### Material Source Icons

| Icon | Source | Description |
|------|--------|-------------|
| 🛒 | Buy | Purchasable from vendor (shows vendor info) |
| ❤️ | Need Favor | Vendor available but requires more favor |
| 🔨 | Craft | Can be crafted with current skills |
| 🔍 | Gather | Must be gathered/farmed (includes Wiki link) |

### Material Categorization Logic

Materials are categorized in this priority order:
1. **Craft** - If player has skill to craft the item
2. **Buy** - If available from vendor AND player has required favor
3. **Buy (needs favor)** - If available from vendor but player lacks favor
4. **Gather** - All other items (with Wiki search link)

## Refresh Behavior

### Auto-Refresh (overlay.html)
- **Interval:** 3 seconds
- **Scope:** Refreshes data for current tab only
- **Trigger:** `setInterval` on page load

### Manual Refresh
- **Trigger:** User switches tabs or views
- **Action:** Fetches fresh data from server

### Theme Sync
- **Interval:** 1 second
- **Action:** Checks localStorage for theme changes from main UI

### Pinned Quests Sync
- **Interval:** 1 second
- **Action:** Syncs pinned quests from localStorage

### Character Selection Sync (v0.7.1+)
- **Source:** Main UI saves to `localStorage['storagebuddy-character']`
- **Sync Method:** Overlay reads on each data refresh (5 second interval)
- **Requirement:** Overlay requires character selection to display quest data
- **Empty State:** Shows "No character selected" if no character in localStorage

## Known Limitations

1. **Cross-tab Communication:** No real-time sync between main UI and overlay
2. **Stale Data:** 3-second refresh interval means up to 3s delay in updates

## Implemented Solutions

### Server Restart Recovery (v0.7.0+)

When the overlay loads and requests pinned recipes:
1. If server returns empty AND localStorage has pins
2. Overlay automatically syncs localStorage to server via POST
3. Overlay re-fetches and displays the synced data

This ensures pins survive server restarts without requiring user action.

```javascript
// In loadCraftingData():
if (craftingView === 'pinned' && allRecipes.length === 0) {
    const localPins = JSON.parse(localStorage.getItem('recipeQuantities') || '{}');
    if (Object.keys(localPins).length > 0) {
        await syncLocalPinsToServer(localPins);
        // Re-fetch after sync
    }
}
```

### Aggregated Materials View (v0.7.0+)

Both Pinned and Ready views now show an aggregated materials list:
- Materials are deduplicated across all recipes
- Each material shows total needed quantity
- Storage locations are displayed for items you have
- Source information always shown (where to get more)
- "For: Recipe1, Recipe2" shows which recipes need each material

```javascript
// Materials aggregation
for (const recipe of allRecipes) {
    for (const mat of recipe.materials) {
        if (!aggregatedMaterials[mat.name]) {
            aggregatedMaterials[mat.name] = { ... };
        }
        aggregatedMaterials[mat.name].need += mat.need;
        aggregatedMaterials[mat.name].recipes.push(recipe.name);
    }
}
```

## Future Improvements

1. Use `BroadcastChannel` API for real-time cross-tab communication
2. Consider persistent storage (file/SQLite) for server-side pin state
3. Add manual "Sync" button to overlay for immediate refresh
