// Background service worker for Quest Tracker extension

// Handle messages from popup to open overlay window
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'openOverlay') {
    createOverlayWindow();
    sendResponse({ success: true });
  }
  return true;
});

async function createOverlayWindow() {
  // Check if overlay window already exists
  const windows = await chrome.windows.getAll();
  const existingOverlay = windows.find(w => w.type === 'popup' && w.width === 320);

  if (existingOverlay) {
    // Focus existing window
    await chrome.windows.update(existingOverlay.id, { focused: true });
    return;
  }

  // Create new overlay window
  chrome.windows.create({
    url: chrome.runtime.getURL('overlay-window.html'),
    type: 'popup',
    width: 320,
    height: 500,
    top: 100,
    left: 100,
    focused: true
  });
}
