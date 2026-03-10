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

// Check if Document Picture-in-Picture API is available
const isPipSupported = 'documentPictureInPicture' in window;

// Pop out to separate window (using Document PiP if available)
document.getElementById('popoutBtn').addEventListener('click', async () => {
    if (isPipSupported) {
        await openPictureInPicture();
    } else {
        // Fallback to regular window for unsupported browsers
        openRegularPopout();
    }
});

async function openPictureInPicture() {
    try {
        // Request a Picture-in-Picture window
        const pipWindow = await window.documentPictureInPicture.requestWindow({
            width: 360,
            height: 500
        });

        // Copy all styles to the PiP window
        copyStylesToPipWindow(pipWindow);

        // Clone the container to the PiP window
        const container = document.querySelector('.container');
        const pipContainer = container.cloneNode(true);

        // Set up the PiP document body
        pipWindow.document.body.style.margin = '0';
        pipWindow.document.body.style.padding = '0';
        pipWindow.document.body.style.background = 'rgb(20, 20, 30)';
        pipWindow.document.body.appendChild(pipContainer);

        // Hide the pop-out button in PiP window (already pinned)
        const pipPopoutBtn = pipWindow.document.getElementById('popoutBtn');
        if (pipPopoutBtn) pipPopoutBtn.style.display = 'none';

        // Show pinned indicator
        const pipPinBtn = pipWindow.document.getElementById('pinBtn');
        if (pipPinBtn) {
            pipPinBtn.style.display = 'flex';
            pipPinBtn.classList.add('pinned');
            pipPinBtn.innerHTML = '<span>📌</span> Pinned';
            pipPinBtn.title = 'This window stays on top';
            pipPinBtn.style.cursor = 'default';
        }

        // Set up interactivity in PiP window
        setupPipInteractivity(pipWindow, pipContainer);

        // Close the extension popup
        window.close();

    } catch (error) {
        console.error('Failed to open Picture-in-Picture:', error);
        // Fall back to regular popout
        openRegularPopout();
    }
}

function copyStylesToPipWindow(pipWindow) {
    // Copy inline styles from <style> tags
    document.querySelectorAll('style').forEach(style => {
        pipWindow.document.head.appendChild(style.cloneNode(true));
    });

    // Copy stylesheets
    for (const styleSheet of document.styleSheets) {
        try {
            const cssRules = [...styleSheet.cssRules].map(rule => rule.cssText).join('\n');
            const style = document.createElement('style');
            style.textContent = cssRules;
            pipWindow.document.head.appendChild(style);
        } catch (e) {
            // External stylesheets may throw SecurityError
            if (styleSheet.href) {
                const link = document.createElement('link');
                link.rel = 'stylesheet';
                link.href = styleSheet.href;
                pipWindow.document.head.appendChild(link);
            }
        }
    }
}

function setupPipInteractivity(pipWindow, pipContainer) {
    const pipDocument = pipWindow.document;

    // Track state for PiP window
    let pipCurrentTab = currentTab;
    let pipCurrentView = currentView;
    let pipCurrentZoom = currentZoom;

    // Tab switching
    pipDocument.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            pipCurrentTab = e.target.dataset.tab;

            // Update tab buttons
            pipDocument.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.tab === pipCurrentTab);
            });

            // Show/hide controls
            pipDocument.getElementById('questControls').style.display = pipCurrentTab === 'quests' ? 'flex' : 'none';
            pipDocument.getElementById('craftingControls').style.display = pipCurrentTab === 'crafting' ? 'flex' : 'none';

            // Save preference
            chrome.storage.local.set({ tab: pipCurrentTab });

            loadPipData();
        });
    });

    // View selector
    const viewSelector = pipDocument.getElementById('viewSelector');
    if (viewSelector) {
        viewSelector.addEventListener('change', (e) => {
            pipCurrentView = e.target.value;
            chrome.storage.local.set({ view: pipCurrentView });
            loadPipData();
        });
    }

    // Zoom controls
    const zoomIn = pipDocument.getElementById('zoomIn');
    const zoomOut = pipDocument.getElementById('zoomOut');
    const zoomValue = pipDocument.getElementById('zoomValue');
    const content = pipDocument.getElementById('content');

    if (zoomIn) {
        zoomIn.addEventListener('click', () => {
            pipCurrentZoom = Math.min(150, pipCurrentZoom + 10);
            content.style.fontSize = `${pipCurrentZoom}%`;
            zoomValue.textContent = `${pipCurrentZoom}%`;
            chrome.storage.local.set({ zoom: pipCurrentZoom });
        });
    }

    if (zoomOut) {
        zoomOut.addEventListener('click', () => {
            pipCurrentZoom = Math.max(70, pipCurrentZoom - 10);
            content.style.fontSize = `${pipCurrentZoom}%`;
            zoomValue.textContent = `${pipCurrentZoom}%`;
            chrome.storage.local.set({ zoom: pipCurrentZoom });
        });
    }

    // Data loading for PiP
    async function loadPipData() {
        const pipContent = pipDocument.getElementById('content');
        const pipStatus = pipDocument.getElementById('connectionStatus');
        const pipItemCount = pipDocument.getElementById('itemCount');
        const pipLastUpdate = pipDocument.getElementById('lastUpdate');

        try {
            if (pipCurrentTab === 'quests') {
                const viewParam = pipCurrentView === 'ready' ? 'completable' : 'active';
                const response = await fetch(`${API_URL}/api/overlay_data?view=${viewParam}`);
                if (!response.ok) throw new Error('Server not responding');
                const data = await response.json();

                if (data.quests.length === 0) {
                    const emptyMessage = pipCurrentView === 'ready' ? 'No quests ready to complete' : 'No active quests with items';
                    pipContent.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📋</div><p>${emptyMessage}</p></div>`;
                    pipItemCount.textContent = '0 quests';
                } else {
                    pipContent.innerHTML = renderQuests(data.quests);
                    pipItemCount.textContent = `${data.quests.length} quest${data.quests.length !== 1 ? 's' : ''}`;
                }
            } else {
                const response = await fetch(`${API_URL}/api/shopping_list`);
                if (!response.ok) throw new Error('Server not responding');
                const data = await response.json();

                if (!data.recipes || data.recipes.length === 0) {
                    pipContent.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔨</div><p>No recipes selected</p></div>`;
                    pipItemCount.textContent = '0 recipes';
                } else {
                    const result = renderRecipes(data.recipes);
                    pipContent.innerHTML = result.html;
                    pipItemCount.textContent = `${data.recipes.length} recipe${data.recipes.length !== 1 ? 's' : ''}, ${result.totalMaterials} materials`;
                }
            }

            pipStatus.textContent = 'Connected';
            pipStatus.className = 'connection-status connected';
            pipLastUpdate.textContent = 'Just now';

        } catch (error) {
            pipStatus.textContent = 'Disconnected';
            pipStatus.className = 'connection-status disconnected';
            pipContent.innerHTML = `<div class="error-state"><div style="font-size: 24px; margin-bottom: 10px;">⚠️</div>Cannot connect to StorageBuddy<code>Make sure the app is running at localhost:5000</code></div>`;
        }
    }

    // Initial load and auto-refresh
    loadPipData();
    const refreshInterval = setInterval(loadPipData, 3000);

    // Clean up when PiP window closes
    pipWindow.addEventListener('pagehide', () => {
        clearInterval(refreshInterval);
    });
}

// Render functions for PiP (same logic as main)
function renderQuests(quests) {
    return quests.map(quest => {
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
                        let icon = location.toLowerCase().includes('saddlebag') ? '🎒' : '🏦';
                        let shortName = location.toLowerCase().includes('saddlebag') ? 'Saddlebag' : location;
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

            return `<div class="${itemClass}"><span class="item-name">${escapeHtml(item.name)}</span><span class="item-progress">${item.have}/${item.need}</span>${detailsHtml}</div>`;
        }).join('');

        return `<div class="${questClass}"><div class="quest-name">${escapeHtml(quest.name)}</div><div class="item-list">${itemsHtml}</div></div>`;
    }).join('');
}

function renderRecipes(recipes) {
    let totalMaterials = 0;
    const html = recipes.map(recipe => {
        const materialsHtml = recipe.materials.map(mat => {
            const isCompleted = mat.have >= mat.need;
            const itemClass = isCompleted ? 'item completed' : 'item';
            totalMaterials++;
            let detailsHtml = '';

            const total = (mat.in_inventory || 0) + (mat.in_storage || 0);
            if (total > 0) {
                let locationParts = [];
                if (mat.in_inventory) locationParts.push(`📦 Inventory: ${mat.in_inventory}`);
                if (mat.storage_locations) {
                    for (const [location, count] of Object.entries(mat.storage_locations)) {
                        let icon = location.toLowerCase().includes('saddlebag') ? '🎒' : '🏦';
                        let shortName = location.toLowerCase().includes('saddlebag') ? 'Saddlebag' : location;
                        locationParts.push(`${icon} ${shortName}: ${count}`);
                    }
                } else if (mat.in_storage) {
                    locationParts.push(`🏦 Storage: ${mat.in_storage}`);
                }
                if (locationParts.length > 0) {
                    detailsHtml += `<div class="item-details">${locationParts.join(' • ')}</div>`;
                }
            }
            if (mat.vendor_info && !isCompleted) {
                detailsHtml += `<div class="vendor-info">🛒 ${escapeHtml(mat.vendor_info)}</div>`;
            }

            return `<div class="${itemClass}"><span class="item-name">${escapeHtml(mat.name)}</span><span class="item-progress">${mat.have}/${mat.need}</span>${detailsHtml}</div>`;
        }).join('');

        const isReady = recipe.materials.every(mat => mat.have >= mat.need);
        const isBuyable = !isReady && recipe.materials.some(mat => mat.vendor_info);
        const recipeClass = isReady ? 'recipe-group ready' : (isBuyable ? 'recipe-group buyable' : 'recipe-group');

        return `<div class="${recipeClass}"><div class="recipe-header"><span class="recipe-name">${escapeHtml(recipe.name)}</span><span class="recipe-qty">×${recipe.quantity}</span></div><div class="recipe-skill">${escapeHtml(recipe.skill)} • Level ${recipe.level}</div><div class="item-list" style="margin-top: 8px;">${materialsHtml}</div></div>`;
    }).join('');

    return { html, totalMaterials };
}

function openRegularPopout() {
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
}

// Check if this is a popped out window (fallback mode) and adjust UI
const urlParams = new URLSearchParams(window.location.search);
const isPopout = urlParams.get('popout') === 'true';

if (isPopout) {
    // Hide the pop-out button in popped out window
    document.getElementById('popoutBtn').style.display = 'none';

    // Show the pin button with instructions for fallback mode
    const pinBtn = document.getElementById('pinBtn');
    pinBtn.style.display = 'flex';
    pinBtn.innerHTML = '<span>📌</span> Pin (manual)';
    pinBtn.title = 'Use your OS window manager to pin this window on top';

    // Adjust body for standalone window
    document.body.style.width = '100%';
    document.body.style.minHeight = '100vh';
}

// Update the popout button text based on PiP support
if (isPipSupported) {
    document.getElementById('popoutBtn').innerHTML = '<span>📌</span> Pop Out (Pinned)';
    document.getElementById('popoutBtn').title = 'Open in always-on-top window';
}

// Initial load
loadData();

// Auto-refresh every 3 seconds
setInterval(loadData, 3000);

// Update timestamp every second
setInterval(updateTimestamp, 1000);
