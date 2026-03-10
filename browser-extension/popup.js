// StorageBuddy Extension - Popup Script

const API_URL = 'http://127.0.0.1:5000';

let currentTab = 'quests';
let currentView = 'all';
let currentZoom = 100;
let lastUpdateTime = Date.now();
let isConnected = false;

// Load saved preferences
chrome.storage.local.get(['tab', 'view', 'zoom'], (result) => {
    if (result.tab) {
        currentTab = result.tab;
        switchTab(currentTab);
    }
    if (result.view) {
        currentView = result.view;
        document.getElementById('viewSelector').value = currentView;
    }
    if (result.zoom) {
        currentZoom = result.zoom;
        applyZoom(currentZoom);
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

// Zoom controls
document.getElementById('zoomIn').addEventListener('click', () => {
    currentZoom = Math.min(150, currentZoom + 10);
    applyZoom(currentZoom);
    chrome.storage.local.set({ zoom: currentZoom });
});

document.getElementById('zoomOut').addEventListener('click', () => {
    currentZoom = Math.max(70, currentZoom - 10);
    applyZoom(currentZoom);
    chrome.storage.local.set({ zoom: currentZoom });
});

function applyZoom(zoom) {
    document.getElementById('content').style.fontSize = `${zoom}%`;
    document.getElementById('zoomValue').textContent = `${zoom}%`;
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

    if (data.quests.length === 0) {
        const emptyMessage = currentView === 'ready'
            ? 'No quests ready to complete'
            : 'No active quests with items';
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
    const questsHtml = data.quests.map(quest => {
        const isReady = quest.items.every(item => item.have >= item.need);
        const isBuyable = !isReady && quest.items.some(item => item.vendor_info);
        const questClass = isReady ? 'quest-group ready' : (isBuyable ? 'quest-group buyable' : 'quest-group');

        const itemsHtml = quest.items.map(item => {
            const isCompleted = item.have >= item.need;
            const itemClass = isCompleted ? 'item completed' : 'item';

            // Build details section
            let detailsHtml = '';

            // Location info
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

            // Vendor info
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
    document.getElementById('itemCount').textContent = `${data.quests.length} quest${data.quests.length !== 1 ? 's' : ''}`;
}

async function loadCraftingData(content) {
    const response = await fetch(`${API_URL}/api/shopping_list`);

    if (!response.ok) {
        throw new Error('Server not responding');
    }

    const data = await response.json();

    if (!data.recipes || data.recipes.length === 0) {
        content.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔨</div>
                <p>No recipes selected</p>
                <p style="font-size: 11px; margin-top: 8px; color: rgba(255,255,255,0.4);">
                    Select recipes in StorageBuddy to see your shopping list here
                </p>
            </div>
        `;
        document.getElementById('itemCount').textContent = '0 recipes';
        return;
    }

    // Render recipes and their materials
    let totalMaterials = 0;
    const recipesHtml = data.recipes.map(recipe => {
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
    document.getElementById('itemCount').textContent = `${data.recipes.length} recipe${data.recipes.length !== 1 ? 's' : ''}, ${totalMaterials} materials`;
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
    // Get current window position for placing popup nearby
    const width = 360;
    const height = 500;
    const left = window.screenX + 50;
    const top = window.screenY + 50;

    // Open popup.html in a new window
    const popoutUrl = chrome.runtime.getURL('popup.html') + '?popout=true';
    window.open(
        popoutUrl,
        'StorageBuddy Overlay',
        `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes`
    );

    // Close the extension popup
    window.close();
});

// Check if this is a popped out window and adjust UI
const urlParams = new URLSearchParams(window.location.search);
const isPopout = urlParams.get('popout') === 'true';

if (isPopout) {
    // Hide the pop-out button in popped out window
    document.getElementById('popoutBtn').style.display = 'none';

    // Show the pin button
    document.getElementById('pinBtn').style.display = 'flex';

    // Adjust body for standalone window
    document.body.style.width = '100%';
    document.body.style.minHeight = '100vh';

    // Initialize pin button state
    initPinButton();
}

// Pin button functionality
async function initPinButton() {
    const pinBtn = document.getElementById('pinBtn');

    // Get current state from storage
    chrome.storage.local.get(['alwaysOnTop'], (result) => {
        updatePinButton(result.alwaysOnTop || false);
    });
}

function updatePinButton(isPinned) {
    const pinBtn = document.getElementById('pinBtn');
    if (isPinned) {
        pinBtn.classList.add('pinned');
        pinBtn.innerHTML = '<span>📌</span> Pinned';
        pinBtn.title = 'Always-on-top enabled - Use PowerToys or window manager to pin';
    } else {
        pinBtn.classList.remove('pinned');
        pinBtn.innerHTML = '<span>📌</span> Pin';
        pinBtn.title = 'Mark as always-on-top (requires PowerToys or window manager)';
    }
}

document.getElementById('pinBtn').addEventListener('click', async () => {
    chrome.storage.local.get(['alwaysOnTop'], (result) => {
        const newState = !result.alwaysOnTop;
        chrome.storage.local.set({ alwaysOnTop: newState }, () => {
            updatePinButton(newState);

            // Show a helpful tooltip on first pin
            if (newState) {
                showPinHelp();
            }
        });
    });
});

function showPinHelp() {
    // Check if we've shown the help before
    chrome.storage.local.get(['pinHelpShown'], (result) => {
        if (!result.pinHelpShown) {
            chrome.storage.local.set({ pinHelpShown: true });

            // Create and show a help tooltip
            const helpDiv = document.createElement('div');
            helpDiv.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(40, 40, 50, 0.98);
                border: 1px solid rgba(255, 193, 7, 0.5);
                border-radius: 8px;
                padding: 15px;
                max-width: 280px;
                z-index: 1000;
                box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            `;
            helpDiv.innerHTML = `
                <div style="color: #ffc107; font-weight: 600; margin-bottom: 8px;">📌 Always-on-Top</div>
                <div style="color: #ccc; font-size: 12px; line-height: 1.5;">
                    Chrome doesn't support native always-on-top for extension windows.<br><br>
                    <strong>Windows:</strong> Use <a href="https://learn.microsoft.com/en-us/windows/powertoys/" target="_blank" style="color: #667eea;">PowerToys</a> "Always on Top" (Win+Ctrl+T)<br><br>
                    <strong>Linux:</strong> Most window managers support pinning via titlebar menu or keyboard shortcut.
                </div>
                <button id="closePinHelp" style="
                    margin-top: 12px;
                    background: rgba(102, 126, 234, 0.3);
                    border: 1px solid rgba(102, 126, 234, 0.5);
                    border-radius: 4px;
                    color: #a8b2ff;
                    padding: 6px 12px;
                    cursor: pointer;
                    width: 100%;
                ">Got it!</button>
            `;
            document.body.appendChild(helpDiv);

            document.getElementById('closePinHelp').addEventListener('click', () => {
                helpDiv.remove();
            });

            // Auto-close after 10 seconds
            setTimeout(() => {
                if (helpDiv.parentNode) {
                    helpDiv.remove();
                }
            }, 10000);
        }
    });
}

// Initial load
loadData();

// Auto-refresh every 3 seconds
setInterval(loadData, 3000);

// Update timestamp every second
setInterval(updateTimestamp, 1000);
