// Velocitas Extension - Minimal Content Script

class VelocitasAI {
    constructor() {
      this.isEnabled = true;
      this.init();
    }
  
    init() {
      // Listen for messages from popup
      chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === 'toggle') {
          this.toggle();
          sendResponse({ enabled: this.isEnabled });
        } else if (request.action === 'getStatus') {
          sendResponse({ enabled: this.isEnabled });
        }
      });
    }
  
    toggle() {
      this.isEnabled = !this.isEnabled;
      chrome.storage.local.set({ enabled: this.isEnabled });
    }
  }
  
  // Initialize minimal extension
  if (window.location.hostname === 'mail.google.com') {
    chrome.storage.local.get(['enabled'], (result) => {
      const velocitasAI = new VelocitasAI();
      if (result.enabled === false) {
        velocitasAI.toggle();
      }
    });
  }