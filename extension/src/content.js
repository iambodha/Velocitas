/**
 * Velocitas Extension - Main Content Script with Modular Architecture
 */

import { VelocitasClasses } from './util/Constants.js';
import DateGrouper from './bundling/DateGrouper.js';
import MainParentObserver from './handlers/MainParentObserver.js';
import MessageListWatcher from './handlers/MessageListWatcher.js';

class VelocitasAI {
    constructor() {
        this.isEnabled = true;
        this.themeClassName = VelocitasClasses.VELOCITAS;
        
        // Initialize components
        this.dateGrouper = new DateGrouper();
        this.messageListWatcher = new MessageListWatcher(this.handleGmailRerender.bind(this));
        this.mainParentObserver = new MainParentObserver(this.handleMainChange.bind(this));
        
        // State tracking
        this.isFreshPage = false;
        this.initializationRetries = 0;
        this.maxInitializationRetries = 5;
        
        this._initializeStateAndListeners();
    }

    _initializeStateAndListeners() {
        // Load stored enabled state
        chrome.storage.local.get(['enabled'], (result) => {
            this.isEnabled = result.enabled !== false;
            this._applyChanges();

            if (!chrome.runtime.onMessage.hasListeners()) {
                chrome.runtime.onMessage.addListener(this._handleMessage.bind(this));
            }
        });
    }

    _handleMessage(request, sender, sendResponse) {
        if (request.action === 'toggle') {
            this.toggle();
            sendResponse({ enabled: this.isEnabled });
        } else if (request.action === 'getStatus') {
            sendResponse({ enabled: this.isEnabled });
        }
        return true;
    }

    toggle() {
        this.isEnabled = !this.isEnabled;
        chrome.storage.local.set({ enabled: this.isEnabled });
        this._applyChanges();
    }

    _applyChanges() {
        if (this.isEnabled) {
            document.body.classList.add(this.themeClassName);
            this._initializeExtension();
        } else {
            document.body.classList.remove(this.themeClassName);
            this._cleanupExtension();
        }
    }

    _initializeExtension() {
        console.log('Velocitas: Initializing extension');
        
        // Try to initialize with retries
        this._tryInitialization();
    }

    _tryInitialization() {
        if (this.initializationRetries >= this.maxInitializationRetries) {
            console.error('Velocitas: Failed to initialize after maximum retries');
            return;
        }

        // Check if Gmail is ready
        if (!this._isGmailReady()) {
            this.initializationRetries++;
            console.log(`Velocitas: Gmail not ready, retrying (${this.initializationRetries}/${this.maxInitializationRetries})`);
            setTimeout(() => this._tryInitialization(), 2000);
            return;
        }

        // Reset retry counter on successful initialization
        this.initializationRetries = 0;
        
        // Initial grouping
        setTimeout(() => {
            this.dateGrouper.groupEmailsByDate();
        }, 1000);

        // Start observers
        this._startObservers();
    }

    _isGmailReady() {
        // Check if basic Gmail structures are present
        const mainArea = document.querySelector('[role="main"]');
        const hasGmailStructure = mainArea && (
            document.querySelector('tbody') || 
            document.querySelector('.nH') ||
            document.querySelector('.Cp')
        );
        
        return hasGmailStructure;
    }

    _startObservers() {
        console.log('Velocitas: Starting observers');
        
        // Start main observer for page changes
        this.mainParentObserver.observe();
        
        // Start message list watcher for email changes
        this.messageListWatcher.observe();
        
        // Set up fresh page detection
        this._setupPageChangeDetection();
    }

    _setupPageChangeDetection() {
        // Listen for navigation events that indicate a fresh page
        document.addEventListener('mousedown', (e) => {
            const target = e.target;
            
            // Check if clicking on inbox tab, refresh, or navigation buttons
            if (target.matches('[data-tooltip="Inbox"]') ||
                target.matches('[data-tooltip="Refresh"]') ||
                target.closest('[data-tooltip="Inbox"]') ||
                target.closest('[data-tooltip="Refresh"]') ||
                target.matches('.ar9.T-I-J3') ||
                target.closest('.ar9.T-I-J3')) {
                
                this.isFreshPage = true;
                console.log('Velocitas: Fresh page navigation detected');
            }
        });
    }

    handleGmailRerender() {
        console.log('Velocitas: Gmail rerender detected');
        
        if (!this.isEnabled) return;
        
        // Disconnect watchers temporarily to avoid recursive triggers
        this.messageListWatcher.disconnect();
        
        // Regroup emails
        setTimeout(() => {
            this.dateGrouper.groupEmailsByDate();
            
            // Reconnect watchers
            this.messageListWatcher.observe();
            
            // Reset fresh page flag
            this.isFreshPage = false;
        }, 500);
    }

    handleMainChange(mutations) {
        console.log('Velocitas: Main container change detected');
        
        if (!this.isEnabled) return;
        
        // Check if this is a significant change that warrants regrouping
        const hasSignificantChanges = mutations.some(mutation => {
            const addedEmailRows = Array.from(mutation.addedNodes).some(node => 
                node.nodeType === Node.ELEMENT_NODE && 
                (node.matches && node.matches('tr') || 
                 node.querySelector && node.querySelector('tr'))
            );
            
            const removedEmailRows = Array.from(mutation.removedNodes).some(node => 
                node.nodeType === Node.ELEMENT_NODE && 
                (node.matches && node.matches('tr') ||
                 node.classList && node.classList.contains(VelocitasClasses.DATE_GROUP_HEADER))
            );
            
            return addedEmailRows || removedEmailRows;
        });
        
        if (hasSignificantChanges) {
            // Debounce the regrouping
            clearTimeout(this.regroupTimeout);
            this.regroupTimeout = setTimeout(() => {
                this.handleGmailRerender();
            }, 1000);
        }
    }

    _cleanupExtension() {
        console.log('Velocitas: Cleaning up extension');
        
        // Clear date groups
        this.dateGrouper.clearExistingGroups();
        
        // Disconnect all observers
        this.mainParentObserver.disconnect();
        this.messageListWatcher.disconnect();
        
        // Clear any pending timeouts
        if (this.regroupTimeout) {
            clearTimeout(this.regroupTimeout);
            this.regroupTimeout = null;
        }
    }
}

// Initialize extension when on Gmail
if (window.location.hostname === 'mail.google.com') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new VelocitasAI());
    } else {
        new VelocitasAI();
    }
}