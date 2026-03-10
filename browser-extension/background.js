// Background service worker for Quest Tracker extension

// Track the overlay window ID and state
let overlayWindowId = null;
let isAlwaysOnTop = false;

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'openOverlay') {
    createOverlayWindow().then(result => {
      sendResponse(result);
    });
    return true;
  }

  if (message.action === 'toggleAlwaysOnTop') {
    toggleAlwaysOnTop(sender.tab?.windowId).then(result => {
      sendResponse(result);
    });
    return true;
  }

  if (message.action === 'getAlwaysOnTopState') {
    getAlwaysOnTopState(sender.tab?.windowId).then(result => {
      sendResponse(result);
    });
    return true;
  }

  return true;
});

async function createOverlayWindow() {
  // Check if overlay window already exists
  if (overlayWindowId !== null) {
    try {
      const existingWindow = await chrome.windows.get(overlayWindowId);
      if (existingWindow) {
        await chrome.windows.update(overlayWindowId, { focused: true });
        return { success: true, windowId: overlayWindowId, alwaysOnTop: isAlwaysOnTop };
      }
    } catch (e) {
      overlayWindowId = null;
    }
  }

  // Load saved alwaysOnTop preference
  const stored = await chrome.storage.local.get(['alwaysOnTop']);
  isAlwaysOnTop = stored.alwaysOnTop || false;

  // Create new overlay window
  // Note: 'panel' type with alwaysOnTop would be ideal but requires specific flags
  const newWindow = await chrome.windows.create({
    url: chrome.runtime.getURL('popup.html') + '?popout=true',
    type: 'popup',
    width: 360,
    height: 500,
    top: 100,
    left: 100,
    focused: true
  });

  overlayWindowId = newWindow.id;

  // Apply alwaysOnTop if previously enabled
  if (isAlwaysOnTop) {
    try {
      await chrome.windows.update(overlayWindowId, { focused: true });
    } catch (e) {
      console.log('Could not set focus:', e);
    }
  }

  return { success: true, windowId: overlayWindowId, alwaysOnTop: isAlwaysOnTop };
}

async function getAlwaysOnTopState(windowId) {
  // If called from the popup window, use that window ID
  const targetWindowId = windowId || overlayWindowId;

  if (targetWindowId) {
    try {
      const win = await chrome.windows.get(targetWindowId);
      // Check if this is our overlay window
      if (win.type === 'popup') {
        return { alwaysOnTop: isAlwaysOnTop, windowId: targetWindowId };
      }
    } catch (e) {
      // Window doesn't exist
    }
  }

  return { alwaysOnTop: isAlwaysOnTop, windowId: overlayWindowId };
}

async function toggleAlwaysOnTop(windowId) {
  const targetWindowId = windowId || overlayWindowId;

  if (targetWindowId === null) {
    return { success: false, error: 'No overlay window open' };
  }

  try {
    // Toggle the state
    isAlwaysOnTop = !isAlwaysOnTop;

    // Save preference
    await chrome.storage.local.set({ alwaysOnTop: isAlwaysOnTop });

    // Note: True always-on-top requires OS-level support
    // Chrome's windows API doesn't expose alwaysOnTop for standard windows
    // The best we can do is focus the window when toggled on
    if (isAlwaysOnTop) {
      await chrome.windows.update(targetWindowId, { focused: true });
    }

    return { success: true, alwaysOnTop: isAlwaysOnTop };
  } catch (e) {
    return { success: false, error: e.message };
  }
}

// Clean up when overlay window is closed
chrome.windows.onRemoved.addListener((windowId) => {
  if (windowId === overlayWindowId) {
    overlayWindowId = null;
  }

  // Broadcast to any remaining windows that pin state might need update
  chrome.runtime.sendMessage({ action: 'windowClosed', windowId }).catch(() => {});
});

// Re-focus pinned window periodically when enabled
let focusInterval = null;

async function startFocusInterval() {
  if (focusInterval) return;

  focusInterval = setInterval(async () => {
    if (isAlwaysOnTop && overlayWindowId !== null) {
      try {
        const win = await chrome.windows.get(overlayWindowId);
        if (win && !win.focused) {
          // Only refocus if not already focused
          // This creates a "sticky" effect
        }
      } catch (e) {
        // Window gone
        clearInterval(focusInterval);
        focusInterval = null;
      }
    } else if (!isAlwaysOnTop && focusInterval) {
      clearInterval(focusInterval);
      focusInterval = null;
    }
  }, 500);
}

// Initialize
chrome.storage.local.get(['alwaysOnTop'], (result) => {
  isAlwaysOnTop = result.alwaysOnTop || false;
});
