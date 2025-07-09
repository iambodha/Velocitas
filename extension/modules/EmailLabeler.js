// EmailLabeler.js - AI-powered email categorization using Hack Club API
window.EmailLabeler = class EmailLabeler {
    constructor() {
        this.apiUrl = 'https://ai.hackclub.com/chat/completions';
        this.categories = [
            'Important',
            'Personal',
            'Promotions',
            'Updates',
            'Spam'
        ];
        
        // Icon mapping for each category
        this.categoryIcons = {
            'Important': '❗',
            'Personal': '👤',
            'Promotions': '🛒',
            'Updates': '📰',
            'Spam': '🗑️'
        };
        
        // Color mapping for each category
        this.categoryColors = {
            'Important': 'rgb(255, 107, 107)',
            'Personal': 'rgb(107, 171, 255)',
            'Promotions': 'rgb(255, 204, 107)',
            'Updates': 'rgb(107, 255, 171)',
            'Spam': 'rgb(171, 107, 255)'
        };
        
        this.processingQueue = [];
        this.isProcessing = false;
        this.isContinuousMode = false; // New flag for continuous labeling
        this.onLabelCallback = null; // Callback for when individual emails are labeled
        
        // Cache settings
        this.cachePrefix = 'velocitas_email_';
        this.cacheExpiration = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
        this.cache = new Map();
        
        // Load cache on initialization
        this._loadCache();
    }

    // Generate a unique identifier for an email
    _generateEmailId(emailData) {
        // Create a hash-like identifier from email content
        const content = `${emailData.title}_${emailData.sender}_${emailData.date}`;
        return btoa(content).replace(/[^a-zA-Z0-9]/g, '').substring(0, 32);
    }

    // Load cache from cookies
    _loadCache() {
        try {
            const cookies = document.cookie.split(';');
            let cacheCount = 0;
            
            cookies.forEach(cookie => {
                const [name, value] = cookie.trim().split('=');
                if (name && name.startsWith(this.cachePrefix)) {
                    try {
                        const decodedValue = decodeURIComponent(value);
                        const cacheData = JSON.parse(decodedValue);
                        
                        // Check if cache is still valid
                        if (Date.now() - cacheData.timestamp < this.cacheExpiration) {
                            const emailId = name.replace(this.cachePrefix, '');
                            this.cache.set(emailId, cacheData);
                            cacheCount++;
                        } else {
                            // Remove expired cache
                            this._deleteCookie(name);
                        }
                    } catch (error) {
                        console.warn('EmailLabeler: Error parsing cache entry:', error);
                        this._deleteCookie(name);
                    }
                }
            });
            
            console.log(`EmailLabeler: Loaded ${cacheCount} cached categorizations`);
        } catch (error) {
            console.warn('EmailLabeler: Error loading cache:', error);
        }
    }

    // Save categorization to cache
    _saveToCache(emailId, emailData) {
        try {
            const cacheData = {
                category: emailData.category,
                icon: emailData.icon,
                color: emailData.color,
                timestamp: Date.now()
            };
            
            this.cache.set(emailId, cacheData);
            
            // Save to cookie
            const cookieName = this.cachePrefix + emailId;
            const cookieValue = encodeURIComponent(JSON.stringify(cacheData));
            const expirationDate = new Date(Date.now() + this.cacheExpiration);
            
            document.cookie = `${cookieName}=${cookieValue}; expires=${expirationDate.toUTCString()}; path=/; SameSite=Strict`;
            
            console.log(`EmailLabeler: Cached categorization for email ${emailId}`);
        } catch (error) {
            console.warn('EmailLabeler: Error saving to cache:', error);
        }
    }

    // Get categorization from cache
    _getFromCache(emailId) {
        const cacheData = this.cache.get(emailId);
        if (cacheData) {
            // Check if still valid
            if (Date.now() - cacheData.timestamp < this.cacheExpiration) {
                return cacheData;
            } else {
                // Remove expired cache
                this.cache.delete(emailId);
                this._deleteCookie(this.cachePrefix + emailId);
            }
        }
        return null;
    }

    // Delete a cookie
    _deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }

    // Clear all cached categorizations
    clearCache() {
        try {
            // Clear memory cache
            this.cache.clear();
            
            // Clear cookies
            const cookies = document.cookie.split(';');
            let deletedCount = 0;
            
            cookies.forEach(cookie => {
                const [name] = cookie.trim().split('=');
                if (name && name.startsWith(this.cachePrefix)) {
                    this._deleteCookie(name);
                    deletedCount++;
                }
            });
            
            console.log(`EmailLabeler: Cleared ${deletedCount} cached categorizations`);
        } catch (error) {
            console.warn('EmailLabeler: Error clearing cache:', error);
        }
    }

    // Main method to label an email (now with caching)
    async labelEmail(emailData) {
        if (!emailData || !emailData.title) {
            console.warn('EmailLabeler: Invalid email data provided');
            return null;
        }

        try {
            const emailId = this._generateEmailId(emailData);
            
            // Check cache first
            const cachedResult = this._getFromCache(emailId);
            if (cachedResult) {
                console.log(`EmailLabeler: Using cached result for email "${emailData.title}"`);
                return {
                    ...emailData,
                    category: cachedResult.category,
                    icon: cachedResult.icon,
                    color: cachedResult.color,
                    labeledAt: new Date(cachedResult.timestamp).toISOString(),
                    fromCache: true
                };
            }

            console.log(`EmailLabeler: Labeling email "${emailData.title}" with AI`);
            
            const prompt = this._buildPrompt(emailData);
            const response = await this._callAI(prompt);
            const category = this._parseResponse(response);
            
            const result = {
                ...emailData,
                category: category,
                icon: this.categoryIcons[category] || '📄',
                color: this.categoryColors[category] || '#795548',
                labeledAt: new Date().toISOString(),
                fromCache: false
            };
            
            // Save to cache
            this._saveToCache(emailId, result);
            
            console.log(`EmailLabeler: Email "${emailData.title}" labeled as "${category}"`);
            return result;
            
        } catch (error) {
            console.error('EmailLabeler: Error labeling email:', error);
            return {
                ...emailData,
                category: 'Other',
                icon: this.categoryIcons['Other'],
                color: this.categoryColors['Other'],
                labeledAt: new Date().toISOString(),
                error: error.message,
                fromCache: false
            };
        }
    }

    // New method for continuous labeling mode
    async processEmailQueueContinuous(emails, onLabelCallback) {
        if (this.isProcessing) {
            console.log('EmailLabeler: Already processing queue, skipping...');
            return;
        }

        this.isProcessing = true;
        this.isContinuousMode = true;
        this.onLabelCallback = onLabelCallback;
        
        console.log(`EmailLabeler: Starting continuous labeling of ${emails.length} emails`);
        
        // Process all emails without limit
        this.processingQueue = [...emails];
        const results = [];

        // Separate cached and uncached emails
        const cachedEmails = [];
        const uncachedEmails = [];
        
        for (const email of emails) {
            const emailId = this._generateEmailId(email);
            const cachedResult = this._getFromCache(emailId);
            
            if (cachedResult) {
                const labeledEmail = {
                    ...email,
                    category: cachedResult.category,
                    icon: cachedResult.icon,
                    color: cachedResult.color,
                    labeledAt: new Date(cachedResult.timestamp).toISOString(),
                    fromCache: true
                };
                cachedEmails.push(labeledEmail);
            } else {
                uncachedEmails.push(email);
            }
        }

        console.log(`EmailLabeler: Found ${cachedEmails.length} cached and ${uncachedEmails.length} uncached emails`);
        
        // Immediately add cached results
        for (const cachedEmail of cachedEmails) {
            results.push(cachedEmail);
            if (this.onLabelCallback) {
                this.onLabelCallback(cachedEmail);
            }
        }
        
        // Process uncached emails individually
        for (let i = 0; i < uncachedEmails.length; i++) {
            const email = uncachedEmails[i];
            console.log(`EmailLabeler: Processing email ${i + 1}/${uncachedEmails.length}: "${email.title}"`);
            
            try {
                const labeledEmail = await this.labelEmail(email);
                results.push(labeledEmail);
                
                // Immediately add label to Gmail interface
                if (this.onLabelCallback) {
                    this.onLabelCallback(labeledEmail);
                }
                
                // Add small delay to avoid overwhelming the API
                if (i < uncachedEmails.length - 1) {
                    await this._delay(300);
                }
                
            } catch (error) {
                console.error(`EmailLabeler: Failed to process email ${i + 1}:`, error);
                const errorEmail = {
                    ...email,
                    category: 'Other',
                    icon: this.categoryIcons['Other'],
                    color: this.categoryColors['Other'],
                    error: error.message,
                    fromCache: false
                };
                results.push(errorEmail);
                
                // Still add error label to interface
                if (this.onLabelCallback) {
                    this.onLabelCallback(errorEmail);
                }
            }
        }

        this.isProcessing = false;
        this.isContinuousMode = false;
        this.onLabelCallback = null;
        this.processingQueue = [];
        
        console.log('EmailLabeler: Continuous labeling complete');
        this._logResults(results);
        
        return results;
    }

    // Process multiple emails in queue (now with bulk processing and async optimization)
    async processEmailQueue(emails) {
        if (this.isProcessing) {
            console.log('EmailLabeler: Already processing queue, skipping...');
            return;
        }

        this.isProcessing = true;
        
        // Process all emails without limit
        this.processingQueue = [...emails];
        const results = [];

        // Separate cached and uncached emails
        const cachedEmails = [];
        const uncachedEmails = [];
        
        for (const email of emails) {
            const emailId = this._generateEmailId(email);
            const cachedResult = this._getFromCache(emailId);
            
            if (cachedResult) {
                cachedEmails.push({
                    ...email,
                    category: cachedResult.category,
                    icon: cachedResult.icon,
                    color: cachedResult.color,
                    labeledAt: new Date(cachedResult.timestamp).toISOString(),
                    fromCache: true
                });
            } else {
                uncachedEmails.push(email);
            }
        }

        console.log(`EmailLabeler: Found ${cachedEmails.length} cached and ${uncachedEmails.length} uncached emails`);
        
        // Add cached results
        results.push(...cachedEmails);
        
        // Process uncached emails in bulk
        if (uncachedEmails.length > 0) {
            console.log(`EmailLabeler: Processing ${uncachedEmails.length} uncached emails with bulk AI processing...`);
            
            try {
                const bulkResults = await this._processBulkEmails(uncachedEmails);
                results.push(...bulkResults);
            } catch (error) {
                console.error('EmailLabeler: Bulk processing failed, falling back to individual processing:', error);
                
                // Fallback to individual processing
                for (let i = 0; i < uncachedEmails.length; i++) {
                    const email = uncachedEmails[i];
                    console.log(`EmailLabeler: Processing email ${i + 1}/${uncachedEmails.length}: "${email.title}"`);
                    
                    try {
                        const labeledEmail = await this.labelEmail(email);
                        results.push(labeledEmail);
                        
                        // Add small delay to avoid overwhelming the API
                        if (i < uncachedEmails.length - 1) {
                            await this._delay(300);
                        }
                        
                    } catch (error) {
                        console.error(`EmailLabeler: Failed to process email ${i + 1}:`, error);
                        results.push({
                            ...email,
                            category: 'Other',
                            icon: this.categoryIcons['Other'],
                            color: this.categoryColors['Other'],
                            error: error.message,
                            fromCache: false
                        });
                    }
                }
            }
        }

        this.isProcessing = false;
        this.processingQueue = [];
        
        console.log('EmailLabeler: Queue processing complete');
        this._logResults(results);
        
        return results;
    }

    // New method to add a single labeled email to Gmail interface immediately
    addSingleLabelToGmail(labeledEmail) {
        if (!labeledEmail) {
            console.warn('EmailLabeler: No labeled email provided');
            return;
        }

        console.log(`EmailLabeler: Adding single label for "${labeledEmail.title}"`);
        
        // Get current email rows
        const emailRows = document.querySelectorAll('tr[class*="zA"]');
        
        // Find the corresponding row
        const row = emailRows[labeledEmail.rowIndex];
        
        if (row) {
            this._addLabelToEmailRow(row, labeledEmail);
            console.log(`EmailLabeler: Added label for "${labeledEmail.title}"`);
        } else {
            console.warn(`EmailLabeler: Could not find row for email "${labeledEmail.title}"`);
        }
    }

    // New method for bulk email processing
    async _processBulkEmails(emails) {
        console.log(`EmailLabeler: Starting bulk processing of ${emails.length} emails...`);
        
        const results = [];
        const batchSize = 5; // Process 5 emails at a time to avoid overwhelming the API
        
        // Process emails in batches
        for (let i = 0; i < emails.length; i += batchSize) {
            const batch = emails.slice(i, i + batchSize);
            console.log(`EmailLabeler: Processing batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(emails.length / batchSize)} (${batch.length} emails)`);
            
            try {
                const batchResults = await this._processBatch(batch);
                results.push(...batchResults);
                
                // Add delay between batches
                if (i + batchSize < emails.length) {
                    await this._delay(500);
                }
            } catch (error) {
                console.error(`EmailLabeler: Batch processing failed for batch ${Math.floor(i / batchSize) + 1}:`, error);
                
                // Fallback to individual processing for this batch
                for (const email of batch) {
                    try {
                        const labeledEmail = await this.labelEmail(email);
                        results.push(labeledEmail);
                    } catch (individualError) {
                        console.error(`EmailLabeler: Individual fallback failed for email "${email.title}":`, individualError);
                        results.push({
                            ...email,
                            category: 'Other',
                            icon: this.categoryIcons['Other'],
                            color: this.categoryColors['Other'],
                            error: individualError.message,
                            fromCache: false
                        });
                    }
                }
            }
        }
        
        console.log(`EmailLabeler: Bulk processing complete. Processed ${results.length} emails.`);
        return results;
    }

    // Process a batch of emails with a single API call
    async _processBatch(emails) {
        const prompt = this._buildBulkPrompt(emails);
        const response = await this._callAI(prompt);
        const categories = this._parseBulkResponse(response, emails.length);
        
        const results = [];
        
        for (let i = 0; i < emails.length; i++) {
            const email = emails[i];
            const category = categories[i] || 'Other';
            
            const result = {
                ...email,
                category: category,
                icon: this.categoryIcons[category] || '📄',
                color: this.categoryColors[category] || '#795548',
                labeledAt: new Date().toISOString(),
                fromCache: false
            };
            
            // Save to cache
            const emailId = this._generateEmailId(email);
            this._saveToCache(emailId, result);
            
            results.push(result);
            console.log(`EmailLabeler: Email "${email.title}" labeled as "${category}" (bulk)`);
        }
        
        return results;
    }

    // Build bulk AI prompt for multiple emails
    _buildBulkPrompt(emails) {
        const categoriesList = this.categories.join(', ');
        
        let prompt = `You are an email categorization assistant. Please categorize the following emails into ONE of these categories for each email: ${categoriesList}

Categories explained:
- Important: Emails that are marked as important by the user or the system
- Personal: Personal messages from friends, family, or personal contacts
- Promotions: Sales emails, promotional offers, marketing campaigns
- Updates: Notifications about updates, changes, or new features
- Spam: Unwanted emails, suspicious content, obvious spam

EMAILS TO CATEGORIZE:
`;

        emails.forEach((email, index) => {
            prompt += `
EMAIL ${index + 1}:
- Subject: "${email.title}"
- Sender: "${email.sender}"
- Snippet: "${email.snippet}"
- Date: "${email.date}"
`;
        });

        prompt += `

INSTRUCTIONS:
1. Analyze each email carefully
2. Choose the MOST appropriate category from the list above for each email
3. Respond with ONLY the category names, one per line, in the same order as the emails
4. If unsure about any email, choose "Other"
5. Your response should have exactly ${emails.length} lines, each containing only a category name

RESPONSE FORMAT:
[Category for Email 1]
[Category for Email 2]
[Category for Email 3]
...

Categories:`;

        return prompt;
    }

    // Parse bulk AI response to extract categories
    _parseBulkResponse(response, expectedCount) {
        const lines = response.trim().split('\n').filter(line => line.trim());
        const categories = [];
        
        for (let i = 0; i < expectedCount; i++) {
            let category = 'Other';
            
            if (i < lines.length) {
                const line = lines[i].trim();
                
                // Check if line matches any of our categories (case-insensitive)
                const matchedCategory = this.categories.find(cat => 
                    line.toLowerCase().includes(cat.toLowerCase()) ||
                    cat.toLowerCase().includes(line.toLowerCase())
                );
                
                if (matchedCategory) {
                    category = matchedCategory;
                } else {
                    // Try to extract category from the line
                    const words = line.split(/\s+/);
                    for (const word of words) {
                        const matchedWord = this.categories.find(cat => 
                            cat.toLowerCase().includes(word.toLowerCase()) || 
                            word.toLowerCase().includes(cat.toLowerCase())
                        );
                        if (matchedWord) {
                            category = matchedWord;
                            break;
                        }
                    }
                }
            }
            
            categories.push(category);
        }
        
        console.log(`EmailLabeler: Parsed ${categories.length} categories from bulk response`);
        return categories;
    }

    // Build AI prompt for individual email
    _buildPrompt(emailData) {
        const categoriesList = this.categories.join(', ');
        
        return `You are an email categorization assistant. Please categorize the following email into ONE of these categories: ${categoriesList}

Categories explained:
- Important: Emails that are marked as important by the user or the system
- Personal: Personal messages from friends, family, or personal contacts
- Promotions: Sales emails, promotional offers, marketing campaigns
- Updates: Notifications about updates, changes, or new features
- Spam: Unwanted emails, suspicious content, obvious spam

EMAIL TO CATEGORIZE:
- Subject: "${emailData.title}"
- Sender: "${emailData.sender}"
- Snippet: "${emailData.snippet}"
- Date: "${emailData.date}"

Please respond with ONLY the category name from the list above. If you're unsure, respond with "Other".

Category:`;
    }

    // Call AI API
    async _callAI(prompt) {
        const response = await fetch(this.apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                model: 'gpt-3.5-turbo',
                messages: [
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                max_tokens: 150,
                temperature: 0.1
            })
        });

        if (!response.ok) {
            throw new Error(`AI API request failed: ${response.status} ${response.statusText}`);
        }

        const data = await response.json();
        
        if (!data.choices || !data.choices[0] || !data.choices[0].message) {
            throw new Error('Invalid AI API response format');
        }

        return data.choices[0].message.content.trim();
    }

    // Parse AI response to extract category
    _parseResponse(response) {
        const cleanResponse = response.trim();
        
        // Check if response matches any of our categories (case-insensitive)
        const matchedCategory = this.categories.find(category => 
            cleanResponse.toLowerCase().includes(category.toLowerCase()) ||
            category.toLowerCase().includes(cleanResponse.toLowerCase())
        );
        
        if (matchedCategory) {
            return matchedCategory;
        }
        
        // Try to extract category from the response
        const words = cleanResponse.split(/\s+/);
        for (const word of words) {
            const matchedWord = this.categories.find(category => 
                category.toLowerCase().includes(word.toLowerCase()) || 
                word.toLowerCase().includes(category.toLowerCase())
            );
            if (matchedWord) {
                return matchedWord;
            }
        }
        
        // Default to 'Other' if no match found
        console.warn(`EmailLabeler: Could not parse category from response: "${cleanResponse}"`);
        return 'Other';
    }

    // Add visual labels to Gmail interface
    addVisualLabelsToGmail(labeledEmails) {
        if (!labeledEmails || labeledEmails.length === 0) {
            console.warn('EmailLabeler: No labeled emails to add to Gmail interface');
            return;
        }

        console.log(`EmailLabeler: Adding ${labeledEmails.length} visual labels to Gmail interface`);
        
        // Get current email rows
        const emailRows = document.querySelectorAll('tr[class*="zA"]');
        
        labeledEmails.forEach((emailData, index) => {
            try {
                // Find the corresponding row (by index for now)
                const row = emailRows[emailData.rowIndex] || emailRows[index];
                
                if (row) {
                    this._addLabelToEmailRow(row, emailData);
                } else {
                    console.warn(`EmailLabeler: Could not find row for email "${emailData.title}"`);
                }
            } catch (error) {
                console.error(`EmailLabeler: Error adding label for email "${emailData.title}":`, error);
            }
        });
        
        console.log('EmailLabeler: Visual labels added to Gmail interface');
    }

    // Add a visual label to a specific email row
    _addLabelToEmailRow(row, emailData) {
        try {
            // Remove any existing Velocitas labels
            const existingLabel = row.querySelector('.velocitas-email-label');
            if (existingLabel) {
                existingLabel.remove();
            }

            // Remove any existing highlight texts from document body
            const existingHighlights = document.querySelectorAll('.velocitas-highlight-text');
            existingHighlights.forEach(highlight => {
                if (highlight.dataset.velocitasRow === row.dataset.velocitasId) {
                    highlight.remove();
                }
            });

            // Create unique identifier for this row
            const rowId = 'velocitas-row-' + Math.random().toString(36).substr(2, 9);
            row.dataset.velocitasId = rowId;

            // Create colored highlight strip
            const highlightStrip = document.createElement('div');
            highlightStrip.className = 'velocitas-email-label';
            highlightStrip.setAttribute('data-category', emailData.category);
            
            // Style the highlight strip - always visible
            highlightStrip.style.cssText = `
                position: absolute;
                left: 0;
                top: 0;
                width: 5px;
                height: 100%;
                background-color: ${this._getCleanTextColor(emailData.color)};
                border-radius: 0 2px 2px 0;
                opacity: 0.8;
                transition: width 0.2s ease, opacity 0.2s ease;
                z-index: 1;
                cursor: pointer;
            `;

            // Make sure the row has relative positioning
            row.style.position = 'relative';

            // Clear any existing Velocitas event handlers
            this._clearRowEventHandlers(row);

            // Create minimal highlight text element (attached to document body)
            const highlightText = document.createElement('div');
            highlightText.className = 'velocitas-highlight-text';
            highlightText.dataset.velocitasRow = rowId;
            highlightText.textContent = emailData.category;
            
            // Minimal highlight text styling - small and clean
            highlightText.style.cssText = `
                position: fixed;
                background: ${this._getCleanTextColor(emailData.color)};
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                white-space: nowrap;
                z-index: 2147483647;
                pointer-events: none;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.2s ease, visibility 0.2s ease;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.2;
            `;

            // Add highlight text to document body
            document.body.appendChild(highlightText);

            // Create event handlers - only for the highlight strip
            const showHighlight = (event) => {
                // Get strip position
                const stripRect = highlightStrip.getBoundingClientRect();
                const scrollY = window.scrollY || window.pageYOffset;
                const scrollX = window.scrollX || window.pageXOffset;
                
                // Position highlight text to the right of the strip
                const highlightX = stripRect.right + scrollX + 8;
                const highlightY = stripRect.top + scrollY + (stripRect.height / 2) - 10;
                
                // Ensure highlight stays within viewport
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                
                let adjustedX = highlightX;
                let adjustedY = highlightY;
                
                // If too far right, position it to the left of the strip
                if (highlightX + 100 > viewportWidth) {
                    adjustedX = stripRect.left + scrollX - 100;
                }
                
                // If too far left, position it inside the viewport
                if (adjustedX < 5) {
                    adjustedX = 5;
                }
                
                // Vertical adjustment
                if (highlightY < 5) {
                    adjustedY = 5;
                } else if (highlightY + 25 > viewportHeight) {
                    adjustedY = viewportHeight - 30;
                }
                
                highlightText.style.left = `${adjustedX}px`;
                highlightText.style.top = `${adjustedY}px`;
                
                // Show highlight text
                highlightText.style.opacity = '1';
                highlightText.style.visibility = 'visible';
                
                // Enhance highlight strip on hover
                highlightStrip.style.width = '7px';
                highlightStrip.style.opacity = '1';
            };

            const hideHighlight = () => {
                // Hide highlight text
                highlightText.style.opacity = '0';
                highlightText.style.visibility = 'hidden';
                
                // Reset highlight strip
                highlightStrip.style.width = '5px';
                highlightStrip.style.opacity = '0.8';
            };

            // Event handling with debouncing - only on the strip itself
            let showTimeout, hideTimeout;
            
            const debouncedShow = (event) => {
                clearTimeout(hideTimeout);
                showTimeout = setTimeout(() => showHighlight(event), 100);
            };
            
            const debouncedHide = () => {
                clearTimeout(showTimeout);
                hideTimeout = setTimeout(hideHighlight, 50);
            };

            // Store handlers for cleanup
            highlightStrip._velocitasShowHandler = debouncedShow;
            highlightStrip._velocitasHideHandler = debouncedHide;
            row._velocitasHighlightText = highlightText;

            // Add event listeners only to the highlight strip
            highlightStrip.addEventListener('mouseenter', debouncedShow, { 
                capture: true, 
                passive: true 
            });
            
            highlightStrip.addEventListener('mouseleave', debouncedHide, { 
                capture: true, 
                passive: true 
            });

            // Insert highlight strip
            row.insertBefore(highlightStrip, row.firstChild);
            
            // Mark row as processed
            row.setAttribute('data-velocitas-labeled', emailData.category);
            
            console.log(`EmailLabeler: Added minimal highlight text system for "${emailData.category}" to email row`);
            
        } catch (error) {
            console.error('EmailLabeler: Error adding visual label:', error);
            
            // Fallback: add a subtle border-left to the row
            try {
                row.style.borderLeft = `3px solid ${this._getCleanTextColor(emailData.color)}`;
                row.style.borderLeftOpacity = '0.6';
                console.log(`EmailLabeler: Added fallback border highlight to email row`);
            } catch (fallbackError) {
                console.error('EmailLabeler: Fallback labeling also failed:', fallbackError);
            }
        }
    }

    // Helper method to clear existing event handlers
    _clearRowEventHandlers(row) {
        // Find and clean up highlight strip handlers
        const existingStrip = row.querySelector('.velocitas-email-label');
        if (existingStrip) {
            if (existingStrip._velocitasShowHandler) {
                existingStrip.removeEventListener('mouseenter', existingStrip._velocitasShowHandler, { capture: true });
            }
            if (existingStrip._velocitasHideHandler) {
                existingStrip.removeEventListener('mouseleave', existingStrip._velocitasHideHandler, { capture: true });
            }
        }

        // Remove highlight text from document body
        if (row._velocitasHighlightText) {
            try {
                document.body.removeChild(row._velocitasHighlightText);
            } catch (e) {
                // Highlight text might already be removed
            }
            row._velocitasHighlightText = null;
        }

        // Clear timeout if exists
        if (row._velocitasHighlightTimeout) {
            clearTimeout(row._velocitasHighlightTimeout);
            row._velocitasHighlightTimeout = null;
        }
    }

    // Helper method to get a darker version of a color
    _getDarkerColor(color) {
        const colorMap = {
            'rgb(255, 107, 107)': '#b71c1c', // Important - darker red
            'rgb(107, 171, 255)': '#0d47a1', // Personal - darker blue
            'rgb(255, 204, 107)': '#e65100', // Promotions - darker orange
            'rgb(107, 255, 171)': '#1b5e20', // Updates - darker green
            'rgb(171, 107, 255)': '#4a148c'  // Spam - darker purple
        };
        return colorMap[color] || '#212121';
    }

    // Helper method to get clean text color
    _getCleanTextColor(color) {
        const colorMap = {
            'rgb(255, 107, 107)': '#c62828', // Important - dark red
            'rgb(107, 171, 255)': '#1565c0', // Personal - dark blue
            'rgb(255, 204, 107)': '#f57c00', // Promotions - dark orange
            'rgb(107, 255, 171)': '#2e7d32', // Updates - dark green
            'rgb(171, 107, 255)': '#6a1b9a'  // Spam - dark purple
        };
        return colorMap[color] || '#424242';
    }

    // Utility method for delays
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Log categorization results
    _logResults(results) {
        console.log('EmailLabeler: Categorization Results');
        console.log('=====================================');
        
        // Count by category
        const categoryCount = {};
        results.forEach(email => {
            const category = email.category || 'Other';
            categoryCount[category] = (categoryCount[category] || 0) + 1;
        });

        console.log('Category Distribution:');
        Object.entries(categoryCount).forEach(([category, count]) => {
            const icon = this.categoryIcons[category] || '📄';
            console.log(`  ${icon} ${category}: ${count} emails`);
        });
        
        console.log('=====================================');
        
        // Log individual results with icons
        results.forEach((email, index) => {
            const icon = email.icon || '📄';
            console.log(`${index + 1}. ${icon} [${email.category}] ${email.title}`);
            if (email.error) {
                console.log(`   Error: ${email.error}`);
            }
        });
        
        console.log('=====================================');
    }

    // Get available categories with icons
    getCategories() {
        return this.categories.map(category => ({
            name: category,
            icon: this.categoryIcons[category],
            color: this.categoryColors[category]
        }));
    }

    // Get processing status
    getStatus() {
        return {
            isProcessing: this.isProcessing,
            queueLength: this.processingQueue.length,
            categories: this.getCategories()
        };
    }
}