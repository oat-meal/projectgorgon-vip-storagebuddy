// Quest Tracker Extension - Popup Script

let currentView = 'completable';
let lastUpdateTime = Date.now();
let currentZoom = 100;
const API_URL = 'http://127.0.0.1:5000';

// Load saved preferences
chrome.storage.local.get(['view', 'zoom'], (result) => {
    if (result.view) {
        currentView = result.view;
        document.getElementById('viewSelector').value = currentView;
    }
    if (result.zoom) {
        currentZoom = result.zoom;
        applyZoom(currentZoom);
    }
});

// View selector change
document.getElementById('viewSelector').addEventListener('change', (e) => {
    currentView = e.target.value;
    chrome.storage.local.set({ view: currentView });
    loadData();
});

// Zoom controls
document.getElementById('zoomIn').addEventListener('click', () => {
    currentZoom = Math.min(200, currentZoom + 10);
    applyZoom(currentZoom);
    chrome.storage.local.set({ zoom: currentZoom });
});

document.getElementById('zoomOut').addEventListener('click', () => {
    currentZoom = Math.max(50, currentZoom - 10);
    applyZoom(currentZoom);
    chrome.storage.local.set({ zoom: currentZoom });
});

function applyZoom(zoom) {
    document.body.style.transform = `scale(${zoom / 100})`;
    document.body.style.transformOrigin = 'top left';
    document.body.style.width = `${100 / (zoom / 100)}%`;
    document.body.style.height = `${100 / (zoom / 100)}%`;
    document.getElementById('zoomValue').textContent = `${zoom}%`;
}

async function loadData() {
    const content = document.getElementById('content');

    try {
        const response = await fetch(`${API_URL}/api/overlay_data?view=${currentView}`);

        if (!response.ok) {
            throw new Error('Server not responding');
        }

        const data = await response.json();

        if (data.quests.length === 0) {
            content.innerHTML = '<div class="empty-state">No quests found</div>';
            document.getElementById('questCount').textContent = '0 quests';
            return;
        }

        // Group items by quest
        const questsHtml = data.quests.map(quest => {
            const itemsHtml = quest.items.map(item => {
                const isCompleted = item.have >= item.need;
                const progressClass = isCompleted ? 'completed' : 'incomplete';
                const itemClass = isCompleted ? 'item completed' : 'item';

                return `
                    <div class="${itemClass}">
                        <div class="item-name">${escapeHtml(item.name)}</div>
                        <div class="item-progress ${progressClass}">${item.have}/${item.need}</div>
                    </div>
                `;
            }).join('');

            return `
                <div class="quest-group">
                    <div class="quest-name">${escapeHtml(quest.name)}</div>
                    <div class="item-list">${itemsHtml}</div>
                </div>
            `;
        }).join('');

        content.innerHTML = questsHtml;
        document.getElementById('questCount').textContent = `${data.quests.length} quest${data.quests.length !== 1 ? 's' : ''}`;

        lastUpdateTime = Date.now();
        updateTimestamp();
    } catch (error) {
        console.error('Error loading data:', error);
        content.innerHTML = `
            <div class="error-state">
                Cannot connect to Quest Helper<br>
                Make sure <code>launcher.py</code> is running
            </div>
        `;
    }
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

// Initial load
loadData();

// Auto-refresh every 3 seconds
setInterval(loadData, 3000);

// Update timestamp every second
setInterval(updateTimestamp, 1000);
