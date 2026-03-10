// StorageBuddy Extension - Popup Script

const API_URL = 'http://127.0.0.1:5000';

let currentTab = 'quests';
let currentView = 'all';
let currentRegion = '';
let craftingView = 'all'; // 'all', 'ready', or 'shopping'
let lastUpdateTime = Date.now();
let isConnected = false;
let allQuests = []; // Cache quests for filtering
let allRecipes = []; // Cache recipes for crafting views

// Load saved preferences
chrome.storage.local.get(['tab', 'view', 'region', 'craftingView'], (result) => {
    if (result.tab) {
        currentTab = result.tab;
        switchTab(currentTab);
    }
    if (result.view) {
        currentView = result.view;
        document.getElementById('viewSelector').value = currentView;
    }
    if (result.region) {
        currentRegion = result.region;
    }
    if (result.craftingView) {
        craftingView = result.craftingView;
        document.getElementById('craftingViewSelector').value = craftingView;
    }
});

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const tab = e.target.dataset.tab;
        switchTab(tab);
        chrome.storage.local.set({ tab });
    });
});

function switchTab(tab) {
    currentTab = tab;

    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // Show/hide controls
    document.getElementById('questControls').style.display = tab === 'quests' ? 'flex' : 'none';
    document.getElementById('craftingControls').style.display = tab === 'crafting' ? 'flex' : 'none';

    loadData();
}

// View selector change
document.getElementById('viewSelector').addEventListener('change', (e) => {
    currentView = e.target.value;
    chrome.storage.local.set({ view: currentView });
    loadData();
});

// Region selector change
document.getElementById('regionSelector').addEventListener('change', (e) => {
    currentRegion = e.target.value;
    chrome.storage.local.set({ region: currentRegion });
    renderFilteredQuests();
});

// Crafting view selector change
document.getElementById('craftingViewSelector').addEventListener('change', (e) => {
    craftingView = e.target.value;
    chrome.storage.local.set({ craftingView });
    renderCraftingView();
});

function updateRegionSelector(quests) {
    const regionSelector = document.getElementById('regionSelector');
    const regions = [...new Set(quests.map(q => q.location).filter(Boolean))].sort();

    // Remember current selection
    const currentSelection = regionSelector.value;

    // Clear and rebuild options
    regionSelector.innerHTML = '<option value="">All Regions</option>';
    regions.forEach(region => {
        const option = document.createElement('option');
        option.value = region;
        option.textContent = region;
        regionSelector.appendChild(option);
    });

    // Restore selection if still valid
    if (currentRegion && regions.includes(currentRegion)) {
        regionSelector.value = currentRegion;
    } else if (currentSelection && regions.includes(currentSelection)) {
        regionSelector.value = currentSelection;
    }
}

function renderFilteredQuests() {
    const content = document.getElementById('content');
    let quests = allQuests;

    // Apply region filter
    if (currentRegion) {
        quests = quests.filter(q => q.location === currentRegion);
    }

    if (quests.length === 0) {
        const emptyMessage = currentRegion
            ? `No quests in ${currentRegion}`
            : (currentView === 'ready' ? 'No quests ready to complete' : 'No active quests with items');
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p>${emptyMessage}</p>
            </div>
        `;
        document.getElementById('itemCount').textContent = '0 quests';
        return;
    }

    // Render quests
    const questsHtml = quests.map(quest => {
        const isReady = quest.items.every(item => item.have >= item.need);
        const isBuyable = !isReady && quest.items.some(item => item.vendor_info);
        const questClass = isReady ? 'quest-group ready' : (isBuyable ? 'quest-group buyable' : 'quest-group');

        const itemsHtml = quest.items.map(item => {
            const isCompleted = item.have >= item.need;
            const itemClass = isCompleted ? 'item completed' : 'item';

            let detailsHtml = '';
            const total = (item.in_inventory || 0) + (item.in_storage || 0);
            if (total > 0) {
                let locationParts = [];
                if (item.in_inventory) locationParts.push(`📦 Inventory: ${item.in_inventory}`);
                if (item.storage_locations) {
                    for (const [location, count] of Object.entries(item.storage_locations)) {
                        let icon = '🏦';
                        let shortName = location;
                        if (location.toLowerCase().includes('saddlebag')) {
                            icon = '🎒';
                            shortName = 'Saddlebag';
                        }
                        locationParts.push(`${icon} ${shortName}: ${count}`);
                    }
                }
                if (locationParts.length > 0) {
                    detailsHtml += `<div class="item-details">${locationParts.join(' • ')}</div>`;
                }
            }
            if (item.vendor_info && !isCompleted) {
                detailsHtml += `<div class="vendor-info">🛒 ${escapeHtml(item.vendor_info)}</div>`;
            }

            return `
                <div class="${itemClass}">
                    <span class="item-name">${escapeHtml(item.name)}</span>
                    <span class="item-progress">${item.have}/${item.need}</span>
                    ${detailsHtml}
                </div>
            `;
        }).join('');

        return `
            <div class="${questClass}">
                <div class="quest-name">${escapeHtml(quest.name)}</div>
                <div class="item-list">${itemsHtml}</div>
            </div>
        `;
    }).join('');

    content.innerHTML = questsHtml;
    document.getElementById('itemCount').textContent = `${quests.length} quest${quests.length !== 1 ? 's' : ''}`;
}

async function loadData() {
    const content = document.getElementById('content');
    const statusEl = document.getElementById('connectionStatus');

    try {
        if (currentTab === 'quests') {
            await loadQuestData(content);
        } else {
            await loadCraftingData(content);
        }

        // Update connection status
        isConnected = true;
        statusEl.textContent = 'Connected';
        statusEl.className = 'connection-status connected';

        lastUpdateTime = Date.now();
        updateTimestamp();
    } catch (error) {
        console.error('Error loading data:', error);
        isConnected = false;
        statusEl.textContent = 'Disconnected';
        statusEl.className = 'connection-status disconnected';

        content.innerHTML = `
            <div class="error-state">
                <div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>
                Cannot connect to StorageBuddy
                <code>Make sure the app is running at localhost:5000</code>
            </div>
        `;
    }
}

async function loadQuestData(content) {
    // Map view to API parameter
    const viewParam = currentView === 'ready' ? 'completable' : 'active';
    const response = await fetch(`${API_URL}/api/overlay_data?view=${viewParam}`);

    if (!response.ok) {
        throw new Error('Server not responding');
    }

    const data = await response.json();

    // Cache quests for filtering
    allQuests = data.quests;

    // Update region selector with available regions
    updateRegionSelector(allQuests);

    // Render with current filter
    renderFilteredQuests();
}

async function loadCraftingData(content) {
    const response = await fetch(`${API_URL}/api/shopping_list`);

    if (!response.ok) {
        throw new Error('Server not responding');
    }

    const data = await response.json();

    // Cache recipes for view switching
    allRecipes = data.recipes || [];

    // Render based on current view
    renderCraftingView();
}

function renderCraftingView() {
    const content = document.getElementById('content');

    if (allRecipes.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔨</div>
                <p>No recipes pinned</p>
                <p style="font-size: 11px; margin-top: 8px; color: rgba(255,255,255,0.4);">
                    Pin recipes in StorageBuddy to see them here
                </p>
            </div>
        `;
        document.getElementById('itemCount').textContent = '0 recipes';
        return;
    }

    if (craftingView === 'shopping') {
        renderShoppingCart(content);
    } else if (craftingView === 'ready') {
        renderReadyRecipes(content);
    } else {
        renderPinnedRecipes(content);
    }
}

function renderPinnedRecipes(content) {
    // Render recipes and their materials (original view)
    let totalMaterials = 0;
    const recipesHtml = allRecipes.map(recipe => {
        const materialsHtml = recipe.materials.map(mat => {
            const isCompleted = mat.have >= mat.need;
            const itemClass = isCompleted ? 'item completed' : 'item';
            totalMaterials++;

            let detailsHtml = '';

            // Location info
            const total = (mat.in_inventory || 0) + (mat.in_storage || 0);
            if (total > 0) {
                let locationParts = [];
                if (mat.in_inventory) locationParts.push(`📦 Inventory: ${mat.in_inventory}`);

                if (mat.storage_locations) {
                    for (const [location, count] of Object.entries(mat.storage_locations)) {
                        let icon = '🏦';
                        let shortName = location;
                        if (location.toLowerCase().includes('saddlebag')) {
                            icon = '🎒';
                            shortName = 'Saddlebag';
                        }
                        locationParts.push(`${icon} ${shortName}: ${count}`);
                    }
                } else if (mat.in_storage) {
                    locationParts.push(`🏦 Storage: ${mat.in_storage}`);
                }

                if (locationParts.length > 0) {
                    detailsHtml += `<div class="item-details">${locationParts.join(' • ')}</div>`;
                }
            }

            // Vendor info
            if (mat.vendor_info && !isCompleted) {
                detailsHtml += `<div class="vendor-info">🛒 ${escapeHtml(mat.vendor_info)}</div>`;
            }

            return `
                <div class="${itemClass}">
                    <span class="item-name">${escapeHtml(mat.name)}</span>
                    <span class="item-progress">${mat.have}/${mat.need}</span>
                    ${detailsHtml}
                </div>
            `;
        }).join('');

        // Determine recipe status (craftable, buyable, or default)
        const isReady = recipe.materials.every(mat => mat.have >= mat.need);
        const isBuyable = !isReady && recipe.materials.some(mat => mat.vendor_info);
        const recipeClass = isReady ? 'recipe-group ready' : (isBuyable ? 'recipe-group buyable' : 'recipe-group');

        return `
            <div class="${recipeClass}">
                <div class="recipe-header">
                    <span class="recipe-name">${escapeHtml(recipe.name)}</span>
                    <span class="recipe-qty">×${recipe.quantity}</span>
                </div>
                <div class="recipe-skill">${escapeHtml(recipe.skill)} • Level ${recipe.level}</div>
                <div class="item-list" style="margin-top: 8px;">${materialsHtml}</div>
            </div>
        `;
    }).join('');

    content.innerHTML = recipesHtml;
    document.getElementById('itemCount').textContent = `${allRecipes.length} recipe${allRecipes.length !== 1 ? 's' : ''}, ${totalMaterials} materials`;
}

function renderReadyRecipes(content) {
    // Filter to recipes where all materials are available
    const readyRecipes = allRecipes.filter(recipe =>
        recipe.materials.every(mat => mat.have >= mat.need)
    );

    if (readyRecipes.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📦</div>
                <p>No recipes ready to craft</p>
                <p style="font-size: 11px; margin-top: 8px; color: rgba(255,255,255,0.4);">
                    Gather more materials or check the Shopping Cart
                </p>
            </div>
        `;
        document.getElementById('itemCount').textContent = '0 recipes ready';
        return;
    }

    // Render ready recipes (simplified view - all materials are complete)
    const recipesHtml = readyRecipes.map(recipe => {
        const materialsHtml = recipe.materials.map(mat => {
            return `
                <div class="item completed">
                    <span class="item-name">${escapeHtml(mat.name)}</span>
                    <span class="item-progress">${mat.have}/${mat.need}</span>
                </div>
            `;
        }).join('');

        return `
            <div class="recipe-group ready">
                <div class="recipe-header">
                    <span class="recipe-name">${escapeHtml(recipe.name)}</span>
                    <span class="recipe-qty">×${recipe.quantity}</span>
                </div>
                <div class="recipe-skill">${escapeHtml(recipe.skill)} • Level ${recipe.level}</div>
                <div class="item-list" style="margin-top: 8px;">${materialsHtml}</div>
            </div>
        `;
    }).join('');

    content.innerHTML = recipesHtml;
    document.getElementById('itemCount').textContent = `${readyRecipes.length} recipe${readyRecipes.length !== 1 ? 's' : ''} ready`;
}

function renderShoppingCart(content) {
    // Get all vendor-purchasable items needed across pinned recipes
    const shoppingItems = {};

    for (const recipe of allRecipes) {
        for (const mat of recipe.materials) {
            const missing = mat.need - mat.have;
            // Only include items that are missing AND have vendors
            if (missing <= 0 || !mat.vendors || mat.vendors.length === 0) continue;

            if (!shoppingItems[mat.name]) {
                shoppingItems[mat.name] = {
                    name: mat.name,
                    totalNeed: 0,
                    totalHave: 0,
                    vendors: mat.vendors,
                    recipes: []
                };
            }

            shoppingItems[mat.name].totalNeed += mat.need;
            shoppingItems[mat.name].totalHave += mat.have;
            shoppingItems[mat.name].recipes.push(`${recipe.name} (×${recipe.quantity})`);
        }
    }

    const items = Object.values(shoppingItems);

    if (items.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🛒</div>
                <p>Shopping cart is empty</p>
                <p style="font-size: 11px; margin-top: 8px; color: rgba(255,255,255,0.4);">
                    No vendor-purchasable materials needed
                </p>
            </div>
        `;
        document.getElementById('itemCount').textContent = '0 items to buy';
        return;
    }

    // Sort by vendor location for efficient shopping trips
    items.sort((a, b) => {
        const aLoc = a.vendors[0]?.location || '';
        const bLoc = b.vendors[0]?.location || '';
        if (aLoc !== bLoc) return aLoc.localeCompare(bLoc);
        return a.name.localeCompare(b.name);
    });

    // Calculate total cost
    let totalCost = 0;
    items.forEach(item => {
        const missing = item.totalNeed - item.totalHave;
        const price = item.vendors[0]?.price || 0;
        totalCost += missing * price;
    });

    const itemsHtml = items.map(item => {
        const missing = item.totalNeed - item.totalHave;
        const vendor = item.vendors[0];
        const itemCost = missing * (vendor?.price || 0);

        return `
            <div class="shopping-item buyable">
                <div class="shopping-header">
                    <span class="item-name">${escapeHtml(item.name)}</span>
                    <span class="item-progress">Buy ${missing}</span>
                </div>
                <div class="vendor-info">
                    🛒 ${escapeHtml(vendor.vendor)} (${escapeHtml(vendor.location)})<br>
                    💰 ${vendor.price}g each = ${itemCost}g total<br>
                    ⭐ Requires: ${escapeHtml(vendor.favor)} favor
                </div>
                <div class="item-recipes">For: ${item.recipes.join(', ')}</div>
            </div>
        `;
    }).join('');

    content.innerHTML = `
        <div class="shopping-summary">
            <span>Total: ${items.length} item${items.length !== 1 ? 's' : ''}</span>
            <span class="shopping-total">💰 ${totalCost}g</span>
        </div>
        ${itemsHtml}
    `;
    document.getElementById('itemCount').textContent = `${items.length} item${items.length !== 1 ? 's' : ''} to buy`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateTimestamp() {
    const secondsAgo = Math.floor((Date.now() - lastUpdateTime) / 1000);
    let text;
    if (secondsAgo < 5) {
        text = 'Just now';
    } else if (secondsAgo < 60) {
        text = `${secondsAgo}s ago`;
    } else {
        text = `${Math.floor(secondsAgo / 60)}m ago`;
    }
    document.getElementById('lastUpdate').textContent = text;
}

// Pop out to separate window
document.getElementById('popoutBtn').addEventListener('click', () => {
    const width = 360;
    const height = 500;
    const left = window.screenX + 50;
    const top = window.screenY + 50;

    const popoutUrl = chrome.runtime.getURL('popup.html') + '?popout=true';
    window.open(
        popoutUrl,
        'StorageBuddy Overlay',
        `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );

    window.close();
});

// Check if this is a popped out window and adjust UI
const urlParams = new URLSearchParams(window.location.search);
const isPopout = urlParams.get('popout') === 'true';

if (isPopout) {
    // Hide the pop-out button in popped out window
    document.getElementById('popoutBtn').style.display = 'none';

    // Adjust body for standalone window
    document.body.style.width = '100%';
    document.body.style.minHeight = '100vh';
}

// Initial load
loadData();

// Auto-refresh every 3 seconds
setInterval(loadData, 3000);

// Update timestamp every second
setInterval(updateTimestamp, 1000);
