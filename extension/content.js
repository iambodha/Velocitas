(() => {
    'use strict';

    // Prevent multiple initialization
    if (window.VelocitasExtension) {
        console.log('Velocitas: Already initialized, skipping...');
        return;
    }

    class DateHeaderManager {
        constructor() {
            this.insertedHeaders = new Map(); // Use Map to store header metadata
            this.observer = null;
            this.debounceTimer = null;
            this.headerPositions = new WeakMap(); // Track header-row relationships
        }

        // Main method to insert date headers with improved reliability
        insertDateHeader(category, row, emailContainer) {
            if (!category || !row || !emailContainer) {
                console.warn("Velocitas: Invalid parameters for header insertion");
                return;
            }

            const headerId = `velocitas-group-${this._sanitizeId(category)}`;
            const rowId = this._getRowIdentifier(row);
            
            // Check if we already have a header for this exact position
            if (this._hasValidHeaderForRow(headerId, row)) {
                return;
            }

            // Clean up any orphaned headers for this category
            this._cleanupExistingHeader(headerId);
            
            // Create and insert new header
            this._createAndInsertHeader(headerId, category, row, emailContainer);
            
            // Track the header-row relationship
            this.insertedHeaders.set(headerId, {
                category,
                rowId,
                timestamp: Date.now()
            });
        }

        // Check if a valid header already exists for this row
        _hasValidHeaderForRow(headerId, targetRow) {
            const existingHeader = document.getElementById(headerId);
            if (!existingHeader) return false;

            // Check if header is correctly positioned
            return existingHeader.nextElementSibling === targetRow && 
                   existingHeader.parentNode === targetRow.parentNode &&
                   document.contains(existingHeader);
        }

        // Generate a unique identifier for a row
        _getRowIdentifier(row) {
            // Use multiple attributes to create a stable identifier
            const text = (row.textContent || '').trim().substring(0, 50);
            const index = Array.from(row.parentNode.children).indexOf(row);
            return `${text}-${index}`;
        }

        // Create and insert the header element
        _createAndInsertHeader(headerId, category, row, emailContainer) {
            const headerElement = document.createElement('tr');
            headerElement.id = headerId;
            headerElement.className = 'velocitas-date-group-header';
            
            // Mark as Velocitas element for easy identification
            headerElement.setAttribute('data-velocitas-header', 'true');
            
            // Critical: Prevent all interaction with header
            this._makeElementNonInteractive(headerElement);
            
            const headerCell = this._createHeaderCell(category, row);
            headerElement.appendChild(headerCell);
            
            try {
                emailContainer.insertBefore(headerElement, row);
                
                // Store the relationship for position tracking
                this.headerPositions.set(headerElement, row);
                
                // Set up stability monitoring
                this._setupHeaderMonitoring(headerElement, row);
                
                console.log(`Velocitas: Inserted header "${category}" before row`);
                
            } catch (error) {
                console.error("Velocitas: Failed to insert header:", error);
            }
        }

        // Create the header cell with proper styling
        _createHeaderCell(category, row) {
            const headerCell = document.createElement('td');
            const colCount = this._getColumnCount(row);
            
            headerCell.colSpan = colCount;
            headerCell.textContent = category;
            
            // Apply comprehensive styling with better isolation
            headerCell.style.cssText = `
                background: linear-gradient(135deg, #FFFACD 0%, #FFF8DC 100%) !important;
                color: #4A4A4A !important;
                padding: 8px 18px !important;
                font-weight: 600 !important;
                font-size: 13px !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
                border-top: 2px solid #FFEE58 !important;
                border-bottom: 1px solid #FFEE58 !important;
                border-left: none !important;
                border-right: none !important;
                pointer-events: none !important;
                user-select: none !important;
                position: relative !important;
                z-index: 0 !important;
                height: 36px !important;
                box-sizing: border-box !important;
                text-align: left !important;
                vertical-align: middle !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
            `;
            
            return headerCell;
        }

        // Make element completely non-interactive with better event handling
        _makeElementNonInteractive(element) {
            // Set CSS properties for non-interaction
            element.style.cssText += `
                pointer-events: none !important;
                user-select: none !important;
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
                cursor: default !important;
                position: relative !important;
                z-index: 0 !important;
            `;
            
            // Add comprehensive event prevention
            const preventEvents = ['click', 'mousedown', 'mouseup', 'mouseover', 'mouseout', 
                                 'contextmenu', 'selectstart', 'dragstart', 'focus', 'blur'];
            
            preventEvents.forEach(eventType => {
                element.addEventListener(eventType, (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    return false;
                }, { capture: true, passive: false });
            });
        }

        // Clean up any existing header
        _cleanupExistingHeader(headerId) {
            const existing = document.getElementById(headerId);
            if (existing) {
                // Stop observing if we were watching this element
                if (this.observer) {
                    this.observer.disconnect();
                    this.observer = null;
                }
                existing.remove();
                this.insertedHeaders.delete(headerId);
                console.log(`Velocitas: Cleaned up existing header: ${headerId}`);
            }
        }

        // Setup monitoring for header stability
        _setupHeaderMonitoring(headerElement, targetRow) {
            // Clear any existing timer
            if (this.debounceTimer) {
                clearTimeout(this.debounceTimer);
            }
            
            // Debounced monitoring setup
            this.debounceTimer = setTimeout(() => {
                this._initializeHeaderObserver(headerElement, targetRow);
            }, 100);
        }

        // Initialize mutation observer for header stability
        _initializeHeaderObserver(headerElement, targetRow) {
            if (this.observer) {
                this.observer.disconnect();
            }
            
            this.observer = new MutationObserver((mutations) => {
                let needsRepositioning = false;
                let headerStillExists = document.contains(headerElement);
                let targetStillExists = document.contains(targetRow);
                
                if (!headerStillExists || !targetStillExists) {
                    this.observer.disconnect();
                    return;
                }
                
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        // Check if header got displaced
                        if (headerElement.nextElementSibling !== targetRow ||
                            headerElement.parentNode !== targetRow.parentNode) {
                            needsRepositioning = true;
                        }
                    }
                });
                
                if (needsRepositioning) {
                    this._repositionHeader(headerElement, targetRow);
                }
            });
            
            // Observe the parent container
            const container = targetRow.parentNode;
            if (container) {
                this.observer.observe(container, {
                    childList: true,
                    subtree: false
                });
            }
        }

        // Reposition a displaced header
        _repositionHeader(headerElement, targetRow) {
            try {
                if (document.contains(targetRow) && document.contains(headerElement)) {
                    targetRow.parentNode.insertBefore(headerElement, targetRow);
                    console.log("Velocitas: Repositioned displaced header");
                }
            } catch (error) {
                console.warn("Velocitas: Could not reposition header:", error);
                // If repositioning fails, remove the broken header
                headerElement.remove();
            }
        }

        // Get column count for proper colspan
        _getColumnCount(row) {
            if (row.cells && row.cells.length > 0) {
                return row.cells.length;
            }
            
            // Fallback: look at other rows in the same table
            const table = row.closest('table, tbody');
            if (table) {
                const rows = table.querySelectorAll('tr');
                for (let testRow of rows) {
                    if (testRow.cells && testRow.cells.length > 0) {
                        return testRow.cells.length;
                    }
                }
            }
            
            return 6; // Gmail typically has 6 columns
        }

        // Sanitize category for use as ID
        _sanitizeId(category) {
            return category.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase().substring(0, 50);
        }

        // Cleanup method
        cleanup() {
            console.log('Velocitas: Cleaning up DateHeaderManager');
            
            // Disconnect observer
            if (this.observer) {
                this.observer.disconnect();
                this.observer = null;
            }
            
            // Clear debounce timer
            if (this.debounceTimer) {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = null;
            }
            
            // Remove all headers
            document.querySelectorAll('.velocitas-date-group-header').forEach(header => {
                header.remove();
            });
            
            // Clear tracking
            this.insertedHeaders.clear();
            this.headerPositions = new WeakMap();
        }

        // Get current stats for debugging
        getStats() {
            return {
                trackedHeaders: this.insertedHeaders.size,
                activeHeaders: document.querySelectorAll('.velocitas-date-group-header').length,
                observerActive: !!this.observer
            };
        }
    }

    // Main Extension Controller
    class VelocitasExtension {
        constructor() {
            this.headerManager = new DateHeaderManager();
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
            
            // Add any additional features here
            // Example: this._startEmailGrouping();
        }

        // Cleanup method for when extension is disabled/removed
        cleanup() {
            console.log('Velocitas: Cleaning up extension');
            
            if (this.messageListener) {
                chrome.runtime.onMessage.removeListener(this.messageListener);
                this.messageListener = null;
            }
            
            this.headerManager.cleanup();
            document.body.classList.remove('velocitas-modern-theme');
            this.initialized = false;
        }
    }

    // Prevent multiple instances and provide global access
    if (!window.VelocitasExtension) {
        // Initialize the extension
        window.VelocitasExtension = new VelocitasExtension();
        window.VelocitasExtension.init().catch(error => {
            console.error('Velocitas: Failed to initialize:', error);
        });

        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (window.VelocitasExtension) {
                window.VelocitasExtension.cleanup();
            }
        });

        console.log('Velocitas: Bundle loaded and initialized');
    }

})();