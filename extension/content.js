// Velocitas Extension - Content Script

class VelocitasAI {
    constructor() {
      this.isEnabled = true; // Default, will be updated from storage
      this.themeClassName = 'velocitas-modern-theme';
      this.observer = null;
      this.debounceTimeout = null;
      this.observerRetryTimeout = null; // For retrying observer setup
      this.observerMaxRetries = 5;    // Max retries for observer setup
      this.observerRetryCount = 0;    // Current retry count
      this._initializeStateAndListeners();
    }

    _initializeStateAndListeners() {
      // Load stored enabled state
      chrome.storage.local.get(['enabled'], (result) => {
        this.isEnabled = result.enabled !== false;
        // _applyChanges will now handle the initial observer setup if enabled
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
        // Return true to indicate you wish to send a response asynchronously
        // (although in this specific case, sendResponse is called synchronously).
        return true;
    }

    toggle() {
      this.isEnabled = !this.isEnabled;
      chrome.storage.local.set({ enabled: this.isEnabled });
      this._applyChanges();
    }

    _disconnectObserver() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null; 
            console.log("Velocitas: MutationObserver disconnected.");
        }
        if (this.observerRetryTimeout) {
            clearTimeout(this.observerRetryTimeout); 
            this.observerRetryTimeout = null;
        }
        this.observerRetryCount = 0; 
    }

    _applyChanges() {
      if (this.isEnabled) {
        document.body.classList.add(this.themeClassName);
        
        // Add delay to allow Gmail to fully load
        setTimeout(() => {
          this.groupEmailsByDate();
        }, 2000); // Wait 2 seconds for Gmail to load
        
        // If observer isn't set up, try to set it up.
        if (!this.observer) {
            this.observerRetryCount = 0; // Reset retries when explicitly trying to apply changes
            this._setupMutationObserver(); 
        }
      } else {
        document.body.classList.remove(this.themeClassName);
        this._ungroupEmailsByDate();
        this._disconnectObserver(); // Centralized disconnect
      }
    }

    _getGmailEmailRows() {
        // Debug: Log current URL and wait state
        console.log("Velocitas: Current URL:", window.location.href);
        console.log("Velocitas: Document ready state:", document.readyState);
        
        // Try multiple selectors for Gmail email rows as Gmail's structure can vary
        const possibleSelectors = [
            // New Gmail interface selectors
            'tr[jsmodel]', // Gmail often uses jsmodel attribute on email rows  
            'tr[role="row"]', // ARIA role for table rows
            'tr.zA', // Classic Gmail selector
            'div[role="main"] tr.zA',
            '[role="main"] tr[jsmodel]',
            '[data-thread-perm-id]', // Gmail thread identifier
            'tr[data-thread-id]', // Alternative thread identifier
            
            // Broader selectors for debugging
            '[role="main"] tbody tr',
            '[role="main"] tr',
            'table.F tr.zA',
            '.BltHke tr.zA',
            'tr.btb', // Alternative Gmail row class
            'tr.Wg', // Another possible Gmail row class
            
            // Very broad selectors as fallback
            'tbody tr',
            'table tr'
        ];
        
        // Debug: Show what's available in the main area
        const mainArea = document.querySelector('[role="main"]');
        if (mainArea) {
            console.log("Velocitas: Main area found:", mainArea);
            console.log("Velocitas: Main area HTML preview:", mainArea.innerHTML.substring(0, 500));
            
            // Look for any table rows in main area
            const allTrs = mainArea.querySelectorAll('tr');
            console.log(`Velocitas: Found ${allTrs.length} total <tr> elements in main area`);
            if (allTrs.length > 0) {
                console.log("Velocitas: First TR element:", allTrs[0]);
                console.log("Velocitas: First TR classes:", allTrs[0].className);
                console.log("Velocitas: First TR attributes:", Array.from(allTrs[0].attributes).map(attr => `${attr.name}="${attr.value}"`));
            }
        } else {
            console.warn("Velocitas: No main area found");
            // Try to find any container that might hold emails
            const containers = document.querySelectorAll('.nH, .aeF, [role="tabpanel"]');
            console.log(`Velocitas: Found ${containers.length} potential containers`);
        }
        
        for (const selector of possibleSelectors) {
            try {
                const rows = document.querySelectorAll(selector);
                if (rows.length > 0) {
                    console.log(`Velocitas: Found ${rows.length} email rows with selector: ${selector}`);
                    
                    // Additional validation - check if these look like email rows
                    const firstRow = rows[0];
                    const hasEmailIndicators = firstRow.querySelector('span[email]') || 
                                             firstRow.querySelector('[data-hovercard-id]') ||
                                             firstRow.querySelector('.yW') || // Gmail sender name class
                                             firstRow.querySelector('.bog') || // Gmail subject class
                                             firstRow.textContent.includes('@') ||
                                             firstRow.querySelector('td.xY'); // Gmail date column
                    
                    if (hasEmailIndicators) {
                        console.log("Velocitas: Rows appear to be email rows (validation passed)");
                        return rows;
                    } else {
                        console.log("Velocitas: Rows found but don't appear to be email rows, continuing search...");
                    }
                }
            } catch (error) {
                console.warn(`Velocitas: Error with email row selector ${selector}:`, error);
            }
        }
        
        console.warn("Velocitas: No email rows found with any selector");
        
        // Final debug attempt - look for any elements that might contain email data
        const potentialEmailElements = document.querySelectorAll('[data-thread-id], [data-legacy-thread-id], .zA, .yW, .bog');
        console.log(`Velocitas: Found ${potentialEmailElements.length} potential email-related elements`);
        if (potentialEmailElements.length > 0) {
            console.log("Velocitas: Sample email element:", potentialEmailElements[0]);
        }
        
        return document.querySelectorAll(''); // Return empty NodeList
    }

    _getGmailEmailContainer(emailRows) {
        if (!emailRows || !emailRows.length) return null;
        
        // Try to find the tbody or table container
        let container = emailRows[0].closest('tbody');
        if (!container) {
            container = emailRows[0].closest('table');
        }
        if (!container) {
            container = emailRows[0].parentElement;
        }
        
        if (container) {
            console.log("Velocitas: Found email container:", container.tagName, container.className);
        }
        
        return container;
    }


    groupEmailsByDate() {
        console.log("Velocitas: Attempting to group emails by date.");
        this._ungroupEmailsByDate(); // Clear existing groups first

        const emailRows = this._getGmailEmailRows();
        if (!emailRows.length) {
            console.log("Velocitas: No email rows found to group.");
            return;
        }

        const emailContainer = this._getGmailEmailContainer(emailRows);
        if (!emailContainer) {
            console.warn("Velocitas: Email container not found.");
            return;
        }

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
            // Try multiple selectors for the date element
            const dateSelectors = [
                'td.xW.xY span[title]',
                'span[title*=":"]', // Look for spans with time in title
                '.xW span[title]',
                '.xY span[title]',
                'td span[title]'
            ];
            
            let dateElement = null;
            for (const selector of dateSelectors) {
                dateElement = row.querySelector(selector);
                if (dateElement && dateElement.title) {
                    break;
                }
            }
            
            if (!dateElement || !dateElement.title) {
                console.warn("Velocitas: Could not find date element for row:", row);
                return; 
            }

            const emailDateStr = dateElement.title;
            let emailDate = new Date(emailDateStr);

            if (isNaN(emailDate.getTime())) {
                // Fallback for relative dates
                const simpleDateMatch = emailDateStr.match(/^([a-zA-Z]{3})\s(\d{1,2})$/);
                if (simpleDateMatch) {
                    emailDate = new Date(`${simpleDateMatch[0]}, ${now.getFullYear()}`);
                }
                if (isNaN(emailDate.getTime())) {
                    console.warn("Velocitas: Could not parse date:", emailDateStr);
                    return;
                }
            }
            
            const emailDateDayOnly = new Date(emailDate.getFullYear(), emailDate.getMonth(), emailDate.getDate());

            let category;
            if (emailDateDayOnly.getTime() === today.getTime()) {
                category = "Today";
            } else if (emailDateDayOnly.getTime() === yesterday.getTime()) {
                category = "Yesterday";
            } else if (emailDateDayOnly >= last7DaysThreshold) {
                category = "Last 7 days";
            } else if (emailDateDayOnly >= last30DaysThreshold) {
                category = "Last 30 days";
            } else {
                category = "Older";
            }

            if (category !== currentGroup) {
                const headerId = `velocitas-group-${category.replace(/\s+/g, '-')}`;
                
                // Create header element
                const headerElement = document.createElement('tr');
                headerElement.id = headerId;
                headerElement.classList.add('velocitas-date-group-header');
                
                const headerCell = document.createElement('td');
                const colCount = row.cells.length > 0 ? row.cells.length : 6;
                headerCell.colSpan = colCount;
                headerCell.textContent = category;
                headerCell.style.cssText = `
                    background-color: #FFFACD !important;
                    color: #4A4A4A !important;
                    padding: 8px 18px !important;
                    font-weight: bold !important;
                    font-size: 13px !important;
                    border-top: 1px solid #FFEE58 !important;
                    border-bottom: 1px solid #FFEE58 !important;
                `;
                
                headerElement.appendChild(headerCell);
                
                try {
                    emailContainer.insertBefore(headerElement, row);
                    console.log(`Velocitas: Added header for ${category}`);
                } catch (error) {
                    console.error("Velocitas: Error inserting header:", error);
                }
                
                currentGroup = category;
            }
        });
        console.log("Velocitas: Email grouping completed.");
    }

    _ungroupEmailsByDate() {
        // console.log("Velocitas: Removing date groups.");
        const headers = document.querySelectorAll('.velocitas-date-group-header');
        headers.forEach(header => header.remove());
    }

    _setupMutationObserver() {
        // Clear any existing observer
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null; 
        }
        if (this.observerRetryTimeout) {
            clearTimeout(this.observerRetryTimeout);
            this.observerRetryTimeout = null;
        }

        // Wait a bit for Gmail to fully load
        setTimeout(() => {
            this._attemptObserverSetup();
        }, 1000);
    }

    _attemptObserverSetup() {
        const possibleSelectors = [
            'div[role="main"]',
            '[role="main"]',
            '.nH.bkK', // Gmail main container
            '.nH', // Gmail container
            'body'
        ];
        
        let targetNode = null;
        for (const selector of possibleSelectors) {
            try {
                targetNode = document.querySelector(selector);
                if (targetNode) {
                    console.log(`Velocitas: Found observer target with selector: ${selector}`);
                    break;
                }
            } catch (error) {
                console.warn(`Velocitas: Error with observer selector ${selector}:`, error);
            }
        }
        
        if (!targetNode) {
            this.observerRetryCount++;
            if (this.observerRetryCount <= this.observerMaxRetries) {
                console.warn(`Velocitas: Retrying observer setup (${this.observerRetryCount}/${this.observerMaxRetries})...`);
                this.observerRetryTimeout = setTimeout(() => {
                    if (this.isEnabled) {
                        this._attemptObserverSetup();
                    }
                }, 2000 * this.observerRetryCount);
            } else {
                console.error("Velocitas: Failed to set up observer after max retries.");
            }
            return;
        }

        // Reset retry count
        this.observerRetryCount = 0;

        const config = { 
            childList: true, 
            subtree: true, // Watch deeper changes
            attributes: false 
        };

        const callback = (mutationsList) => {
            if (!this.isEnabled) return;

            let shouldRegroup = false;
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList') {
                    // Check if any email rows were added or removed
                    const hasEmailChanges = Array.from(mutation.addedNodes).some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (node.matches && node.matches('tr.zA') || 
                         node.querySelector && node.querySelector('tr.zA'))
                    ) || Array.from(mutation.removedNodes).some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (node.matches && node.matches('tr.zA') || 
                         node.classList && node.classList.contains('velocitas-date-group-header'))
                    );
                    
                    if (hasEmailChanges) {
                        shouldRegroup = true;
                        break;
                    }
                }
            }
            
            if (shouldRegroup) {
                this.debouncedGroupEmails();
            }
        };

        try {
            this.observer = new MutationObserver(callback);
            this.observer.observe(targetNode, config);
            console.log("Velocitas: MutationObserver successfully set up");

            // Initialize debounced function
            if (!this.debouncedGroupEmails) {
                this.debouncedGroupEmails = () => {
                    clearTimeout(this.debounceTimeout);
                    this.debounceTimeout = setTimeout(() => {
                        if (this.isEnabled) {
                            this.groupEmailsByDate();
                        }
                    }, 1000);
                };
            }
        } catch (error) {
            console.error("Velocitas: Error creating MutationObserver:", error);
            // Retry setup
            this.observerRetryCount++;
            if (this.observerRetryCount <= this.observerMaxRetries) {
                this.observerRetryTimeout = setTimeout(() => {
                    if (this.isEnabled) {
                        this._attemptObserverSetup();
                    }
                }, 2000 * this.observerRetryCount);
            }
        }
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