// Background service worker for Quest Tracker extension
// Minimal service worker - Document PiP handles always-on-top natively

// Clean up any stale storage on install/update
chrome.runtime.onInstalled.addListener(() => {
  // Clear old pin-related storage since we now use Document PiP
  chrome.storage.local.remove(['alwaysOnTop', 'pinHelpShown']);
});
