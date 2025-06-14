// VelocitasExtension.js - Main extension controller
// Convert the VelocitasExtension module to attach to window object and reference other modules from window
window.VelocitasExtension = class VelocitasExtension {
    constructor() {
        this.headerManager = new window.DateHeaderManager();
        this.emailExtractor = new window.EmailExtractor();
        this.isEnabled = true;
        this.initialized = false;
        this.messageListener = null;
    }

    async init() {
        if (this.initialized) {
            console.log('Velocitas: Already initialized');
            return;
        }

        console.log('Velocitas: Initializing extension...');

        try {
            // Load saved state
            const result = await chrome.storage.local.get(['velocitasEnabled']);
            this.isEnabled = result.velocitasEnabled !== false; // Default to true
        } catch (error) {
            console.log('Velocitas: Using default enabled state (storage unavailable)');
            this.isEnabled = true;
        }

        // Set up message listener (avoid duplicates)
        this._setupMessageListener();

        // Apply initial state
        this.applyTheme();

        // Initialize features after page is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this._initializeFeatures());
        } else {
            this._initializeFeatures();
        }

        this.initialized = true;
        console.log(`Velocitas: Extension initialized (enabled: ${this.isEnabled})`);
    }

    _setupMessageListener() {
        // Remove existing listener if any
        if (this.messageListener) {
            chrome.runtime.onMessage.removeListener(this.messageListener);
        }

        // Create new listener
        this.messageListener = (message, sender, sendResponse) => {
            try {
                if (message.action === 'toggle') {
                    this.toggle();
                    sendResponse({ enabled: this.isEnabled });
                } else if (message.action === 'getStatus') {
                    sendResponse({ 
                        enabled: this.isEnabled,
                        stats: this.headerManager.getStats()
                    });
                } else if (message.action === 'cleanup') {
                    this.headerManager.cleanup();
                    sendResponse({ success: true });
                } else if (message.action === 'extractFirstEmail') {
                    const emailData = this.emailExtractor.extractFirstEmail();
                    sendResponse({ emailData });
                }
            } catch (error) {
                console.error('Velocitas: Error handling message:', error);
                sendResponse({ error: error.message });
            }
            return true; // Keep message channel open for async response
        };

        chrome.runtime.onMessage.addListener(this.messageListener);
    }

    toggle() {
        this.isEnabled = !this.isEnabled;
        this.applyTheme();
        
        // Save state
        try {
            chrome.storage.local.set({ velocitasEnabled: this.isEnabled });
        } catch (error) {
            console.warn('Velocitas: Could not save state:', error);
        }
        
        console.log(`Velocitas: Toggled to ${this.isEnabled ? 'enabled' : 'disabled'}`);
    }

    applyTheme() {
        if (this.isEnabled) {
            document.body.classList.add('velocitas-modern-theme');
            console.log('Velocitas: Theme enabled');
        } else {
            document.body.classList.remove('velocitas-modern-theme');
            this.headerManager.cleanup();
            console.log('Velocitas: Theme disabled and cleaned up');
        }
    }

    _initializeFeatures() {
        if (!this.isEnabled) {
            console.log('Velocitas: Skipping feature initialization (disabled)');
            return;
        }

        console.log('Velocitas: Features initialized');
        
        // Check if we're in an extraction context first
        const isExtractionContext = this.emailExtractor._handleExtractionContext();
        
        // Check if we need to mark email as unread after returning
        this.emailExtractor._handleMarkUnreadOnReturn();
        
        // Only auto-extract if we're not already in an extraction context
        if (!isExtractionContext) {
            this._autoExtractFirstEmail();
        }
    }

    // Auto-extract the first email on page load
    _autoExtractFirstEmail() {
        console.log('Velocitas: Setting up auto-extraction of 10 emails...');
        
        // Wait a bit for Gmail to fully load, then extract multiple emails
        const attemptExtraction = (attempt = 1, maxAttempts = 5) => {
            console.log(`Velocitas: Auto-extraction attempt ${attempt}/${maxAttempts}`);
            
            // Extract 10 emails instead of just one
            const emailsData = this.emailExtractor.extractMultipleEmails(10);
            
            if (emailsData && emailsData.length > 0) {
                console.log(`Velocitas: Auto-extraction successful! Found ${emailsData.length} emails to process.`);
            } else if (attempt < maxAttempts) {
                // Try again after a delay
                setTimeout(() => attemptExtraction(attempt + 1, maxAttempts), 2000);
            } else {
                console.log('Velocitas: Auto-extraction failed after all attempts. Gmail may not be fully loaded or inbox may be empty.');
            }
        };

        // Start extraction after initial delay
        setTimeout(() => attemptExtraction(), 1000);
    }

    // Cleanup method
    cleanup() {
        console.log('Velocitas: Cleaning up VelocitasExtension');
        
        // Clean up components
        if (this.headerManager) {
            this.headerManager.cleanup();
        }
        
        // Remove message listener
        if (this.messageListener) {
            chrome.runtime.onMessage.removeListener(this.messageListener);
            this.messageListener = null;
        }
        
        // Clean up any overlays
        const loadingOverlay = document.getElementById('velocitas-loading-overlay');
        const syncingOverlay = document.getElementById('velocitas-syncing-overlay');
        const loadingStyles = document.getElementById('velocitas-loading-styles');
        const syncingStyles = document.getElementById('velocitas-syncing-styles');
        
        if (loadingOverlay) loadingOverlay.remove();
        if (syncingOverlay) syncingOverlay.remove();
        if (loadingStyles) loadingStyles.remove();
        if (syncingStyles) syncingStyles.remove();
        
        // Remove theme class
        document.body.classList.remove('velocitas-modern-theme');
        
        this.initialized = false;
    }
}