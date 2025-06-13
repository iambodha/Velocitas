class DateHeaderManager {
    constructor() {
        this.insertedHeaders = new Set();
        this.observer = null;
        this.debounceTimer = null;
    }

    // Main method to insert date headers with improved reliability
    insertDateHeader(category, row, emailContainer) {
        if (!category || !row || !emailContainer) {
            console.warn("Velocitas: Invalid parameters for header insertion");
            return;
        }

        const headerId = `velocitas-group-${this._sanitizeId(category)}`;
        
        // Check if we already handled this header recently
        if (this.insertedHeaders.has(headerId)) {
            const existingHeader = document.getElementById(headerId);
            if (existingHeader && this._isHeaderPositionedCorrectly(existingHeader, row)) {
                return;
            }
        }

        this._cleanupExistingHeader(headerId);
        this._createAndInsertHeader(headerId, category, row, emailContainer);
        
        // Track insertion to prevent duplicates
        this.insertedHeaders.add(headerId);
        
        // Clean up tracking after a delay
        setTimeout(() => this.insertedHeaders.delete(headerId), 1000);
    }

    // Create and insert the header element
    _createAndInsertHeader(headerId, category, row, emailContainer) {
        const headerElement = document.createElement('tr');
        headerElement.id = headerId;
        headerElement.className = 'velocitas-date-group-header';
        
        // Critical: Prevent all interaction with header
        this._makeElementNonInteractive(headerElement);
        
        const headerCell = this._createHeaderCell(category, row);
        headerElement.appendChild(headerCell);
        
        try {
            emailContainer.insertBefore(headerElement, row);
            
            // Add mutation observer to handle dynamic changes
            this._observeHeaderStability(headerElement, row);
            
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
        
        // Apply comprehensive styling
        headerCell.style.cssText = `
            background-color: #FFFACD !important;
            color: #4A4A4A !important;
            padding: 8px 18px !important;
            font-weight: bold !important;
            font-size: 13px !important;
            border-top: 1px solid #FFEE58 !important;
            border-bottom: 1px solid #FFEE58 !important;
            pointer-events: none !important;
            user-select: none !important;
            position: relative !important;
            z-index: 1 !important;
            height: 32px !important;
            box-sizing: border-box !important;
        `;
        
        return headerCell;
    }

    // Make element completely non-interactive
    _makeElementNonInteractive(element) {
        element.style.cssText += `
            pointer-events: none !important;
            user-select: none !important;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            cursor: default !important;
        `;
        
        // Prevent event bubbling
        element.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
        }, true);
        
        element.addEventListener('mousedown', (e) => {
            e.stopPropagation();
            e.preventDefault();
        }, true);
    }

    // Clean up any existing header
    _cleanupExistingHeader(headerId) {
        const existing = document.getElementById(headerId);
        if (existing) {
            // Stop observing if we were watching this element
            if (this.observer) {
                this.observer.disconnect();
            }
            existing.remove();
        }
    }

    // Check if header is positioned correctly
    _isHeaderPositionedCorrectly(header, targetRow) {
        return header.nextElementSibling === targetRow && 
               header.parentNode === targetRow.parentNode;
    }

    // Get column count for proper colspan
    _getColumnCount(row) {
        if (row.cells && row.cells.length > 0) {
            return row.cells.length;
        }
        
        // Fallback: look at other rows in the same table
        const table = row.closest('table');
        if (table) {
            const firstRow = table.querySelector('tr');
            if (firstRow && firstRow.cells) {
                return firstRow.cells.length;
            }
        }
        
        return 6; // Default fallback
    }

    // Sanitize category for use as ID
    _sanitizeId(category) {
        return category.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase();
    }

    // Observe header to ensure it stays in place
    _observeHeaderStability(headerElement, targetRow) {
        // Debounce to avoid excessive checking
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        this.debounceTimer = setTimeout(() => {
            if (this.observer) {
                this.observer.disconnect();
            }
            
            this.observer = new MutationObserver((mutations) => {
                let needsRepositioning = false;
                
                mutations.forEach((mutation) => {
                    if (mutation.type === 'childList') {
                        // Check if our header got moved or removed
                        if (!document.contains(headerElement) || 
                            headerElement.nextElementSibling !== targetRow) {
                            needsRepositioning = true;
                        }
                    }
                });
                
                if (needsRepositioning && document.contains(targetRow)) {
                    console.log("Velocitas: Repositioning displaced header");
                    try {
                        targetRow.parentNode.insertBefore(headerElement, targetRow);
                    } catch (e) {
                        console.warn("Velocitas: Could not reposition header:", e);
                    }
                }
            });
            
            // Observe the parent container for changes
            const container = targetRow.parentNode;
            if (container) {
                this.observer.observe(container, {
                    childList: true,
                    subtree: false
                });
            }
        }, 100);
    }

    // Cleanup method to call when the extension is disabled/removed
    cleanup() {
        if (this.observer) {
            this.observer.disconnect();
        }
        
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Remove all headers
        document.querySelectorAll('.velocitas-date-group-header').forEach(header => {
            header.remove();
        });
        
        this.insertedHeaders.clear();
    }
}

// Usage example:
const headerManager = new DateHeaderManager();

// Replace your existing _insertDateHeader method with:
function _insertDateHeader(category, row, emailContainer) {
    headerManager.insertDateHeader(category, row, emailContainer);
}

// Alternative: If you prefer to keep it as a simple function without the class:
function insertDateHeaderImproved(category, row, emailContainer) {
    if (!category || !row || !emailContainer) return;
    
    const headerId = `velocitas-group-${category.replace(/[^a-zA-Z0-9-_]/g, '-').toLowerCase()}`;
    
    // Remove existing header
    const existing = document.getElementById(headerId);
    if (existing) existing.remove();
    
    // Create new header
    const headerElement = document.createElement('tr');
    headerElement.id = headerId;
    headerElement.className = 'velocitas-date-group-header';
    
    // Make completely non-interactive
    headerElement.style.cssText = `
        pointer-events: none !important;
        user-select: none !important;
        -webkit-user-select: none !important;
        -moz-user-select: none !important;
        cursor: default !important;
    `;
    
    // Create cell
    const cell = document.createElement('td');
    cell.colSpan = row.cells.length || 6;
    cell.textContent = category;
    cell.style.cssText = `
        background-color: #FFFACD !important;
        color: #4A4A4A !important;
        padding: 8px 18px !important;
        font-weight: bold !important;
        font-size: 13px !important;
        border-top: 1px solid #FFEE58 !important;
        border-bottom: 1px solid #FFEE58 !important;
        pointer-events: none !important;
        user-select: none !important;
        height: 32px !important;
        box-sizing: border-box !important;
    `;
    
    headerElement.appendChild(cell);
    
    // Prevent event bubbling
    ['click', 'mousedown', 'mouseup'].forEach(eventType => {
        headerElement.addEventListener(eventType, (e) => {
            e.stopPropagation();
            e.preventDefault();
        }, true);
    });
    
    try {
        emailContainer.insertBefore(headerElement, row);
    } catch (error) {
        console.error("Velocitas: Header insertion failed:", error);
    }
}