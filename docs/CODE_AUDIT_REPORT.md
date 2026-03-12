# StorageBuddy Code Audit Report

**Audit Date:** March 11, 2026
**Version:** 0.7.0
**Scope:** Full application (Python backend + JavaScript frontend)
**Total Lines Analyzed:** ~10,000+ lines across 30+ files

---

## Executive Summary

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| Python Backend | 0 | 8 | 18 | 15 | 41 |
| Main UI (index.html) | 1 | 14 | 39 | 29 | 83 |
| Overlay (overlay.html) | 0 | 5 | 11 | 7 | 23 |
| **TOTAL** | **1** | **27** | **68** | **51** | **147** |

### Top 10 Most Critical Issues

1. **[CRITICAL]** `recipeQuantities` data structure inconsistency (index.html) - stores number but accesses `.quantity` property
2. **[HIGH]** Thread-unsafe global `_recipe_selections` in crafting.py
3. **[HIGH]** Log file overwritten on restart (factory.py mode='w')
4. **[HIGH]** Material rendering logic duplicated 5+ times across frontend
5. **[HIGH]** Recipe/vendor loading duplicated in 3+ backend modules
6. **[HIGH]** 4 separate setInterval timers in overlay causing 180+ ops/minute
7. **[HIGH]** Race conditions in tab switching with async data loading
8. **[HIGH]** Storage icon mapping duplicated 6+ times in frontend
9. **[HIGH]** Inventory loading duplicated across multiple route handlers
10. **[HIGH]** Quest list building code duplicated 4+ times

---

## Part 1: Python Backend Audit

### High Severity Issues

#### 1. Thread-Unsafe Global State
**File:** `app/routes/crafting.py:31`
```python
_recipe_selections = {}  # Global dict, not thread-safe
```
**Impact:** Multiple concurrent requests could corrupt recipe selection data.
**Fix:** Use thread-safe dictionary or store in session/database.

#### 2. Log File Overwritten on Restart
**File:** `app/factory.py:90`
```python
FileHandler(log_file, mode='w')  # Should be 'a' for append
```
**Impact:** All previous logs lost on every restart.
**Fix:** Change to `mode='a'`.

#### 3. Recipe Indexing Duplicated 3+ Times
**Files:** `crafting.py`, `data.py`, `item_resolution_service.py`
```python
# Same logic appears in all three:
recipes_by_output = {}
for recipe in recipes:
    for output in recipe.get('outputs', []):
        recipes_by_output[output['name']] = recipe
```
**Impact:** Maintenance nightmare, inconsistent behavior possible.
**Fix:** Consolidate into single `ItemResolutionService` method.

#### 4. Vendor Loading Duplicated 3+ Times
**Files:** `crafting.py`, `vendor_service.py`, `item_resolution_service.py`
**Impact:** Same vendor data loaded and parsed multiple times per request.
**Fix:** Use VendorService exclusively; remove duplicates.

#### 5. Inventory Loading Duplicated
**Files:** `quests.py:176-188`, `crafting.py:98-112`, `crafting.py:507-521`
**Impact:** Same try-catch pattern repeated; changes need updating in multiple places.
**Fix:** Extract to `CharacterService.get_player_inventory()` method.

#### 6. Tracker State Not Validated Against Config
**File:** `app/routes/decorators.py:16-20`
```python
_quest_db = None  # Never reset when config changes
```
**Impact:** After config update, trackers use stale paths.
**Fix:** Validate tracker paths match config; auto-reinitialize on mismatch.

#### 7. Compatibility Route Duplicates Data Loading
**File:** `web_server.py:146-159`
**Impact:** `get_recipes_compat()` duplicates recipes loading logic.
**Fix:** After migration complete, remove compatibility shim.

#### 8. Duplicate Path Utility
**File:** `web_server.py:35-41`
```python
def get_bundled_path():  # Also exists in app/utils/paths.py
```
**Fix:** Remove and import from paths.py.

### Medium Severity Issues

1. **Cache misses repeated for same log file** - Each quest endpoint parses same log
2. **File stat() calls repeated** in cache checks (cache_service.py)
3. **Quest search O(n)** without indexing (quests.py:79-89)
4. **Storage location extraction duplicated** in crafting.py
5. **Recursive visited set copying inefficient** (crafting.py:317)
6. **Vendor structure inconsistent** across endpoints
7. **Recipe ID validation too permissive** (validation.py:219)
8. **Traceback exposed in debug mode** (factory.py:195)
9. **CORS hardcoded with port 5000** (factory.py:113-122)
10. **Fallback app lacks routes** (web_server.py:51-58)

---

## Part 2: Main UI (index.html) Audit

### Critical Issue

#### recipeQuantities Type Inconsistency
**Lines:** 2684, 2728, 3763
```javascript
// Line 3763 - stores number:
recipeQuantities[recipeId] = 1;

// Lines 2684, 2728 - reads object:
recipeQuantities[recipe.id]?.quantity || 1
```
**Impact:** Accessing `.quantity` on a number returns undefined; recipes show wrong quantities.
**Fix:** Use consistent data structure throughout.

### High Severity Issues

#### 1. Material Rendering Duplicated 5+ Times
**Lines:** 1413-1423, 1484-1496, 1766-1776, 2038-2054, 2127-2137, 2364-2368, 4250-4354
```javascript
// Identical pattern appears 5+ times:
let icon = '🏦';
if (loc.toLowerCase().includes('dream')) icon = '💤';
else if (loc.toLowerCase().includes('saddlebag')) icon = '🎒';
```
**Fix:** Extract to `getStorageIcon(location)` utility function.

#### 2. Quest/Recipe List Building Duplicated 4+ Times
**Lines:** 1078-1210, 1244-1307, 1907-1964, 2662-2720
**Fix:** Extract to `buildItemListHtml(items, groupBy, renderFn)`.

#### 3. DOM Elements Queried Multiple Times
**Lines:** 779-784, 999-1004
```javascript
// Same elements queried in initializeTab() and switchTab():
document.getElementById('questSearchBox')
document.getElementById('craftingSearchBox')
```
**Fix:** Cache element references at module level.

#### 4. Race Conditions in Tab Switching
**Lines:** 811-816, 1017-1019
```javascript
// Rapid tab switches cause multiple async chains:
switchTab('crafting')  // starts loadCraftingRecipes()
switchTab('quests')    // starts loadActiveQuests() before first finishes
```
**Fix:** Implement abort controller or request cancellation.

#### 5. Double Re-render on Quest Pin
**Line:** 1150-1151
```javascript
onclick="toggleQuestPin(...); renderAllQuestsView()"
// toggleQuestPin already calls renderAllQuestsView internally!
```
**Fix:** Remove redundant `renderAllQuestsView()` from onclick.

#### 6. Parallel API Calls Without Batching
**Lines:** 1323-1333, 1539-1547
```javascript
// Fetches each quest detail individually - 20+ parallel requests:
for (const questId of readyQuestIds) {
    fetch(`/api/quest/${questId}`)
}
```
**Fix:** Implement batch endpoint or client-side caching.

#### 7. Craftability Check O(n³) Complexity
**Lines:** 2319-2391
```javascript
// For each recipe, for each ingredient, for each sub-recipe...
checkRecipeCraftability()  // Called after every inventory load
```
**Fix:** Implement memoization; cache craftability results.

### Medium Severity Issues (39 total)

Key patterns:
- **Refresh timer runs when no quest selected** (line 831)
- **Set operations not debounced** for localStorage (lines 3754-3776)
- **Character search listener added before tab loads** (line 4742)
- **No loading state shown** during async operations
- **Promise.all fails entirely** if any request fails (line 2173)
- **escapeHtml creates DOM element per call** (line 4735)

---

## Part 3: Overlay (overlay.html) Audit

### Timer/Interval Analysis

| Timer | Interval | Ops/Minute | Purpose |
|-------|----------|------------|---------|
| checkThemeSync | 1000ms | 60 | DOM reads/writes for theme |
| syncPinnedQuests | 1000ms | 60 | JSON.parse + Set creation |
| loadData | 3000ms | 20 | API calls |
| updateTimestamp | 1000ms | 60 | DOM text update |
| **TOTAL** | - | **200** | Combined operations |

**Impact:** 200+ operations per minute; high CPU/battery usage.
**Fix:** Replace polling with storage event listeners:
```javascript
window.addEventListener('storage', (e) => {
    if (e.key === 'storagebuddy-theme') loadTheme();
    if (e.key === 'pinnedQuests') syncPinnedQuests();
});
```

### High Severity Issues

#### 1. Material Aggregation Logic Duplicated
**Lines:** 1074-1172 and 1174-1278
```javascript
// Near-identical aggregation in renderPinnedRecipes() and renderReadyRecipes()
const aggregatedMaterials = {};
for (const recipe of allRecipes) {
    for (const mat of recipe.materials) {
        // ... identical logic
    }
}
```
**Fix:** Extract to `aggregateMaterials(recipes)` function.

#### 2. Ready View Filter Incomplete
**Lines:** 866-880
```javascript
// Only checks is_buyable and is_craftable, not gatherable items
const canObtainAll = q.items.every(item => {
    if (item.is_buyable && item.favor_met) return true;
    if (item.is_craftable && item.recipe?.has_skill) return true;
    return false;  // Gathered items return false incorrectly
});
```
**Fix:** Add gather-able items consideration or documentation.

#### 3. Server Restart Recovery Logic Flawed
**Lines:** 1004-1016
```javascript
// Assumes empty = server lost data, but could be intentional clear
if (allRecipes.length === 0) {
    await syncLocalPinsToServer(localPins);  // May overwrite user intent
}
```
**Fix:** Add server state check before auto-syncing.

### Medium Severity Issues (11 total)

- Storage location rendering duplicated (lines 933-970, 1116-1151)
- Wiki link generation duplicated
- Region selector always rebuilds even if unchanged
- No visibility API check (fetches when hidden)
- Cross-window sync uses polling instead of events

---

## Recommended Refactoring Priority

### Phase 1: Critical Fixes (Immediate)
1. Fix `recipeQuantities` type inconsistency
2. Change log file mode from 'w' to 'a'
3. Fix thread-safety in `_recipe_selections`

### Phase 2: High-Impact Consolidation (1-2 days)
1. Extract storage icon utility function
2. Extract material rendering utility
3. Replace overlay polling with storage events
4. Consolidate recipe/vendor loading in backend

### Phase 3: Performance Optimization (2-3 days)
1. Implement request deduplication/cancellation
2. Add memoization for craftability checks
3. Cache DOM element references
4. Implement batch API endpoints

### Phase 4: Code Quality (Ongoing)
1. Extract shared HTML rendering functions
2. Consolidate quest/recipe list builders
3. Add request-level caching for log parsing
4. Standardize error handling patterns

---

## API Call Analysis

### Main UI (per minute, typical usage)
- Auto-refresh: 12 calls (5s interval)
- Tab switches: 4-8 calls per switch
- Pin/unpin: 2 calls per action
- **Total typical:** 20-30 calls/minute

### Overlay (per minute)
- Auto-refresh: 20 calls (3s interval)
- Theme sync: 0 (polling, no network)
- Pin sync: 0 (polling, no network)
- **Total:** 20 calls/minute

### Combined worst case: 50+ API calls/minute

---

## Test Coverage Gaps

Based on code analysis, these areas lack test coverage:
1. Race conditions in async tab switching
2. Recipe quantity data structure handling
3. Cross-window localStorage sync
4. Server restart recovery scenarios
5. Edge cases in craftability recursion

---

## Appendix: Files Analyzed

### Python (23 files)
- app/routes/*.py (6 files)
- app/services/*.py (6 files)
- app/utils/*.py (6 files)
- app/factory.py
- web_server.py
- config.py
- vendor_hints.py
- data_updater.py

### JavaScript/HTML (4 files)
- templates/index.html (~5000 lines JS)
- templates/overlay.html (~1500 lines JS)
- templates/setup.html
- static/themes.css

---

## Resolution Status (March 12, 2026)

### Completed Fixes

| Issue | Resolution |
|-------|------------|
| recipeQuantities type inconsistency | Fixed - now stores numbers consistently |
| Log file mode='w' | Fixed - changed to mode='a' for append |
| Thread-unsafe _recipe_selections | Fixed - using threading.Lock() |
| Recipe loading duplication | Consolidated via ItemResolutionService |
| Storage icon duplication | Extracted to getStorageIcon() utility |
| Overlay polling timers | Replaced with storage event listeners |
| Double re-render on quest pin | Removed redundant render calls from onclick handlers |
| DOM element caching | Added DOM object with cached references |
| loadActiveQuests cancelableFetch bug | Fixed AbortController usage |

### Intentional Design Decisions (Documented in Code)

| Flagged Issue | Resolution |
|---------------|------------|
| **Visibility API not used** | INTENTIONAL: Browser Visibility API only detects tab switches/minimize, not windows behind other applications. StorageBuddy runs behind the game window, so refresh must continue. See comment near setInterval(refreshCurrentQuest). |
| **Material rendering duplicated 5+ times** | INTENTIONAL: Each view has different layout requirements (columns, grouping, metadata). Core logic extracted to getStorageIcon() and categorizeMaterial(). HTML templates remain view-specific for maintainability. See MATERIAL RENDERING ARCHITECTURE comment. |
| **Craftability O(n³) complexity** | ANALYZED: Actual complexity is O(n*k) where k≈1-5 ingredients/recipe. Memoization exists via _categorizeMaterialCache. Further optimization impractical due to recursive cycle detection. See CRAFTABILITY CACHING STRATEGY comment. |

### Remaining Items (Lower Priority)

| Issue | Status |
|-------|--------|
| Batch API endpoints | Not implemented - current request volume acceptable |
| Web Worker for craftability | Not needed - current performance acceptable |
| Request-level log caching | Deferred - cache service provides adequate performance |

---

*Report generated by automated code audit on overlay-debug-audit branch*
*Resolution status updated: March 12, 2026*
