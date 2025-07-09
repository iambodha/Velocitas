// VelocitasExtension.js - Main extension controller
// Convert the VelocitasExtension module to attach to window object and reference other modules from window
window.VelocitasExtension = class VelocitasExtension {
    constructor() {
        this.headerManager = new window.DateHeaderManager();
        this.emailLabeler = new window.EmailLabeler();
        this.emailSummarizer = new window.EmailSummarizer();
        this.individualEmailSummarizer = new window.IndividualEmailSummarizer();
        this.emailChatbox = new window.EmailChatbox();
        this.emailReplyAssistant = new window.EmailReplyAssistant();
        this.isEnabled = true;
        this.initialized = false;
        this.messageListener = null;
        
        // Add observer for dynamic content changes
        this.emailObserver = null;
        this.lastEmailCount = 0;
        this.observerTimeout = null;
        this.labeledEmails = new Map(); // Track labeled emails
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

        // Initialize email summarizer
        await this.emailSummarizer.init();
        
        // Initialize individual email summarizer
        await this.individualEmailSummarizer.init();

        // Initialize email chatbox
        await this.emailChatbox.init();

        // Initialize email reply assistant
        await this.emailReplyAssistant.init();

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
                        stats: this.headerManager.getStats(),
                        labelerStatus: this.emailLabeler.getStatus(),
                        cacheSize: this.emailLabeler.cache.size,
                        summarizerStatus: this.emailSummarizer.getStatus(),
                        individualSummarizerStatus: this.individualEmailSummarizer.getStatus(),
                        chatboxStatus: this.emailChatbox.getStatus(),
                        replyAssistantStatus: this.emailReplyAssistant.getStatus()
                    });
                } else if (message.action === 'cleanup') {
                    this.headerManager.cleanup();
                    sendResponse({ success: true });
                } else if (message.action === 'clearCache') {
                    this.emailLabeler.clearCache();
                    sendResponse({ success: true });
                } else if (message.action === 'refreshLabels') {
                    this._reapplyLabels();
                    sendResponse({ success: true });
                } else if (message.action === 'logEmailInfo') {
                    this._logEmailInformation();
                    sendResponse({ success: true });
                } else if (message.action === 'labelEmails') {
                    this._labelAllEmails();
                    sendResponse({ success: true });
                } else if (message.action === 'summarizeEmails') {
                    this._summarizeUnreadEmails();
                    sendResponse({ success: true });
                } else if (message.action === 'clearIndividualSummaryCache') {
                    this.individualEmailSummarizer.clearCache();
                    sendResponse({ success: true });
                } else if (message.action === 'clearIndividualSummary') {
                    this.individualEmailSummarizer.clearSummary();
                    sendResponse({ success: true });
                } else if (message.action === 'clearChatHistory') {
                    this.emailChatbox.clearChatHistory();
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

        console.log('Velocitas: Basic features initialized');
        
        // Auto-log and label email information on page load
        setTimeout(() => {
            this._logAndLabelEmails();
        }, 2000);
        
        // Set up dynamic email monitoring
        this._setupEmailObserver();
    }

    // Set up observer to monitor email list changes
    _setupEmailObserver() {
        if (!this.isEnabled) return;
        
        console.log('Velocitas: Setting up email observer...');
        
        // Disconnect existing observer
        if (this.emailObserver) {
            this.emailObserver.disconnect();
        }
        
        // Set up search detection
        this._setupSearchDetection();
        
        // Find the main email list container
        const emailListContainer = document.querySelector('[role="main"]') || 
                                 document.querySelector('.nH.bkK') ||
                                 document.querySelector('.nH.bkL') ||
                                 document.body;
        
        if (!emailListContainer) {
            console.warn('Velocitas: Could not find email list container');
            return;
        }
        
        // Create new observer
        this.emailObserver = new MutationObserver((mutations) => {
            let shouldReapplyLabels = false;
            
            mutations.forEach((mutation) => {
                // Check if email rows were added/removed
                if (mutation.type === 'childList') {
                    const addedNodes = Array.from(mutation.addedNodes);
                    const removedNodes = Array.from(mutation.removedNodes);
                    
                    // Check if any email rows were added or removed
                    const emailRowsAdded = addedNodes.some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (node.matches && node.matches('tr[class*="zA"]') || 
                         node.querySelector && node.querySelector('tr[class*="zA"]'))
                    );
                    
                    const emailRowsRemoved = removedNodes.some(node => 
                        node.nodeType === Node.ELEMENT_NODE && 
                        (node.matches && node.matches('tr[class*="zA"]') || 
                         node.querySelector && node.querySelector('tr[class*="zA"]'))
                    );
                    
                    if (emailRowsAdded || emailRowsRemoved) {
                        shouldReapplyLabels = true;
                    }
                }
            });
            
            if (shouldReapplyLabels) {
                this._debounceReapplyLabels();
            }
        });
        
        // Start observing
        this.emailObserver.observe(emailListContainer, {
            childList: true,
            subtree: true
        });
        
        console.log('Velocitas: Email observer set up successfully');
    }

    // Set up search detection
    _setupSearchDetection() {
        console.log('Velocitas: Setting up search detection...');
        
        // Set up URL-based search detection for Gmail SPA navigation
        this._setupUrlSearchDetection();
        
        // Try multiple strategies to find Gmail search box
        const findSearchBox = () => {
            const selectors = [
                'input[aria-label="Search mail"]',
                'input[placeholder*="Search"]',
                'input[placeholder*="search"]',
                'input[name="q"]',
                '.gb_hf input',
                'form[role="search"] input',
                '.asor input',
                '.gb_x input',
                'input[type="search"]',
                '.gb_Pd input',
                '.gb_uf input'
            ];
            
            for (const selector of selectors) {
                const element = document.querySelector(selector);
                if (element) {
                    console.log(`Velocitas: Found search box with selector: ${selector}`);
                    return element;
                }
            }
            return null;
        };
        
        // Try to find search box immediately
        let searchBox = findSearchBox();
        
        // If not found, try again after a delay (Gmail might still be loading)
        if (!searchBox) {
            setTimeout(() => {
                searchBox = findSearchBox();
                if (searchBox) {
                    this._attachSearchListeners(searchBox);
                } else {
                    console.warn('Velocitas: Could not find Gmail search box after retry');
                }
            }, 2000);
        } else {
            this._attachSearchListeners(searchBox);
        }
    }

    // Attach search event listeners
    _attachSearchListeners(searchBox) {
        // Remove existing search listeners
        if (this.searchEventHandler) {
            searchBox.removeEventListener('keydown', this.searchEventHandler);
            searchBox.removeEventListener('input', this.searchEventHandler);
        }
        
        // Create search event handler
        this.searchEventHandler = (event) => {
            if (event.type === 'keydown' && event.key === 'Enter') {
                // Search initiated with Enter key
                console.log('Velocitas: Search initiated with Enter key');
                this._handleSearchEvent(searchBox.value);
            } else if (event.type === 'input') {
                // Search query changed - debounce to avoid too many triggers
                clearTimeout(this.searchInputTimeout);
                this.searchInputTimeout = setTimeout(() => {
                    if (searchBox.value.trim()) {
                        console.log('Velocitas: Search query changed:', searchBox.value);
                        this._handleSearchEvent(searchBox.value);
                    }
                }, 1000); // Wait 1 second after user stops typing
            }
        };
        
        // Add search listeners
        searchBox.addEventListener('keydown', this.searchEventHandler);
        searchBox.addEventListener('input', this.searchEventHandler);
        
        console.log('Velocitas: Search detection set up successfully');
    }

    // Set up URL-based search detection for Gmail SPA navigation
    _setupUrlSearchDetection() {
        console.log('Velocitas: Setting up URL-based search detection...');
        
        // Track the current URL
        this.lastUrl = window.location.href;
        
        // Create URL change observer
        const urlObserver = new MutationObserver(() => {
            const currentUrl = window.location.href;
            if (currentUrl !== this.lastUrl) {
                this.lastUrl = currentUrl;
                console.log('Velocitas: URL changed to:', currentUrl);
                
                // Check if this is a search URL
                this._checkForSearchUrl(currentUrl);
            }
        });
        
        // Start observing for URL changes
        urlObserver.observe(document, { 
            subtree: true, 
            childList: true 
        });
        
        // Also listen for history changes
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;
        
        history.pushState = function(...args) {
            originalPushState.apply(history, args);
            setTimeout(() => {
                const currentUrl = window.location.href;
                console.log('Velocitas: History pushState - URL:', currentUrl);
                window.VelocitasExtensionInstance?._checkForSearchUrl(currentUrl);
            }, 100);
        };
        
        history.replaceState = function(...args) {
            originalReplaceState.apply(history, args);
            setTimeout(() => {
                const currentUrl = window.location.href;
                console.log('Velocitas: History replaceState - URL:', currentUrl);
                window.VelocitasExtensionInstance?._checkForSearchUrl(currentUrl);
            }, 100);
        };
        
        // Check current URL immediately
        this._checkForSearchUrl(window.location.href);
        
        console.log('Velocitas: URL-based search detection set up successfully');
    }

    // Check if URL indicates a search and extract search query
    _checkForSearchUrl(url) {
        // Gmail search URL patterns:
        // https://mail.google.com/mail/u/5/#search/test
        // https://mail.google.com/mail/u/0/#search/from%3Asomeone
        // https://mail.google.com/mail/u/0/#advanced-search/...
        
        const searchPatterns = [
            /#search\/(.+)$/,           // #search/query
            /#advanced-search\/(.+)$/,  // #advanced-search/query
            /\?q=([^&]+)/,              // ?q=query
            /search=([^&]+)/            // search=query
        ];
        
        for (const pattern of searchPatterns) {
            const match = url.match(pattern);
            if (match && match[1]) {
                const searchQuery = decodeURIComponent(match[1]);
                console.log(`Velocitas: Search detected from URL: "${searchQuery}"`);
                this._handleSearchEvent(searchQuery);
                return;
            }
        }
        
        // If we're not in a search URL but were previously searching, 
        // check if we navigated away from search
        if (this.wasInSearchMode && !this._isSearchUrl(url)) {
            console.log('Velocitas: Navigated away from search results');
            this.wasInSearchMode = false;
        }
    }

    // Check if URL represents a search page
    _isSearchUrl(url) {
        return url.includes('#search/') || 
               url.includes('#advanced-search/') || 
               url.includes('?q=') || 
               url.includes('search=');
    }

    // Handle search events
    _handleSearchEvent(searchQuery) {
        console.log(`Velocitas: Handling search event for query: "${searchQuery}"`);
        
        // Set search mode flag
        this.wasInSearchMode = true;
        
        // Start continuous labeling after a short delay to allow Gmail to load results
        setTimeout(() => {
            this._startContinuousLabeling();
        }, 1500);
    }

    // Start continuous labeling mode
    async _startContinuousLabeling() {
        console.log('Velocitas: Starting continuous labeling mode...');
        
        const emailData = this._extractEmailInfo();
        
        if (emailData.length === 0) {
            console.log('Velocitas: No emails found for continuous labeling');
            return;
        }
        
        console.log(`Velocitas: Found ${emailData.length} emails for continuous labeling`);
        
        // Create callback function to handle individual labels
        const onLabelCallback = (labeledEmail) => {
            console.log(`Velocitas: Adding label for "${labeledEmail.title}" - ${labeledEmail.category}`);
            this.emailLabeler.addSingleLabelToGmail(labeledEmail);
        };
        
        // Start continuous processing
        await this.emailLabeler.processEmailQueueContinuous(emailData, onLabelCallback);
        
        console.log('Velocitas: Continuous labeling completed');
    }

    // Debounced method to reapply labels
    _debounceReapplyLabels() {
        if (this.observerTimeout) {
            clearTimeout(this.observerTimeout);
        }
        
        this.observerTimeout = setTimeout(() => {
            this._reapplyLabels();
        }, 500); // Wait 500ms before reapplying
    }

    // Reapply labels to current email list
    async _reapplyLabels() {
        if (!this.isEnabled) return;
        
        console.log('Velocitas: Email list changed, reapplying labels...');
        
        const emailData = this._extractEmailInfo();
        const currentEmailCount = emailData.length;
        
        // Only proceed if we have emails and the count has changed
        if (currentEmailCount === 0) {
            console.log('Velocitas: No emails found, skipping reapply');
            return;
        }
        
        if (currentEmailCount === this.lastEmailCount) {
            console.log('Velocitas: Email count unchanged, checking for unlabeled emails...');
            this._checkAndLabelUnlabeled();
            return;
        }
        
        this.lastEmailCount = currentEmailCount;
        console.log(`Velocitas: Email count changed to ${currentEmailCount}, reapplying labels...`);
        
        // Process emails (this will use cache for existing emails)
        const labeledEmails = await this.emailLabeler.processEmailQueue(emailData);
        
        // Add visual labels to Gmail interface
        if (labeledEmails && labeledEmails.length > 0) {
            this.emailLabeler.addVisualLabelsToGmail(labeledEmails);
        }
    }

    // Check for unlabeled emails and apply labels
    _checkAndLabelUnlabeled() {
        const emailRows = document.querySelectorAll('tr[class*="zA"]');
        let unlabeledCount = 0;
        
        emailRows.forEach((row, index) => {
            const existingLabel = row.querySelector('.velocitas-email-label');
            if (!existingLabel) {
                unlabeledCount++;
                
                // Try to find cached data for this email
                const emailData = this._extractSingleEmailInfo(row, index);
                if (emailData) {
                    const emailId = this.emailLabeler._generateEmailId(emailData);
                    const cachedResult = this.emailLabeler._getFromCache(emailId);
                    
                    if (cachedResult) {
                        const labeledEmail = {
                            ...emailData,
                            category: cachedResult.category,
                            icon: cachedResult.icon,
                            color: cachedResult.color,
                            rowIndex: index
                        };
                        
                        this.emailLabeler._addLabelToEmailRow(row, labeledEmail);
                        console.log(`Velocitas: Reapplied cached label for "${emailData.title}"`);
                    }
                }
            }
        });
        
        if (unlabeledCount > 0) {
            console.log(`Velocitas: Found ${unlabeledCount} unlabeled emails, labels reapplied from cache`);
        }
    }

    // Extract email info from a single row
    _extractSingleEmailInfo(row, index) {
        try {
            // Extract title (subject)
            const titleElement = row.querySelector('[data-thread-id] span[id*=":"]') || 
                               row.querySelector('span[data-thread-id]') ||
                               row.querySelector('span[id*=":"]');
            const title = titleElement ? titleElement.textContent.trim() : 'No title';

            // Extract snippet
            const snippetElement = row.querySelector('.y2') || 
                                 row.querySelector('[class*="y2"]') ||
                                 row.querySelector('.bog');
            const snippet = snippetElement ? snippetElement.textContent.trim() : 'No snippet';

            // Extract sender
            const senderElement = row.querySelector('[email]') ||
                                row.querySelector('.yW') ||
                                row.querySelector('[class*="yW"]');
            const sender = senderElement ? 
                          (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                          'Unknown sender';

            // Extract date
            const dateElement = row.querySelector('[title*=":"]') ||
                              row.querySelector('.xY') ||
                              row.querySelector('[class*="xY"]');
            const date = dateElement ? 
                       (dateElement.getAttribute('title') || dateElement.textContent.trim()) : 
                       'No date';

            // Only return if we have meaningful data
            if (title !== 'No title' || snippet !== 'No snippet') {
                return {
                    title,
                    snippet: snippet.substring(0, 200) + (snippet.length > 200 ? '...' : ''),
                    sender,
                    date,
                    rowIndex: index
                };
            }
        } catch (error) {
            console.warn(`Velocitas: Error extracting email ${index}:`, error);
        }
        
        return null;
    }

    // Combined method to log and label emails
    async _logAndLabelEmails() {
        console.log('Velocitas: Gathering and labeling email information...');
        
        const emailData = this._extractEmailInfo();
        
        if (emailData.length === 0) {
            console.log('Velocitas: No emails found in current view');
            return;
        }

        // First, log the basic email information
        console.log(`Velocitas: Found ${emailData.length} emails:`);
        console.log('========================================');
        
        emailData.forEach((email, index) => {
            console.log(`Email ${index + 1}:`);
            console.log(`  Title: ${email.title}`);
            console.log(`  Snippet: ${email.snippet}`);
            console.log(`  Sender: ${email.sender}`);
            console.log(`  Date: ${email.date}`);
            console.log('---');
        });
        
        console.log('========================================');
        
        // Then, label the emails with AI
        console.log('Velocitas: Starting AI labeling process...');
        const labeledEmails = await this.emailLabeler.processEmailQueue(emailData);
        
        // Add visual labels to Gmail interface
        if (labeledEmails && labeledEmails.length > 0) {
            console.log('Velocitas: Adding visual labels to Gmail interface...');
            this.emailLabeler.addVisualLabelsToGmail(labeledEmails);
        }
        
        return labeledEmails;
    }

    // Method to label all emails (can be called manually)
    async _labelAllEmails() {
        const emailData = this._extractEmailInfo();
        
        if (emailData.length === 0) {
            console.log('Velocitas: No emails found to label');
            return;
        }

        console.log(`Velocitas: Labeling ${emailData.length} emails with AI...`);
        const labeledEmails = await this.emailLabeler.processEmailQueue(emailData);
        
        // Add visual labels to Gmail interface
        if (labeledEmails && labeledEmails.length > 0) {
            console.log('Velocitas: Adding visual labels to Gmail interface...');
            this.emailLabeler.addVisualLabelsToGmail(labeledEmails);
        }
        
        return labeledEmails;
    }

    // Method to log email information (existing functionality)
    _logEmailInformation() {
        console.log('Velocitas: Gathering email information...');
        
        const emailData = this._extractEmailInfo();
        
        if (emailData.length === 0) {
            console.log('Velocitas: No emails found in current view');
            return;
        }

        console.log(`Velocitas: Found ${emailData.length} emails:`);
        console.log('========================================');
        
        emailData.forEach((email, index) => {
            console.log(`Email ${index + 1}:`);
            console.log(`  Title: ${email.title}`);
            console.log(`  Snippet: ${email.snippet}`);
            console.log(`  Sender: ${email.sender}`);
            console.log(`  Date: ${email.date}`);
            console.log('---');
        });
        
        console.log('========================================');
    }

    // Extract basic email information from Gmail interface
    _extractEmailInfo() {
        const emails = [];
        
        // Try different Gmail selectors for email rows
        const emailRows = document.querySelectorAll('tr[class*="zA"]'); // Gmail email row class
        
        emailRows.forEach((row, index) => {
            try {
                // Extract title (subject)
                const titleElement = row.querySelector('[data-thread-id] span[id*=":"]') || 
                                   row.querySelector('span[data-thread-id]') ||
                                   row.querySelector('span[id*=":"]');
                const title = titleElement ? titleElement.textContent.trim() : 'No title';

                // Extract snippet
                const snippetElement = row.querySelector('.y2') || 
                                     row.querySelector('[class*="y2"]') ||
                                     row.querySelector('.bog');
                const snippet = snippetElement ? snippetElement.textContent.trim() : 'No snippet';

                // Extract sender
                const senderElement = row.querySelector('[email]') ||
                                    row.querySelector('.yW') ||
                                    row.querySelector('[class*="yW"]');
                const sender = senderElement ? 
                              (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                              'Unknown sender';

                // Extract date
                const dateElement = row.querySelector('[title*=":"]') ||
                                  row.querySelector('.xY') ||
                                  row.querySelector('[class*="xY"]');
                const date = dateElement ? 
                           (dateElement.getAttribute('title') || dateElement.textContent.trim()) : 
                           'No date';

                // Only add if we have meaningful data
                if (title !== 'No title' || snippet !== 'No snippet') {
                    emails.push({
                        title,
                        snippet: snippet.substring(0, 200) + (snippet.length > 200 ? '...' : ''),
                        sender,
                        date,
                        rowIndex: index
                    });
                }
            } catch (error) {
                console.warn(`Velocitas: Error extracting email ${index}:`, error);
            }
        });

        return emails;
    }

    // Method to summarize unread emails
    async _summarizeUnreadEmails() {
        console.log('Velocitas: Starting unread email summarization...');
        
        const unreadEmails = this.emailSummarizer.extractUnreadEmails();
        
        if (unreadEmails.length === 0) {
            console.log('Velocitas: No unread emails found');
            this.emailSummarizer.displaySummary({
                success: false,
                message: "No unread emails found in your inbox."
            });
            return;
        }

        console.log(`Velocitas: Found ${unreadEmails.length} unread emails, generating summary...`);
        
        // Generate and display summary
        const summaryResult = await this.emailSummarizer.generateSummary(unreadEmails);
        this.emailSummarizer.displaySummary(summaryResult);
        
        return summaryResult;
    }

    // Cleanup method
    cleanup() {
        console.log('Velocitas: Cleaning up VelocitasExtension');
        
        // Clean up observers
        if (this.emailObserver) {
            this.emailObserver.disconnect();
            this.emailObserver = null;
        }
        
        if (this.observerTimeout) {
            clearTimeout(this.observerTimeout);
            this.observerTimeout = null;
        }
        
        // Clean up components
        if (this.headerManager) {
            this.headerManager.cleanup();
        }
        
        if (this.emailSummarizer) {
            this.emailSummarizer.cleanup();
        }
        
        if (this.individualEmailSummarizer) {
            this.individualEmailSummarizer.cleanup();
        }
        
        if (this.emailChatbox) {
            this.emailChatbox.cleanup();
        }
        
        if (this.emailReplyAssistant) {
            this.emailReplyAssistant.cleanup();
        }
        
        // Remove message listener
        if (this.messageListener) {
            chrome.runtime.onMessage.removeListener(this.messageListener);
            this.messageListener = null;
        }
        
        // Remove theme class
        document.body.classList.remove('velocitas-modern-theme');
        
        // Clear tracked data
        this.labeledEmails.clear();
        
        this.initialized = false;
    }
}