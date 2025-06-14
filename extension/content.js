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

    // Email Extraction Class
    class EmailExtractor {
        constructor() {
            this.emailSelectors = {
                // Gmail email rows - these are common selectors
                emailRows: ['.zA', 'tr[jsaction*="click"]', '[role="main"] tr'],
                // Email content selectors
                sender: ['.yW', '.go span[email]', '.yP', '.qu [name]'],
                subject: ['.bog', '.aKS', '.y6 span[id]'],
                snippet: ['.y2', '.xS'],
                date: ['.xY span', '.zu .y2'],
                // Email thread/conversation selectors
                conversation: ['.ii.gt', '.adn.ads', '.gs .ii'],
                emailBody: ['.ii.gt .a3s', '.ii.gt div[dir="ltr"]', '.adn.ads .a3s']
            };
        }

        // Main method to extract the first email
        extractFirstEmail() {
            console.log('Velocitas: Starting email extraction...');
            
            // Wait for Gmail to load if needed
            if (!this._isGmailLoaded()) {
                console.log('Velocitas: Gmail not fully loaded, retrying in 2 seconds...');
                setTimeout(() => this.extractFirstEmail(), 2000);
                return null;
            }

            try {
                // Method 1: Try to find the first email in the list
                const emailFromList = this._extractFromEmailList();
                if (emailFromList) {
                    console.log('Velocitas: Extracted email from list view:', emailFromList);
                    
                    // Try to get full content by simulating a click
                    this._attemptToGetFullEmail(emailFromList);
                    return emailFromList;
                }

                // Method 2: Try to extract from currently open email
                const openEmail = this._extractFromOpenEmail();
                if (openEmail) {
                    console.log('Velocitas: Extracted from open email:', openEmail);
                    return openEmail;
                }

                console.log('Velocitas: No email found to extract');
                return null;

            } catch (error) {
                console.error('Velocitas: Error during email extraction:', error);
                return null;
            }
       }

        // Check if Gmail has loaded sufficiently
        _isGmailLoaded() {
            // Look for key Gmail elements
            const mainElements = [
                document.querySelector('[role="main"]'),
                document.querySelector('.nH'), // Gmail main container
                document.querySelector('.aKS'), // Subject container
                document.querySelector('.zA') // Email row
            ];
            
            return mainElements.some(el => el !== null);
        }

        // Extract email from the email list view
        _extractFromEmailList() {
            // Find the first email row
            const firstEmailRow = this._findFirstEmailRow();
            if (!firstEmailRow) {
                console.log('Velocitas: No email rows found');
                return null;
            }

            console.log('Velocitas: Found first email row:', firstEmailRow);

            // Extract basic information from the row
            const emailData = {
                type: 'list_view',
                element: firstEmailRow,
                sender: this._extractTextFromElement(firstEmailRow, this.emailSelectors.sender),
                subject: this._extractTextFromElement(firstEmailRow, this.emailSelectors.subject),
                snippet: this._extractTextFromElement(firstEmailRow, this.emailSelectors.snippet),
                date: this._extractTextFromElement(firstEmailRow, this.emailSelectors.date),
                isRead: !firstEmailRow.classList.contains('zE'), // Gmail uses zE for unread
                isStarred: firstEmailRow.querySelector('.aT5-aOt-I.J-JN-M-I-J6-H') !== null
            };

            return emailData;
        }

        // Find the first email row in Gmail
        _findFirstEmailRow() {
            for (const selector of this.emailSelectors.emailRows) {
                const rows = document.querySelectorAll(selector);
                if (rows.length > 0) {
                    // Filter to get actual email rows (not headers or other elements)
                    for (const row of rows) {
                        if (this._isValidEmailRow(row)) {
                            return row;
                        }
                    }
                }
            }
            return null;
        }

        // Check if an element is a valid email row
        _isValidEmailRow(element) {
            // Must have visible text content
            if (!element.textContent || element.textContent.trim().length < 10) {
                return false;
            }

            // Should not be a header or other non-email element
            if (element.classList.contains('velocitas-date-group-header') ||
                element.getAttribute('data-velocitas-header') === 'true') {
                return false;
            }

            // Should have typical email row characteristics
            const hasEmailContent = 
                element.querySelector('[email]') || // Has email address
                element.textContent.includes('@') || // Contains @ symbol
                element.querySelector('.yW, .yP, .go') || // Has sender elements
                element.querySelector('.bog, .aKS') || // Has subject elements
                (element.tagName === 'TR' && element.cells && element.cells.length > 3); // Table row with multiple cells

            return hasEmailContent;
        }

        // Extract from currently open email (conversation view)
        _extractFromOpenEmail() {
            // Look for open email conversation
            const conversationContainer = this._findElement(this.emailSelectors.conversation);
            if (!conversationContainer) {
                return null;
            }

            console.log('Velocitas: Found open conversation:', conversationContainer);

            const emailData = {
                type: 'conversation_view',
                element: conversationContainer,
                sender: this._extractTextFromElement(conversationContainer, this.emailSelectors.sender),
                subject: document.querySelector('.hP')?.textContent || '', // Subject in conversation view
                body: this._extractEmailBody(conversationContainer),
                date: this._extractTextFromElement(conversationContainer, this.emailSelectors.date)
            };

            return emailData;
        }

        // Extract email body content
        _extractEmailBody(container) {
            const bodyElement = this._findElement(this.emailSelectors.emailBody, container);
            if (!bodyElement) {
                return '';
            }

            // Get clean text content, preserving some formatting
            let bodyText = bodyElement.innerText || bodyElement.textContent || '';
            
            // Clean up common Gmail artifacts
            bodyText = bodyText
                .replace(/\n\s*\n\s*\n/g, '\n\n') // Remove excessive line breaks
                .replace(/^\s+|\s+$/g, '') // Trim whitespace
                .substring(0, 5000); // Limit length for console output

            return bodyText;
        }

        // Attempt to open the full email in current tab with loading overlay
        _attemptToGetFullEmail(emailData) {
            if (!emailData.element) return;

            console.log('Velocitas: Attempting to access full email content with loading overlay...');

            // Show loading overlay
            this._showLoadingOverlay();

            // Try multiple approaches to get email content
            this._tryMultipleExtractionMethods(emailData);
        }

        // Try multiple methods to extract email content
        _tryMultipleExtractionMethods(emailData) {
            console.log('Velocitas: Trying multiple extraction methods...');

            // Method 1: Try direct click simulation first
            if (this._tryDirectClickExtraction(emailData)) {
                return;
            }

            // Method 2: Try constructing URL and navigating (fallback)
            setTimeout(() => {
                this._tryUrlNavigationExtraction(emailData);
            }, 1000);
        }

        // Method 1: Try direct click simulation on the email row
        _tryDirectClickExtraction(emailData) {
            try {
                console.log('Velocitas: Attempting direct click extraction...');

                // Save original state
                const originalScrollY = window.scrollY;
                const originalActiveElement = document.activeElement;

                // Create a more natural click event
                const clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: 100,
                    clientY: 100,
                    button: 0,
                    buttons: 1
                });

                // Click the email row to open it
                emailData.element.dispatchEvent(clickEvent);

                // Wait for Gmail to potentially open the email
                setTimeout(() => {
                    const extractedContent = this._extractContentFromCurrentPage();
                    
                    if (extractedContent && extractedContent.body && extractedContent.body.trim().length > 50) {
                        console.log('Velocitas: Direct click extraction successful!');
                        this._printFullEmailContent(emailData, extractedContent);
                        this._hideLoadingOverlay();
                        
                        // Mark as unread and return to inbox
                        setTimeout(() => {
                            this._returnToInboxDirectly(originalScrollY);
                        }, 1000);
                        
                        return true;
                    } else {
                        console.log('Velocitas: Direct click extraction failed, content not sufficient');
                        return false;
                    }
                }, 2000);

                return true; // Indicate we're trying this method

            } catch (error) {
                console.warn('Velocitas: Direct click extraction failed:', error);
                return false;
            }
        }

        // Method 2: URL navigation with anti-detection measures
        _tryUrlNavigationExtraction(emailData) {
            console.log('Velocitas: Attempting URL navigation extraction...');

            // Get the email URL with anti-detection
            const emailUrl = this._getEmailUrlWithAntiDetection(emailData.element);
            if (!emailUrl) {
                console.log('Velocitas: Could not determine email URL, aborting extraction');
                this._hideLoadingOverlay();
                return;
            }

            // Use a more sophisticated navigation approach
            this._navigateWithAntiDetection(emailUrl, emailData);
        }

        // Get email URL with anti-detection measures
        _getEmailUrlWithAntiDetection(emailElement) {
            // Try to get URL without constructing it (more natural)
            const directLink = emailElement.querySelector('a[href*="mail.google.com"]');
            if (directLink && directLink.href) {
                console.log('Velocitas: Found direct link:', directLink.href);
                return directLink.href;
            }

            // Try clicking and capturing the URL change
            const capturedUrl = this._captureUrlFromClick(emailElement);
            if (capturedUrl) {
                return capturedUrl;
            }

            // Fallback to construction but with better thread ID detection
            return this._constructUrlSafely(emailElement);
        }

        // Capture URL from a simulated click
        _captureUrlFromClick(emailElement) {
            try {
                const originalUrl = window.location.href;
                let capturedUrl = null;

                // Set up a temporary URL change listener
                const urlWatcher = setInterval(() => {
                    if (window.location.href !== originalUrl) {
                        capturedUrl = window.location.href;
                        // Immediately restore original URL
                        window.history.replaceState({}, '', originalUrl);
                        clearInterval(urlWatcher);
                    }
                }, 50);

                // Simulate a very light click
                const lightClick = new MouseEvent('mousedown', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    button: 0
                });

                emailElement.dispatchEvent(lightClick);

                // Clean up after 500ms
                setTimeout(() => {
                    clearInterval(urlWatcher);
                }, 500);

                return capturedUrl;

            } catch (error) {
                console.warn('Velocitas: URL capture failed:', error);
                return null;
            }
        }

        // Construct URL more safely
        _constructUrlSafely(emailElement) {
            const threadId = this._extractEmailId(emailElement);
            if (!threadId) {
                return null;
            }

            // Use regular Gmail URL instead of popout to avoid detection
            const userMatch = window.location.href.match(/\/mail\/u\/(\d+)\//);
            const userNumber = userMatch ? userMatch[1] : '0';

            // Use regular Gmail conversation URL
            const conversationUrl = `https://mail.google.com/mail/u/${userNumber}/#inbox/${threadId}`;
            
            console.log('Velocitas: Constructed conversation URL:', conversationUrl);
            return conversationUrl;
        }

        // Navigate with anti-detection measures
        _navigateWithAntiDetection(emailUrl, originalEmailData) {
            console.log('Velocitas: Navigating with anti-detection measures...');

            // Add randomized delay to appear more human
            const humanDelay = 800 + Math.random() * 400; // 800-1200ms

            setTimeout(() => {
                // Store original URL
                const originalUrl = window.location.href;
                
                // Store extraction data
                sessionStorage.setItem('velocitas_extraction_data', JSON.stringify({
                    originalEmailData: originalEmailData,
                    originalUrl: originalUrl,
                    extractionInProgress: true,
                    timestamp: Date.now()
                }));

                // Add user agent spoofing and natural headers
                this._addAntiDetectionHeaders();

                // Navigate more naturally
                window.location.assign(emailUrl);

            }, humanDelay);
        }

        // Add anti-detection headers and properties
        _addAntiDetectionHeaders() {
            try {
                // Set natural document properties
                Object.defineProperty(document, 'webdriver', {
                    get: () => undefined
                });

                // Add natural timing
                if (window.performance && window.performance.timing) {
                    const timing = window.performance.timing;
                    Object.defineProperty(timing, 'loadEventEnd', {
                        get: () => timing.loadEventStart + Math.random() * 100
                    });
                }

            } catch (error) {
                console.warn('Velocitas: Could not set anti-detection properties:', error);
            }
        }

        // Return to inbox directly without URL navigation
        _returnToInboxDirectly(originalScrollY) {
            console.log('Velocitas: Returning to inbox directly...');

            // Try to find and click inbox navigation
            const inboxButton = document.querySelector('[title="Inbox"]') ||
                              document.querySelector('[aria-label="Inbox"]') ||
                              document.querySelector('a[href*="#inbox"]');

            if (inboxButton) {
                inboxButton.click();
                
                // Restore scroll position
                setTimeout(() => {
                    window.scrollTo(0, originalScrollY);
                    this._markFirstEmailAsUnread();
                }, 1000);
            } else {
                // Fallback: use browser back button
                window.history.back();
                
                setTimeout(() => {
                    window.scrollTo(0, originalScrollY);
                    this._markFirstEmailAsUnread();
                }, 1000);
            }
        }

        // Navigate to email and extract content
        _navigateAndExtract(emailUrl, originalEmailData) {
            // This method is kept for compatibility but now uses anti-detection
            this._navigateWithAntiDetection(emailUrl, originalEmailData);
        }

        // Enhanced extraction context handler
        _handleExtractionContext() {
            const extractionData = sessionStorage.getItem('velocitas_extraction_data');
            if (!extractionData) {
                return false;
            }

            try {
                const data = JSON.parse(extractionData);
                if (!data.extractionInProgress) {
                    return false;
                }

                // Check if extraction is too old (prevent stale states)
                const age = Date.now() - (data.timestamp || 0);
                if (age > 30000) { // 30 seconds
                    console.log('Velocitas: Extraction context too old, clearing...');
                    sessionStorage.removeItem('velocitas_extraction_data');
                    return false;
                }

                console.log('Velocitas: Found extraction context, processing email...');

                // Clear the extraction flag to prevent loops
                data.extractionInProgress = false;
                sessionStorage.setItem('velocitas_extraction_data', JSON.stringify(data));

                // Hide any existing loading overlay
                this._hideLoadingOverlay();

                // Wait for page to load, then extract with better detection
                this._waitAndExtractImproved(data);
                return true;

            } catch (error) {
                console.error('Velocitas: Error handling extraction context:', error);
                sessionStorage.removeItem('velocitas_extraction_data');
                this._hideLoadingOverlay();
                return false;
            }
        }

        // Improved wait and extract with better Gmail detection
        _waitAndExtractImproved(extractionData) {
            let retryCount = 0;
            const maxRetries = 15; // Increased retries

            const attemptExtraction = () => {
                retryCount++;
                console.log(`Velocitas: Extraction attempt ${retryCount}/${maxRetries}`);

                // Check if we're on an error page or Gmail blocked us
                if (this._isErrorPage()) {
                    console.log('Velocitas: Detected error page, returning to inbox...');
                    this._returnToInbox(extractionData.originalUrl);
                    return;
                }

                // Wait for Gmail to load properly
                if (!this._isGmailFullyLoaded()) {
                    if (retryCount < maxRetries) {
                        setTimeout(attemptExtraction, 1000);
                        return;
                    }
                }

                // Extract content
                const emailContent = this._extractContentFromCurrentPage();
                
                if (emailContent && (emailContent.body && emailContent.body.trim().length > 20)) {
                    console.log('Velocitas: Email content extracted successfully');
                    
                    // Print the extracted content
                    this._printFullEmailContent(extractionData.originalEmailData, emailContent);
                    
                    // Return to inbox
                    this._finalizeExtractionAndReturn(extractionData);
                    
                } else if (retryCount < maxRetries) {
                    // Try again after a delay
                    setTimeout(attemptExtraction, 1000);
                } else {
                    console.log('Velocitas: Failed to extract email content after max retries');
                    this._returnToInbox(extractionData.originalUrl);
                }
            };

            // Start extraction after a longer delay to let page settle
            setTimeout(attemptExtraction, 3000);
        }

        // Check if we're on an error page
        _isErrorPage() {
            const errorIndicators = [
                document.querySelector('[class*="error"]'),
                document.querySelector('[id*="error"]'),
                document.title.toLowerCase().includes('error'),
                document.body.textContent.includes('Something went wrong'),
                document.body.textContent.includes('This page isn\'t working'),
                window.location.href.includes('error')
            ];

            return errorIndicators.some(indicator => indicator);
        }

        // Check if Gmail is fully loaded
        _isGmailFullyLoaded() {
            const loadedIndicators = [
                document.querySelector('.ii.gt'), // Gmail conversation
                document.querySelector('.gs'), // Gmail message
                document.querySelector('.a3s'), // Email body
                document.querySelector('.hP') // Email subject
            ];

            return loadedIndicators.some(indicator => indicator) && 
                   document.readyState === 'complete';
        }

        // Show loading overlay
        _showLoadingOverlay() {
            // Remove existing overlay if any
            this._hideLoadingOverlay();

            const overlay = document.createElement('div');
            overlay.id = 'velocitas-loading-overlay';
            overlay.innerHTML = `
                <div class="velocitas-loading-container">
                    <div class="velocitas-spinner"></div>
                    <div class="velocitas-loading-text">Extracting email content...</div>
                    <div class="velocitas-loading-subtext">Please wait while we process your email</div>
                </div>
            `;

            // Add styles
            overlay.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background: rgba(255, 255, 255, 0.95) !important;
                backdrop-filter: blur(5px) !important;
                z-index: 999999 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            `;

            // Add container styles
            const containerStyle = `
                <style id="velocitas-loading-styles">
                .velocitas-loading-container {
                    text-align: center !important;
                    padding: 40px !important;
                    background: white !important;
                    border-radius: 12px !important;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2) !important;
                    max-width: 400px !important;
                    width: 90% !important;
                }
                
                .velocitas-spinner {
                    width: 50px !important;
                    height: 50px !important;
                    border: 4px solid #f3f3f3 !important;
                    border-top: 4px solid #FFD700 !important;
                    border-radius: 50% !important;
                    animation: velocitas-spin 1s linear infinite !important;
                    margin: 0 auto 20px auto !important;
                }
                
                @keyframes velocitas-spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                .velocitas-loading-text {
                    font-size: 18px !important;
                    font-weight: 600 !important;
                    color: #333 !important;
                    margin-bottom: 8px !important;
                }
                
                .velocitas-loading-subtext {
                    font-size: 14px !important;
                    color: #666 !important;
                    margin-bottom: 0 !important;
                }
                </style>
            `;

            document.head.insertAdjacentHTML('beforeend', containerStyle);
            document.body.appendChild(overlay);

            console.log('Velocitas: Loading overlay displayed');
        }

        // Hide loading overlay
        _hideLoadingOverlay() {
            const overlay = document.getElementById('velocitas-loading-overlay');
            const styles = document.getElementById('velocitas-loading-styles');
            
            if (overlay) {
                overlay.remove();
            }
            if (styles) {
                styles.remove();
            }
        }

        // Extract content from the current page
        _extractContentFromCurrentPage() {
            const extractors = {
                sender: ['.go span[email]', '.qu [name]', '.yP', '.gs .gD [email]', '.hP .qu'],
                subject: ['.hP', '.aKS', '.bog', '.ha h2', '.ii.gt .a3s h1'],
                body: ['.ii.gt .a3s', '.adn.ads .a3s', '.gs div[dir="ltr"]', '.ii.gt div[dir="ltr"]'],
                date: ['.g3', '.xY span', '.gs .g3', '.qu .g3']
            };

            const content = {};

            for (const [key, selectors] of Object.entries(extractors)) {
                for (const selector of selectors) {
                    const element = document.querySelector(selector);
                    if (element) {
                        if (key === 'body') {
                            content[key] = element.innerText || element.textContent || '';
                        } else {
                            content[key] = element.getAttribute('email') || 
                                         element.getAttribute('title') || 
                                         element.innerText || 
                                         element.textContent || '';
                        }
                        if (content[key] && content[key].trim()) {
                            break;
                        }
                    }
                }
            }

            return content;
        }

        // Finalize extraction and return to inbox
        _finalizeExtractionAndReturn(extractionData) {
            console.log('Velocitas: Finalizing extraction and returning to inbox...');

            // Clean up extraction data
            sessionStorage.removeItem('velocitas_extraction_data');

            // Return to inbox after a short delay
            setTimeout(() => {
                this._returnToInbox(extractionData.originalUrl);
            }, 1000);
        }

        // Return to inbox and mark email as unread
        _returnToInbox(originalUrl) {
            console.log('Velocitas: Returning to inbox...');

            // Navigate back to inbox
            window.location.href = originalUrl;

            // Set up a listener for when we return to mark email as unread
            sessionStorage.setItem('velocitas_mark_unread', 'true');
        }

        // Check if we need to mark an email as unread after returning
        _handleMarkUnreadOnReturn() {
            const shouldMarkUnread = sessionStorage.getItem('velocitas_mark_unread');
            if (shouldMarkUnread === 'true') {
                sessionStorage.removeItem('velocitas_mark_unread');
                
                // Wait for inbox to load, then mark first email as unread
                setTimeout(() => {
                    this._markFirstEmailAsUnread();
                }, 2000);
            }
        }

        // Mark the first email as unread
        _markFirstEmailAsUnread() {
            const firstEmailRow = this._findFirstEmailRow();
            if (firstEmailRow) {
                console.log('Velocitas: Marking first email as unread...');
                
                // Method 1: Try to find and use Gmail's mark as unread button directly
                if (this._tryMarkUnreadWithButton(firstEmailRow)) {
                    return;
                }
                
                // Method 2: Use keyboard shortcut without clicking the email
                if (this._tryMarkUnreadWithKeyboard(firstEmailRow)) {
                    return;
                }
                
                // Method 3: Modify CSS classes directly as fallback
                this._markUnreadWithClasses(firstEmailRow);
            }
        }

        // Method 1: Try to find and click the mark as unread button
        _tryMarkUnreadWithButton(emailRow) {
            try {
                // Look for unread button in various locations
                const unreadButtonSelectors = [
                    '[data-tooltip="Mark as unread"]',
                    '[aria-label*="Mark as unread"]',
                    '[title*="Mark as unread"]',
                    '.ar9[data-tooltip="Mark as unread"]',
                    '.T-I-J3[data-tooltip="Mark as unread"]'
                ];

                // First check in the email row itself
                for (const selector of unreadButtonSelectors) {
                    const button = emailRow.querySelector(selector);
                    if (button) {
                        console.log('Velocitas: Found unread button in email row');
                        button.click();
                        return true;
                    }
                }

                // Check in the toolbar area
                for (const selector of unreadButtonSelectors) {
                    const button = document.querySelector(selector);
                    if (button) {
                        console.log('Velocitas: Found unread button in toolbar');
                        
                        // Select the email first (without opening it)
                        const checkbox = emailRow.querySelector('input[type="checkbox"]') ||
                                        emailRow.querySelector('.oZ-x3-V');
                        
                        if (checkbox) {
                            checkbox.click(); // Just select, don't open
                            
                            setTimeout(() => {
                                button.click();
                                console.log('Velocitas: Clicked unread button');
                            }, 200);
                            
                            return true;
                        }
                    }
                }

                return false;

            } catch (error) {
                console.warn('Velocitas: Button method failed:', error);
                return false;
            }
        }

        // Method 2: Use keyboard shortcut without clicking the email
        _tryMarkUnreadWithKeyboard(emailRow) {
            try {
                console.log('Velocitas: Trying keyboard shortcut method...');
                
                // Select the email using checkbox instead of clicking the row
                const checkbox = emailRow.querySelector('input[type="checkbox"]') ||
                                emailRow.querySelector('.oZ-x3-V') ||
                                emailRow.querySelector('[role="checkbox"]');
                
                if (checkbox) {
                    // Check the checkbox to select the email (doesn't open it)
                    checkbox.click();
                    
                    setTimeout(() => {
                        // Gmail shortcut: Shift+U to mark as unread
                        const keyEvent = new KeyboardEvent('keydown', {
                            key: 'u',
                            code: 'KeyU',
                            shiftKey: true,
                            bubbles: true,
                            cancelable: true
                        });
                        
                        document.dispatchEvent(keyEvent);
                        
                        // Also try the keyup event for better compatibility
                        const keyUpEvent = new KeyboardEvent('keyup', {
                            key: 'u',
                            code: 'KeyU',
                            shiftKey: true,
                            bubbles: true,
                            cancelable: true
                        });
                        
                        document.dispatchEvent(keyUpEvent);
                        
                        console.log('Velocitas: Sent keyboard shortcut Shift+U');
                        
                        // Uncheck the checkbox after marking as unread
                        setTimeout(() => {
                            if (checkbox.checked) {
                                checkbox.click();
                            }
                        }, 300);
                        
                    }, 300);
                    
                    return true;
                }
                
                return false;

            } catch (error) {
                console.warn('Velocitas: Keyboard method failed:', error);
                return false;
            }
        }

        // Method 3: Modify CSS classes directly (visual feedback)
        _markUnreadWithClasses(emailRow) {
            try {
                console.log('Velocitas: Using CSS class method as fallback...');
                
                // Gmail uses different classes for read/unread states
                emailRow.classList.remove('yW'); // Remove read class
                emailRow.classList.add('zE'); // Add unread class
                
                // Also try to modify other read indicators
                const readIndicators = emailRow.querySelectorAll('.yW, .yP');
                readIndicators.forEach(indicator => {
                    indicator.classList.remove('yW', 'yP');
                    indicator.classList.add('zE');
                });
                
                // Make the email appear bold (unread styling)
                const subjectElement = emailRow.querySelector('.bog, .aKS, .y6');
                if (subjectElement) {
                    subjectElement.style.fontWeight = 'bold';
                }
                
                console.log('Velocitas: Applied unread CSS classes');

            } catch (error) {
                console.warn('Velocitas: CSS class method failed:', error);
            }
        }

        // Extract Gmail email ID from various possible sources
        _extractEmailId(emailElement) {
            // Try various attributes that Gmail uses for email identification
            const possibleIdSources = [
                emailElement.getAttribute('data-thread-id'),
                emailElement.getAttribute('data-legacy-thread-id'),
                emailElement.getAttribute('jsaction'),
                emailElement.id,
                emailElement.querySelector('[data-thread-id]')?.getAttribute('data-thread-id'),
                emailElement.querySelector('[jsaction]')?.getAttribute('jsaction')
            ];

            for (const source of possibleIdSources) {
                if (source) {
                    // Extract ID from jsaction or other attributes
                    const idMatch = source.match(/[a-f0-9]{16,}/i);
                    if (idMatch) {
                        return idMatch[0];
                    }
                }
            }

            // Try to extract from data-legacy-thread-id or similar
            const threadIdElement = emailElement.closest('[data-legacy-thread-id]') || 
                                   emailElement.closest('[id*="thread"]') ||
                                   emailElement.querySelector('[id*="thread"]');
            
            if (threadIdElement) {
                const threadId = threadIdElement.getAttribute('data-legacy-thread-id') || 
                               threadIdElement.id;
                if (threadId) {
                    const idMatch = threadId.match(/[a-f0-9]{16,}/i);
                    if (idMatch) {
                        return idMatch[0];
                    }
                }
            }

            return null;
        }

        // Print the full email content with original metadata
        _printFullEmailContent(originalEmailData, extractedContent) {
            console.log('\n' + '='.repeat(70));
            console.log('📧 VELOCITAS - COMPLETE EMAIL EXTRACTED (IN-TAB)');
            console.log('='.repeat(70));
            
            console.log(`📤 From: ${extractedContent.sender || originalEmailData.sender || 'Unknown Sender'}`);
            console.log(`📝 Subject: ${extractedContent.subject || originalEmailData.subject || '(No Subject)'}`);
            console.log(`📅 Date: ${extractedContent.date || originalEmailData.date || 'Unknown Date'}`);
            
            if (originalEmailData.isRead !== undefined) {
                console.log(`👁️  Read Status: ${originalEmailData.isRead ? 'Read' : 'Unread'}`);
            }
            if (originalEmailData.isStarred !== undefined) {
                console.log(`⭐ Starred: ${originalEmailData.isStarred ? 'Yes' : 'No'}`);
            }
            
            if (extractedContent.body && extractedContent.body.trim()) {
                console.log('\n📄 FULL EMAIL CONTENT:');
                console.log('-'.repeat(50));
                // Clean and limit the body content
                const cleanBody = extractedContent.body
                    .replace(/\n\s*\n\s*\n/g, '\n\n')
                    .replace(/^\s+|\s+$/g, '')
                    .substring(0, 5000);
                console.log(cleanBody);
                console.log('-'.repeat(50));
            } else if (originalEmailData.snippet) {
                console.log(`📄 Preview: ${originalEmailData.snippet}`);
            }
            
            console.log('✅ Extraction completed - returning to inbox and marking as unread');
            console.log('='.repeat(70) + '\n');
        }

        // Public method to manually trigger extraction (for debugging)
        manualExtract() {
            console.log('Velocitas: Manual extraction triggered');
            return this.extractFirstEmail();
        }

        // Main method to extract multiple emails
        extractMultipleEmails(count = 10) {
            console.log(`Velocitas: Starting extraction of ${count} emails...`);
            
            // Wait for Gmail to load if needed
            if (!this._isGmailLoaded()) {
                console.log('Velocitas: Gmail not fully loaded, retrying in 2 seconds...');
                setTimeout(() => this.extractMultipleEmails(count), 2000);
                return null;
            }

            try {
                // Find multiple email rows
                const emailRows = this._findMultipleEmailRows(count);
                if (emailRows.length === 0) {
                    console.log('Velocitas: No email rows found');
                    return null;
                }

                console.log(`Velocitas: Found ${emailRows.length} email rows to extract`);

                // Extract basic information from all rows
                const emailsData = emailRows.map((row, index) => {
                    const isCurrentlyUnread = row.classList.contains('zE'); // Gmail uses zE for unread
                    return {
                        type: 'list_view',
                        element: row,
                        index: index + 1,
                        sender: this._extractTextFromElement(row, this.emailSelectors.sender),
                        subject: this._extractTextFromElement(row, this.emailSelectors.subject),
                        snippet: this._extractTextFromElement(row, this.emailSelectors.snippet),
                        date: this._extractTextFromElement(row, this.emailSelectors.date),
                        isRead: !isCurrentlyUnread, // True if read, false if unread
                        wasOriginallyUnread: isCurrentlyUnread, // Track original unread state
                        isStarred: row.querySelector('.aT5-aOt-I.J-JN-M-I-J6-H') !== null
                    };
                });

                // Start processing all emails
                this._processMultipleEmails(emailsData);
                return emailsData;

            } catch (error) {
                console.error('Velocitas: Error during multiple email extraction:', error);
                return null;
            }
        }

        // Find multiple email rows in Gmail
        _findMultipleEmailRows(count) {
            const foundRows = [];
            
            for (const selector of this.emailSelectors.emailRows) {
                const rows = document.querySelectorAll(selector);
                if (rows.length > 0) {
                    // Filter to get actual email rows (not headers or other elements)
                    for (const row of rows) {
                        if (this._isValidEmailRow(row) && foundRows.length < count) {
                            foundRows.push(row);
                        }
                    }
                }
                
                // Break if we have enough emails
                if (foundRows.length >= count) {
                    break;
                }
            }
            
            return foundRows.slice(0, count);
        }

        // Process multiple emails with syncing overlay
        _processMultipleEmails(emailsData) {
            console.log(`Velocitas: Processing ${emailsData.length} emails with syncing overlay...`);

            // Show syncing overlay
            this._showSyncingOverlay(emailsData.length);

            // Initialize tracking
            this.multiEmailTracking = {
                total: emailsData.length,
                completed: 0,
                failed: 0,
                extractedEmails: [],
                currentIndex: 0
            };

            // Process emails sequentially to avoid overwhelming Gmail
            this._processNextEmail(emailsData);
        }

        // Process emails one by one
        _processNextEmail(emailsData) {
            const tracking = this.multiEmailTracking;
            
            if (tracking.currentIndex >= emailsData.length) {
                // All emails processed
                this._finishMultiEmailExtraction();
                return;
            }

            const currentEmail = emailsData[tracking.currentIndex];
            console.log(`Velocitas: Processing email ${tracking.currentIndex + 1}/${tracking.total}: ${currentEmail.subject}`);

            // Update overlay progress
            this._updateSyncingProgress(tracking.currentIndex + 1, tracking.total, currentEmail.subject);

            // Try to get full content for this email
            this._attemptToGetFullEmailInSequence(currentEmail, emailsData);
        }

        // Get full email content for sequential processing
        _attemptToGetFullEmailInSequence(emailData, allEmailsData) {
            if (!emailData.element) {
                this._handleEmailProcessingComplete(false, emailData, allEmailsData);
                return;
            }

            console.log(`Velocitas: Attempting to get full content for email ${emailData.index}...`);

            // Try direct click extraction first (faster)
            this._tryDirectClickExtractionSequential(emailData, allEmailsData);
        }

        // Direct click extraction for sequential processing
        _tryDirectClickExtractionSequential(emailData, allEmailsData) {
            try {
                // Save original state
                const originalScrollY = window.scrollY;

                // Create a natural click event
                const clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true,
                    clientX: 100,
                    clientY: 100,
                    button: 0,
                    buttons: 1
                });

                // Click the email row to open it
                emailData.element.dispatchEvent(clickEvent);

                // Wait for Gmail to potentially open the email
                setTimeout(() => {
                    const extractedContent = this._extractContentFromCurrentPage();
                    
                    if (extractedContent && extractedContent.body && extractedContent.body.trim().length > 50) {
                        console.log(`Velocitas: Direct click extraction successful for email ${emailData.index}!`);
                        
                        // Store the extracted content
                        emailData.extractedContent = extractedContent;
                        this.multiEmailTracking.extractedEmails.push(emailData);
                        
                        // Return to inbox quickly
                        this._returnToInboxQuickly(originalScrollY, () => {
                            this._handleEmailProcessingComplete(true, emailData, allEmailsData);
                        });
                        
                    } else {
                        console.log(`Velocitas: Direct click extraction failed for email ${emailData.index}, trying URL navigation...`);
                        this._tryUrlNavigationExtractionSequential(emailData, allEmailsData);
                    }
                }, 2000);

            } catch (error) {
                console.warn(`Velocitas: Direct click extraction failed for email ${emailData.index}:`, error);
                this._tryUrlNavigationExtractionSequential(emailData, allEmailsData);
            }
        }

        // URL navigation extraction for sequential processing
        _tryUrlNavigationExtractionSequential(emailData, allEmailsData) {
            console.log(`Velocitas: Attempting URL navigation for email ${emailData.index}...`);

            const emailUrl = this._getEmailUrlWithAntiDetection(emailData.element);
            if (!emailUrl) {
                console.log(`Velocitas: Could not determine email URL for email ${emailData.index}`);
                this._handleEmailProcessingComplete(false, emailData, allEmailsData);
                return;
            }

            // Store context for this specific email
            sessionStorage.setItem('velocitas_extraction_data', JSON.stringify({
                originalEmailData: emailData,
                allEmailsData: allEmailsData,
                originalUrl: window.location.href,
                extractionInProgress: true,
                timestamp: Date.now(),
                isMultiEmail: true
            }));

            // Navigate to email
            setTimeout(() => {
                window.location.assign(emailUrl);
            }, 1000 + Math.random() * 500); // Randomized delay
        }

        // Handle completion of individual email processing
        _handleEmailProcessingComplete(success, emailData, allEmailsData) {
            const tracking = this.multiEmailTracking;
            
            if (success) {
                tracking.completed++;
                console.log(`Velocitas: Successfully processed email ${emailData.index} (${tracking.completed}/${tracking.total})`);
            } else {
                tracking.failed++;
                console.log(`Velocitas: Failed to process email ${emailData.index} (${tracking.failed} failed)`);
            }

            // Move to next email
            tracking.currentIndex++;

            // Small delay before processing next email to be gentle on Gmail
            setTimeout(() => {
                this._processNextEmail(allEmailsData);
            }, 1500);
        }

        // Quick return to inbox for sequential processing
        _returnToInboxQuickly(originalScrollY, callback) {
            // Try to find and click inbox navigation
            const inboxButton = document.querySelector('[title="Inbox"]') ||
                              document.querySelector('[aria-label="Inbox"]') ||
                              document.querySelector('a[href*="#inbox"]');

            if (inboxButton) {
                inboxButton.click();
                setTimeout(() => {
                    window.scrollTo(0, originalScrollY);
                    if (callback) callback();
                }, 800);
            } else {
                // Fallback: use browser back button
                window.history.back();
                setTimeout(() => {
                    window.scrollTo(0, originalScrollY);
                    if (callback) callback();
                }, 800);
            }
        }

        // Finish multi-email extraction
        _finishMultiEmailExtraction() {
            const tracking = this.multiEmailTracking;
            console.log(`Velocitas: Finished processing all emails. Success: ${tracking.completed}, Failed: ${tracking.failed}`);

            // Print all extracted emails to console
            this._printAllExtractedEmails();

            // Mark all processed emails as unread
            this._markAllEmailsAsUnread(() => {
                // Hide syncing overlay
                this._hideSyncingOverlay();
                
                // Clean up tracking
                delete this.multiEmailTracking;
                
                console.log('Velocitas: Multi-email extraction completed!');
            });
        }

        // Print all extracted emails to console
        _printAllExtractedEmails() {
            console.log('\n' + '='.repeat(80));
            console.log('📧 VELOCITAS - MULTIPLE EMAILS EXTRACTED');
            console.log('='.repeat(80));
            
            const tracking = this.multiEmailTracking;
            console.log(`✅ Successfully extracted: ${tracking.completed} emails`);
            console.log(`❌ Failed to extract: ${tracking.failed} emails`);
            console.log(`📊 Total processed: ${tracking.total} emails`);
            console.log('='.repeat(80));

            tracking.extractedEmails.forEach((emailData, index) => {
                console.log(`\n📧 EMAIL ${index + 1}:`);
                console.log('-'.repeat(40));
                console.log(`📤 From: ${emailData.extractedContent?.sender || emailData.sender || 'Unknown Sender'}`);
                console.log(`📝 Subject: ${emailData.extractedContent?.subject || emailData.subject || '(No Subject)'}`);
                console.log(`📅 Date: ${emailData.extractedContent?.date || emailData.date || 'Unknown Date'}`);
                console.log(`👁️  Read Status: ${emailData.isRead ? 'Read' : 'Unread'}`);
                console.log(`⭐ Starred: ${emailData.isStarred ? 'Yes' : 'No'}`);
                
                if (emailData.extractedContent?.body && emailData.extractedContent.body.trim()) {
                    console.log('\n📄 FULL EMAIL CONTENT:');
                    console.log('- '.repeat(20));
                    const cleanBody = emailData.extractedContent.body
                        .replace(/\n\s*\n\s*\n/g, '\n\n')
                        .replace(/^\s+|\s+$/g, '')
                        .substring(0, 2000); // Shorter for multiple emails
                    console.log(cleanBody);
                    console.log('- '.repeat(20));
                } else if (emailData.snippet) {
                    console.log(`📄 Preview: ${emailData.snippet}`);
                }
            });

            console.log('\n' + '='.repeat(80));
            console.log('✅ All emails have been extracted and will be marked as unread');
            console.log('='.repeat(80) + '\n');
        }

        // Mark all processed emails as unread (only if they were originally unread)
        _markAllEmailsAsUnread(callback) {
            console.log('Velocitas: Checking which emails need to be marked as unread...');
            
            const tracking = this.multiEmailTracking;
            const emailsToMarkUnread = tracking.extractedEmails.filter(email => email.wasOriginallyUnread);
            
            if (emailsToMarkUnread.length === 0) {
                console.log('Velocitas: No emails need to be marked as unread (none were originally unread)');
                if (callback) callback();
                return;
            }
            
            console.log(`Velocitas: Marking ${emailsToMarkUnread.length} emails as unread (out of ${tracking.total} processed)`);
            
            let markedCount = 0;
            
            emailsToMarkUnread.forEach((emailData, index) => {
                setTimeout(() => {
                    this._markSingleEmailAsUnreadImproved(emailData.element, emailData.index, emailData.subject);
                    markedCount++;
                    
                    if (markedCount === emailsToMarkUnread.length) {
                        setTimeout(() => {
                            if (callback) callback();
                        }, 1000);
                    }
                }, index * 300); // Longer stagger for better success rate
            });
        }

        // Improved single email unread marking
        _markSingleEmailAsUnreadImproved(emailRow, emailNumber, emailSubject) {
            console.log(`Velocitas: Marking email ${emailNumber} as unread: "${emailSubject}"`);
            
            try {
                // First, ensure we can find the email row
                if (!emailRow || !document.contains(emailRow)) {
                    console.warn(`Velocitas: Email row ${emailNumber} not found in DOM`);
                    return;
                }

                // Method 1: Try selecting the email and using keyboard shortcut
                const checkbox = emailRow.querySelector('input[type="checkbox"]') ||
                                emailRow.querySelector('.oZ-x3-V') ||
                                emailRow.querySelector('[role="checkbox"]') ||
                                emailRow.querySelector('div[role="checkbox"]');
                
                if (checkbox) {
                    console.log(`Velocitas: Found checkbox for email ${emailNumber}, attempting keyboard shortcut`);
                    
                    // Ensure checkbox is not already checked
                    if (!checkbox.checked) {
                        // Check the checkbox to select the email
                        checkbox.click();
                        
                        // Wait a bit for Gmail to register the selection
                        setTimeout(() => {
                            // Focus on the main Gmail area to ensure keyboard events work
                            const gmailMain = document.querySelector('[role="main"]') || 
                                            document.querySelector('.nH') || 
                                            document.body;
                            gmailMain.focus();
                            
                            // Send the keyboard shortcut
                            this._sendUnreadKeyboardShortcut();
                            
                            // Uncheck the checkbox after a delay
                            setTimeout(() => {
                                if (checkbox.checked) {
                                    checkbox.click();
                                }
                                console.log(`Velocitas: Completed unread marking for email ${emailNumber}`);
                            }, 500);
                            
                        }, 200);
                    }
                } else {
                    console.log(`Velocitas: No checkbox found for email ${emailNumber}, trying CSS method`);
                    this._markUnreadWithClasses(emailRow);
                }

            } catch (error) {
                console.warn(`Velocitas: Failed to mark email ${emailNumber} as unread:`, error);
                this._markUnreadWithClasses(emailRow);
            }
        }

        // Send keyboard shortcut for marking as unread
        _sendUnreadKeyboardShortcut() {
            // Send both keydown and keyup events for better compatibility
            const keydownEvent = new KeyboardEvent('keydown', {
                key: 'u',
                code: 'KeyU',
                keyCode: 85,
                which: 85,
                shiftKey: true,
                bubbles: true,
                cancelable: true,
                composed: true
            });
            
            const keyupEvent = new KeyboardEvent('keyup', {
                key: 'u',
                code: 'KeyU',
                keyCode: 85,
                which: 85,
                shiftKey: true,
                bubbles: true,
                cancelable: true,
                composed: true
            });
            
            // Dispatch to both document and active element
            document.dispatchEvent(keydownEvent);
            document.dispatchEvent(keyupEvent);
            
            // Also try on the Gmail main container
            const gmailMain = document.querySelector('[role="main"]');
            if (gmailMain) {
                gmailMain.dispatchEvent(keydownEvent);
                gmailMain.dispatchEvent(keyupEvent);
            }
            
            console.log('Velocitas: Sent Shift+U keyboard shortcut');
        }

        // Show syncing overlay for multiple emails
        _showSyncingOverlay(totalEmails) {
            // Remove existing overlay if any
            this._hideSyncingOverlay();

            const overlay = document.createElement('div');
            overlay.id = 'velocitas-syncing-overlay';
            overlay.innerHTML = `
                <div class="velocitas-syncing-container">
                    <div class="velocitas-syncing-spinner"></div>
                    <div class="velocitas-syncing-title">Syncing ${totalEmails} Emails</div>
                    <div class="velocitas-syncing-progress">
                        <div class="velocitas-progress-bar">
                            <div class="velocitas-progress-fill" id="velocitas-progress-fill"></div>
                        </div>
                        <div class="velocitas-progress-text" id="velocitas-progress-text">Initializing...</div>
                    </div>
                    <div class="velocitas-current-email" id="velocitas-current-email">Preparing to extract emails...</div>
                </div>
            `;

            // Add styles
            overlay.style.cssText = `
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                width: 100vw !important;
                height: 100vh !important;
                background: rgba(255, 255, 255, 0.98) !important;
                backdrop-filter: blur(8px) !important;
                z-index: 999999 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
            `;

            // Add container styles
            const containerStyle = `
                <style id="velocitas-syncing-styles">
                .velocitas-syncing-container {
                    text-align: center !important;
                    padding: 50px !important;
                    background: white !important;
                    border-radius: 16px !important;
                    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15) !important;
                    max-width: 500px !important;
                    width: 90% !important;
                    border: 1px solid #e1e5e9 !important;
                }
                
                .velocitas-syncing-spinner {
                    width: 60px !important;
                    height: 60px !important;
                    border: 5px solid #f0f0f0 !important;
                    border-top: 5px solid #FFD700 !important;
                    border-radius: 50% !important;
                    animation: velocitas-sync-spin 1.2s linear infinite !important;
                    margin: 0 auto 25px auto !important;
                }
                
                @keyframes velocitas-sync-spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                
                .velocitas-syncing-title {
                    font-size: 22px !important;
                    font-weight: 700 !important;
                    color: #1a1a1a !important;
                    margin-bottom: 20px !important;
                }
                
                .velocitas-syncing-progress {
                    margin-bottom: 20px !important;
                }
                
                .velocitas-progress-bar {
                    width: 100% !important;
                    height: 8px !important;
                    background: #f0f0f0 !important;
                    border-radius: 4px !important;
                    overflow: hidden !important;
                    margin-bottom: 10px !important;
                }
                
                .velocitas-progress-fill {
                    height: 100% !important;
                    background: linear-gradient(90deg, #FFD700, #FFA500) !important;
                    border-radius: 4px !important;
                    width: 0% !important;
                    transition: width 0.3s ease-in-out !important;
                }
                
                .velocitas-progress-text {
                    font-size: 16px !important;
                    font-weight: 600 !important;
                    color: #333 !important;
                    margin-bottom: 8px !important;
                }
                
                .velocitas-current-email {
                    font-size: 14px !important;
                    color: #666 !important;
                    font-style: italic !important;
                    max-width: 100% !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
                }
                </style>
            `;

            document.head.insertAdjacentHTML('beforeend', containerStyle);
            document.body.appendChild(overlay);

            console.log(`Velocitas: Syncing overlay displayed for ${totalEmails} emails`);
        }

        // Update syncing progress
        _updateSyncingProgress(current, total, emailSubject) {
            const progressFill = document.getElementById('velocitas-progress-fill');
            const progressText = document.getElementById('velocitas-progress-text');
            const currentEmail = document.getElementById('velocitas-current-email');

            if (progressFill && progressText && currentEmail) {
                const percentage = Math.round((current / total) * 100);
                
                progressFill.style.width = `${percentage}%`;
                progressText.textContent = `Processing ${current} of ${total} emails (${percentage}%)`;
                currentEmail.textContent = `Currently extracting: ${emailSubject || 'Unknown Subject'}`;
                
                console.log(`Velocitas: Progress updated - ${current}/${total} (${percentage}%)`);
            }
        }

        // Hide syncing overlay
        _hideSyncingOverlay() {
            const overlay = document.getElementById('velocitas-syncing-overlay');
            const styles = document.getElementById('velocitas-syncing-styles');
            
            if (overlay) {
                overlay.remove();
                console.log('Velocitas: Syncing overlay hidden');
            }
            if (styles) {
                styles.remove();
            }
        }

        // Helper to find element using multiple selectors
        _findElement(selectors, container = document) {
            for (const selector of selectors) {
                const element = container.querySelector(selector);
                if (element) {
                    return element;
                }
            }
            return null;
        }

        // Helper to extract text from element using multiple selectors
        _extractTextFromElement(container, selectors) {
            const element = this._findElement(selectors, container);
            if (!element) return '';

            // Get the most appropriate text content
            let text = element.getAttribute('email') || 
                      element.getAttribute('title') || 
                      element.innerText || 
                      element.textContent || 
                      '';

            return text.trim();
        }

        // Public method to manually trigger multiple email extraction
        manualExtractMultiple(count = 10) {
            console.log(`Velocitas: Manual multiple extraction triggered for ${count} emails`);
            return this.extractMultipleEmails(count);
        }
    }

    // Main Extension Controller
    class VelocitasExtension {
        constructor() {
            this.headerManager = new DateHeaderManager();
            this.emailExtractor = new EmailExtractor();
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
            
            // Add any additional features here
            // Example: this._startEmailGrouping();
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

        // Print email data to console in a formatted way
        _printEmailToConsole(emailData) {
            console.log('\n' + '='.repeat(60));
            console.log('📧 VELOCITAS - FIRST EMAIL EXTRACTED');
            console.log('='.repeat(60));
            
            if (emailData.type === 'list_view') {
                console.log(`📤 From: ${emailData.sender || 'Unknown Sender'}`);
                console.log(`📝 Subject: ${emailData.subject || '(No Subject)'}`);
                console.log(`📅 Date: ${emailData.date || 'Unknown Date'}`);
                console.log(`👁️  Read Status: ${emailData.isRead ? 'Read' : 'Unread'}`);
                console.log(`⭐ Starred: ${emailData.isStarred ? 'Yes' : 'No'}`);
                
                if (emailData.snippet) {
                    console.log(`📄 Preview: ${emailData.snippet}`);
                }
                
                console.log('\n🔄 Attempting to get full email content...');
                
            } else if (emailData.type === 'conversation_view') {
                console.log(`📤 From: ${emailData.sender || 'Unknown Sender'}`);
                console.log(`📝 Subject: ${emailData.subject || '(No Subject)'}`);
                console.log(`📅 Date: ${emailData.date || 'Unknown Date'}`);
                
                if (emailData.body) {
                    console.log('\n📄 FULL EMAIL CONTENT:');
                    console.log('-'.repeat(40));
                    console.log(emailData.body);
                    console.log('-'.repeat(40));
                }
            }
            
            console.log('='.repeat(60) + '\n');
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