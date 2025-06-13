// Velocitas Extension - Content Script

class VelocitasAI {
    constructor() {
        this.isEnabled = true;
        this.themeClassName = 'velocitas-modern-theme';
        this.observer = null;
        this.messageListWatcher = null;
        this.debounceTimeout = null;
        this.isProcessing = false;
        this._initializeStateAndListeners();
    }

    _initializeStateAndListeners() {
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
            this._startWatching();
            this.groupEmailsByDate();
        } else {
            document.body.classList.remove(this.themeClassName);
            this._ungroupEmailsByDate();
            this._stopWatching();
        }
    }

    _startWatching() {
        if (this.messageListWatcher) {
            this.messageListWatcher.disconnect();
        }
        this.messageListWatcher = this._createMessageListWatcher();
        this.messageListWatcher.observe();
    }

    _stopWatching() {
        if (this.messageListWatcher) {
            this.messageListWatcher.disconnect();
            this.messageListWatcher = null;
        }
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
            this.debounceTimeout = null;
        }
    }

    _createMessageListWatcher() {
        const possibleSelectors = [
            'div[role="main"]',
            '[role="main"]',
            '.nH.bkK',
            '.nH',
            'body'
        ];

        let targetNode = null;
        for (const selector of possibleSelectors) {
            targetNode = document.querySelector(selector);
            if (targetNode) break;
        }

        if (!targetNode) {
            console.warn("Velocitas: No suitable target found for watching");
            return { 
                observe: () => {}, 
                disconnect: () => {} 
            };
        }

        const config = {
            childList: true,
            subtree: true,
            attributes: false
        };

        const observer = new MutationObserver((mutations) => {
            if (!this.isEnabled || this.isProcessing) return;

            let shouldRefresh = false;
            for (const mutation of mutations) {
                if (mutation.type === 'childList') {
                    // Check for email row changes
                    const hasRelevantChanges = Array.from(mutation.addedNodes).some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        this._isEmailRelatedNode(node)
                    ) || Array.from(mutation.removedNodes).some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (this._isEmailRelatedNode(node) || node.classList?.contains('velocitas-date-group-header'))
                    );

                    if (hasRelevantChanges) {
                        shouldRefresh = true;
                        break;
                    }
                }
            }

            if (shouldRefresh) {
                this._debouncedRefresh();
            }
        });

        return {
            observe: () => observer.observe(targetNode, config),
            disconnect: () => observer.disconnect()
        };
    }

    _isEmailRelatedNode(node) {
        if (!node.matches && !node.querySelector) return false;
        
        // Check if it's an email row or contains email rows
        const emailIndicators = [
            'tr.zA', 'tr[jsmodel]', 'tr[role="row"]',
            '[data-thread-id]', '[data-thread-perm-id]',
            '.yW', '.bog', '.xY'
        ];

        return emailIndicators.some(selector => {
            try {
                return node.matches?.(selector) || node.querySelector?.(selector);
            } catch (e) {
                return false;
            }
        });
    }

    _debouncedRefresh() {
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
        }
        
        this.debounceTimeout = setTimeout(() => {
            if (this.isEnabled && !this.isProcessing) {
                this.groupEmailsByDate();
            }
        }, 100); // Much shorter delay for smoothness
    }

    _findMessageList() {
        // Try multiple selectors in order of preference
        const possibleSelectors = [
            'div[role="main"] table tbody',
            '[role="main"] tbody',
            'table.F tbody',
            '.BltHke tbody',
            'tbody'
        ];

        for (const selector of possibleSelectors) {
            const element = document.querySelector(selector);
            if (element && element.querySelectorAll('tr').length > 0) {
                return element;
            }
        }
        return null;
    }

    _getGmailEmailRows() {
        const messageList = this._findMessageList();
        if (!messageList) {
            return document.querySelectorAll('');
        }

        // Get all table rows and filter for email rows
        const allRows = messageList.querySelectorAll('tr');
        const emailRows = [];

        for (const row of allRows) {
            // Skip our own headers
            if (row.classList.contains('velocitas-date-group-header')) {
                continue;
            }

            // Check if this looks like an email row
            const hasEmailIndicators = 
                row.querySelector('[data-thread-id]') ||
                row.querySelector('[data-thread-perm-id]') ||
                row.querySelector('.yW') || // sender
                row.querySelector('.bog') || // subject
                row.querySelector('.xY') || // date
                row.querySelector('span[email]') ||
                row.querySelector('[title*=":"]') || // time format
                row.classList.contains('zA') ||
                row.hasAttribute('jsmodel');

            if (hasEmailIndicators) {
                emailRows.push(row);
            }
        }

        return emailRows;
    }

    _getGmailEmailContainer(emailRows) {
        if (!emailRows || !emailRows.length) return null;
        return emailRows[0].closest('tbody') || emailRows[0].parentElement;
    }

    groupEmailsByDate() {
        if (this.isProcessing) return;
        this.isProcessing = true;

        try {
            // Clear existing headers first
            this._ungroupEmailsByDate();

            const emailRows = this._getGmailEmailRows();
            if (!emailRows.length) {
                return;
            }

            const emailContainer = this._getGmailEmailContainer(emailRows);
            if (!emailContainer) {
                return;
            }

            // Process all emails and collect header insertion points BEFORE making any DOM changes
            const insertionPlan = [];
            const now = new Date();
            const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);
            const last7DaysThreshold = new Date(today);
            last7DaysThreshold.setDate(today.getDate() - 6);
            const last30DaysThreshold = new Date(today);
            last30DaysThreshold.setDate(today.getDate() - 29);

            let currentGroup = null;

            emailRows.forEach(row => {
                const dateElement = this._findDateElement(row);
                if (!dateElement) return;

                const emailDate = this._parseEmailDate(dateElement.title || dateElement.textContent, now);
                if (!emailDate) return;

                const emailDateDayOnly = new Date(emailDate.getFullYear(), emailDate.getMonth(), emailDate.getDate());
                const category = this._categorizeDate(emailDateDayOnly, today, yesterday, last7DaysThreshold, last30DaysThreshold);

                if (category !== currentGroup) {
                    insertionPlan.push({ category, row });
                    currentGroup = category;
                }
            });

            // Now insert all headers in reverse order to avoid DOM shifting issues
            for (let i = insertionPlan.length - 1; i >= 0; i--) {
                const { category, row } = insertionPlan[i];
                this._insertDateHeaderSafely(category, row, emailContainer);
            }
        } finally {
            this.isProcessing = false;
        }
    }

    _insertDateHeaderSafely(category, row, emailContainer) {
        const headerId = `velocitas-group-${category.replace(/\s+/g, '-')}`;
        
        // Remove any existing header with this ID
        const existingHeader = document.getElementById(headerId);
        if (existingHeader) {
            existingHeader.remove();
        }

        // Create header with minimal DOM manipulation
        const headerElement = document.createElement('tr');
        headerElement.id = headerId;
        headerElement.classList.add('velocitas-date-group-header');
        
        // Use a single cell with colspan to avoid complex cell structure
        const headerCell = document.createElement('td');
        const colCount = row.cells.length > 0 ? row.cells.length : 6;
        headerCell.colSpan = colCount;
        headerCell.textContent = category;
        
        // Apply all styles inline to avoid CSS timing issues
        headerElement.style.cssText = `
            pointer-events: none !important;
            user-select: none !important;
            position: relative !important;
            z-index: 1 !important;
        `;
        
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
        `;
        
        headerElement.appendChild(headerCell);
        
        try {
            // Insert immediately before the email row
            emailContainer.insertBefore(headerElement, row);
        } catch (error) {
            console.warn("Velocitas: Error inserting header:", error);
        }
    }

    _findDateElement(row) {
        const dateSelectors = [
            'span[title*=":"]',
            'td.xY span',
            '.xW span[title]',
            '.xY span[title]',
            'td span[title]',
            'span[title]'
        ];

        for (const selector of dateSelectors) {
            const element = row.querySelector(selector);
            if (element && (element.title || element.textContent)) {
                return element;
            }
        }
        return null;
    }

    _parseEmailDate(dateStr, now) {
        if (!dateStr) return null;

        let emailDate = new Date(dateStr);
        if (!isNaN(emailDate.getTime())) {
            return emailDate;
        }

        // Try parsing relative dates
        const simpleDateMatch = dateStr.match(/^([a-zA-Z]{3})\s(\d{1,2})$/);
        if (simpleDateMatch) {
            emailDate = new Date(`${simpleDateMatch[0]}, ${now.getFullYear()}`);
            if (!isNaN(emailDate.getTime())) {
                return emailDate;
            }
        }

        return null;
    }

    _categorizeDate(emailDateDayOnly, today, yesterday, last7DaysThreshold, last30DaysThreshold) {
        const todayTime = today.getTime();
        const yesterdayTime = yesterday.getTime();
        const emailTime = emailDateDayOnly.getTime();
        
        // Calculate time differences in days
        const daysDiff = Math.floor((todayTime - emailTime) / (1000 * 60 * 60 * 24));
        
        if (emailTime === todayTime) {
            return "Today";
        } else if (emailTime === yesterdayTime) {
            return "Yesterday";
        } else if (daysDiff === 2) {
            return "2 days ago";
        } else if (daysDiff === 3) {
            return "3 days ago";
        } else if (daysDiff === 4) {
            return "4 days ago";
        } else if (daysDiff === 5) {
            return "5 days ago";
        } else if (daysDiff === 6) {
            return "6 days ago";
        } else if (daysDiff >= 7 && daysDiff <= 13) {
            return "A week ago";
        } else if (daysDiff >= 14 && daysDiff <= 20) {
            return "2 weeks ago";
        } else if (daysDiff >= 21 && daysDiff <= 27) {
            return "3 weeks ago";
        } else if (daysDiff >= 28 && daysDiff <= 59) {
            return "A month ago";
        } else if (daysDiff >= 60 && daysDiff <= 89) {
            return "2 months ago";
        } else if (daysDiff >= 90 && daysDiff <= 119) {
            return "3 months ago";
        } else if (daysDiff >= 120 && daysDiff <= 179) {
            return "4-6 months ago";
        } else if (daysDiff >= 180 && daysDiff <= 364) {
            return "6 months ago";
        } else if (daysDiff >= 365 && daysDiff <= 729) {
            return "A year ago";
        } else {
            return "A while ago";
        }
    }

    _insertDateHeader(category, row, emailContainer) {
        const headerId = `velocitas-group-${category.replace(/\s+/g, '-')}`;
        
        const existingHeader = document.getElementById(headerId);
        if (existingHeader && existingHeader.nextElementSibling === row) {
            return;
        }

        if (existingHeader) {
            existingHeader.remove();
        }

        const headerElement = document.createElement('tr');
        headerElement.id = headerId;
        headerElement.classList.add('velocitas-date-group-header');
        
        // Create individual cells instead of one spanning cell
        const colCount = row.cells.length > 0 ? row.cells.length : 6;
        
        for (let i = 0; i < colCount; i++) {
            const cell = document.createElement('td');
            
            if (i === 0) {
                // Put the date text only in the first cell
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
                `;
            } else {
                // Empty cells for other columns
                cell.innerHTML = '&nbsp;';
                cell.style.cssText = `
                    background-color: #FFFACD !important;
                    border-top: 1px solid #FFEE58 !important;
                    border-bottom: 1px solid #FFEE58 !important;
                    pointer-events: none !important;
                    user-select: none !important;
                    padding: 8px 0 !important;
                `;
            }
            
            headerElement.appendChild(cell);
        }
        
        // Make entire row non-interactive
        headerElement.style.pointerEvents = 'none';
        headerElement.style.userSelect = 'none';
        
        try {
            emailContainer.insertBefore(headerElement, row);
        } catch (error) {
            console.warn("Velocitas: Error inserting header:", error);
        }
    }

    _ungroupEmailsByDate() {
        const headers = document.querySelectorAll('.velocitas-date-group-header');
        headers.forEach(header => header.remove());
    }
}

// Initialize extension logic when on Gmail
if (window.location.hostname === 'mail.google.com') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => new VelocitasAI());
    } else {
        new VelocitasAI();
    }
}