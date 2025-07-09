// EmailSummarizer.js - AI-powered email summarization module
window.EmailSummarizer = class EmailSummarizer {
    constructor() {
        this.cache = new Map();
        this.processingQueue = [];
        this.isProcessing = false;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.summaryButton = null;
        this.apiUrl = 'https://ai.hackclub.com/chat/completions';
    }

    // Initialize the summarizer
    async init() {
        console.log('EmailSummarizer: Initializing with Hack Club AI API');
        
        // Inject the summary button into Gmail UI
        this.injectSummaryButton();
    }

    // Inject summary button into Gmail UI
    injectSummaryButton() {
        // Wait for Gmail to load
        const checkGmailLoaded = () => {
            // Look for the top bar area where we want to inject the button
            const topBar = document.querySelector('.gb_Dd.gb_1d.gb_yd.gb_Ld') || 
                          document.querySelector('.gb_md.gb_qd.gb_Id') ||
                          document.querySelector('[data-ogsr-up]');
            
            if (!topBar) {
                setTimeout(checkGmailLoaded, 1000);
                return;
            }

            // Check if button already exists
            if (document.getElementById('velocitas-summary-btn')) {
                return;
            }

            // Create the summary button with Gmail-like structure
            const summaryButton = document.createElement('div');
            summaryButton.id = 'velocitas-summary-btn';
            summaryButton.className = 'gb_z gb_dd gb_Pf gb_0'; // Use Gmail's account section classes
            summaryButton.innerHTML = `
                <div class="gb_D gb_jb gb_Pf gb_0">
                    <button class="velocitas-summary-btn-icon" 
                            aria-label="Summarize Unread Emails"
                            data-tooltip-enabled="true"
                            data-tooltip-id="velocitas-summary-tooltip">
                        <span class="velocitas-btn-bg"></span>
                        <span class="velocitas-btn-ripple"></span>
                        <span class="velocitas-btn-icon-wrapper">
                            <svg focusable="false" viewBox="0 0 24 24" height="24" width="24" class="velocitas-summary-icon">
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                                <path d="M12 6l1.5 3L17 9.5l-2.5 2.4L15 15l-3-1.6L9 15l.5-3.1L7 9.5l3.5-.5L12 6z" opacity="0.7"/>
                                <circle cx="12" cy="12" r="1" opacity="0.5"/>
                            </svg>
                        </span>
                        <div class="velocitas-tooltip" role="tooltip" aria-hidden="true" id="velocitas-summary-tooltip">
                            Summarize Unread Emails
                        </div>
                    </button>
                </div>
            `;

            // Add styles for the button
            this.addButtonStyles();

            // Find the account section and insert the button right before it
            const accountSection = topBar.querySelector('.gb_z.gb_dd.gb_Pf.gb_0:last-child');
            if (accountSection) {
                // Insert the button as a sibling right before the account section
                accountSection.parentNode.insertBefore(summaryButton, accountSection);
                console.log('EmailSummarizer: Button inserted before account section');
            } else {
                // Fallback: look for any account-related section
                const fallbackAccountSection = topBar.querySelector('.gb_z.gb_dd.gb_Pf.gb_0') ||
                                               topBar.querySelector('[aria-label*="Account"]') ||
                                               topBar.querySelector('[aria-label*="Google Account"]');
                
                if (fallbackAccountSection) {
                    fallbackAccountSection.parentNode.insertBefore(summaryButton, fallbackAccountSection);
                    console.log('EmailSummarizer: Button inserted before fallback account section');
                } else {
                    // Last resort: append to the top bar
                    topBar.appendChild(summaryButton);
                    console.log('EmailSummarizer: Button appended to top bar (fallback)');
                }
            }

            // Add click event listener
            const button = summaryButton.querySelector('.velocitas-summary-btn-icon');
            if (button) {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleSummaryButtonClick();
                });
                
                this.summaryButton = button;
                console.log('EmailSummarizer: Summary button injected into Gmail UI');
            }
        };

        // Start checking for Gmail to load
        checkGmailLoaded();
    }

    // Add styles for the summary button
    addButtonStyles() {
        if (document.getElementById('velocitas-summary-btn-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'velocitas-summary-btn-styles';
        styles.textContent = `
            .velocitas-summary-wrapper {
                display: flex;
                align-items: center;
                margin-right: 8px;
            }
            
            .velocitas-summary-inner {
                display: flex;
                align-items: center;
                position: relative;
            }
            
            .velocitas-summary-spacer {
                width: 4px;
                height: 1px;
            }
            
            .velocitas-summary-btn-icon {
                position: relative !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                border: none !important;
                background: transparent !important;
                cursor: pointer !important;
                outline: none !important;
                transition: all 0.2s ease !important;
                overflow: hidden !important;
            }
            
            .velocitas-btn-bg {
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                background: #FFF9C4 !important;
                border-radius: 50% !important;
                opacity: 0 !important;
                transition: opacity 0.2s ease !important;
            }
            
            .velocitas-summary-btn-icon:hover .velocitas-btn-bg {
                opacity: 1 !important;
            }
            
            .velocitas-btn-ripple {
                position: absolute !important;
                top: 0 !important;
                left: 0 !important;
                width: 100% !important;
                height: 100% !important;
                border-radius: 50% !important;
                pointer-events: none !important;
            }
            
            .velocitas-btn-icon-wrapper {
                position: relative !important;
                z-index: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            
            .velocitas-summary-icon {
                fill: #5f6368 !important;
                transition: fill 0.2s ease !important;
            }
            
            .velocitas-summary-btn-icon:hover .velocitas-summary-icon {
                fill: #333333 !important;
            }
            
            .velocitas-summary-btn-icon.processing .velocitas-summary-icon {
                fill: #9aa0a6 !important;
                animation: velocitas-sparkle 2s ease-in-out infinite !important;
            }
            
            @keyframes velocitas-sparkle {
                0%, 100% {
                    transform: scale(1) rotate(0deg);
                    opacity: 1;
                }
                50% {
                    transform: scale(1.1) rotate(180deg);
                    opacity: 0.8;
                }
            }
            
            .velocitas-tooltip {
                position: absolute !important;
                top: 50px !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                background: rgba(0, 0, 0, 0.8) !important;
                color: white !important;
                padding: 8px 12px !important;
                border-radius: 4px !important;
                font-size: 12px !important;
                font-family: system-ui, sans-serif !important;
                white-space: nowrap !important;
                z-index: 10001 !important;
                opacity: 0 !important;
                pointer-events: none !important;
                transition: opacity 0.2s ease !important;
            }
            
            .velocitas-summary-btn-icon:hover + .velocitas-tooltip,
            .velocitas-summary-btn-icon:focus + .velocitas-tooltip {
                opacity: 1 !important;
            }
            
            /* Add a subtle pulse effect when processing */
            .velocitas-summary-btn-icon.processing .velocitas-btn-bg {
                opacity: 0.3 !important;
                animation: velocitas-pulse 1.5s ease-in-out infinite !important;
            }
            
            @keyframes velocitas-pulse {
                0%, 100% {
                    opacity: 0.2;
                }
                50% {
                    opacity: 0.4;
                }
            }
        `;
        
        document.head.appendChild(styles);
    }

    // Handle summary button click
    async handleSummaryButtonClick() {
        if (this.isProcessing) {
            return;
        }

        console.log('EmailSummarizer: Summary button clicked');
        
        // Update button state
        this.updateButtonState('processing');
        
        try {
            const unreadEmails = this.extractUnreadEmails();
            
            if (unreadEmails.length === 0) {
                console.log('EmailSummarizer: No unread emails found');
                this.displaySummary({
                    success: false,
                    message: "No unread emails found in your inbox."
                });
                return;
            }

            console.log(`EmailSummarizer: Found ${unreadEmails.length} unread emails, generating summary...`);
            
            // Generate and display summary
            const summaryResult = await this.generateSummary(unreadEmails);
            this.displaySummary(summaryResult);
            
        } catch (error) {
            console.error('EmailSummarizer: Error in summary generation:', error);
            this.displaySummary({
                success: false,
                message: "An error occurred while generating the summary. Please try again."
            });
        } finally {
            // Reset button state
            this.updateButtonState('ready');
        }
    }

    // Update button state
    updateButtonState(state) {
        if (!this.summaryButton) return;

        const icon = this.summaryButton.querySelector('.velocitas-summary-icon');
        
        if (state === 'processing') {
            this.isProcessing = true;
            this.summaryButton.classList.add('processing');
            this.summaryButton.setAttribute('aria-label', 'Processing...');
            if (icon) {
                icon.innerHTML = `
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    <path d="M12 6l1.5 3L17 9.5l-2.5 2.4L15 15l-3-1.6L9 15l.5-3.1L7 9.5l3.5-.5L12 6z" opacity="0.7"/>
                    <circle cx="12" cy="12" r="1" opacity="0.5"/>
                    <circle cx="6" cy="6" r="0.5" opacity="0.8"/>
                    <circle cx="18" cy="6" r="0.5" opacity="0.6"/>
                    <circle cx="6" cy="18" r="0.5" opacity="0.4"/>
                    <circle cx="18" cy="18" r="0.5" opacity="0.9"/>
                `;
            }
        } else {
            this.isProcessing = false;
            this.summaryButton.classList.remove('processing');
            this.summaryButton.setAttribute('aria-label', 'Summarize Unread Emails');
            if (icon) {
                icon.innerHTML = `
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    <path d="M12 6l1.5 3L17 9.5l-2.5 2.4L15 15l-3-1.6L9 15l.5-3.1L7 9.5l3.5-.5L12 6z" opacity="0.7"/>
                    <circle cx="12" cy="12" r="1" opacity="0.5"/>
                `;
            }
        }
    }

    // Extract unread emails from Gmail interface
    extractUnreadEmails() {
        const unreadEmails = [];
        
        // Gmail uses different classes for unread emails
        const emailRows = document.querySelectorAll('tr[class*="zA"]');
        
        emailRows.forEach((row, index) => {
            try {
                // Check if email is unread (unread emails have different styling)
                const isUnread = row.classList.contains('zE') || // Bold/unread class
                               row.querySelector('.yW span[style*="font-weight: bold"]') ||
                               row.querySelector('.yW[style*="font-weight: bold"]') ||
                               row.querySelector('[class*="zE"]');

                if (!isUnread) {
                    return; // Skip read emails
                }

                // Extract email details
                const titleElement = row.querySelector('[data-thread-id] span[id*=":"]') || 
                                   row.querySelector('span[data-thread-id]') ||
                                   row.querySelector('span[id*=":"]');
                const title = titleElement ? titleElement.textContent.trim() : 'No title';

                const snippetElement = row.querySelector('.y2') || 
                                     row.querySelector('[class*="y2"]') ||
                                     row.querySelector('.bog');
                const snippet = snippetElement ? snippetElement.textContent.trim() : 'No snippet';

                const senderElement = row.querySelector('[email]') ||
                                    row.querySelector('.yW') ||
                                    row.querySelector('[class*="yW"]');
                const sender = senderElement ? 
                              (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                              'Unknown sender';

                const dateElement = row.querySelector('[title*=":"]') ||
                                  row.querySelector('.xY') ||
                                  row.querySelector('[class*="xY"]');
                const date = dateElement ? 
                           (dateElement.getAttribute('title') || dateElement.textContent.trim()) : 
                           'No date';

                // Only add if we have meaningful data
                if (title !== 'No title' || snippet !== 'No snippet') {
                    unreadEmails.push({
                        title,
                        snippet: snippet.substring(0, 300) + (snippet.length > 300 ? '...' : ''),
                        sender,
                        date,
                        rowIndex: index,
                        isUnread: true
                    });
                }
            } catch (error) {
                console.warn(`EmailSummarizer: Error extracting unread email ${index}:`, error);
            }
        });

        return unreadEmails;
    }

    // Generate summary for unread emails
    async generateSummary(unreadEmails) {
        if (!unreadEmails || unreadEmails.length === 0) {
            return {
                success: false,
                message: "No unread emails found to summarize."
            };
        }

        try {
            console.log(`EmailSummarizer: Generating summary for ${unreadEmails.length} unread emails using Hack Club AI...`);
            
            const prompt = this.createSummaryPrompt(unreadEmails);
            const summary = await this.callHackClubAI(prompt);
            
            return {
                success: true,
                summary: summary,
                emailCount: unreadEmails.length,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('EmailSummarizer: Error generating summary:', error);
            return {
                success: false,
                message: error.message || "Failed to generate email summary."
            };
        }
    }

    // Create an optimized prompt for email summarization
    createSummaryPrompt(emails) {
        const emailsText = emails.map((email, index) => {
            return `Email ${index + 1}:
From: ${email.sender}
Date: ${email.date}
Subject: ${email.title}
Preview: ${email.snippet}
---`;
        }).join('\n\n');

        return `You are an expert email assistant. Please provide a concise, well-structured summary of the following unread emails.

Format your response using simple HTML structure:
- Use <h4> for section headers
- Use <p> for paragraphs
- Use <ul> and <li> for lists
- Use <strong> for emphasis
- For urgent items, wrap in: <div class="urgent-item">content</div>
- For action items, wrap in: <div class="action-item">content</div>
- For email groups, wrap in: <div class="email-group"><div class="email-group-title">Title</div>content</div>

Your summary should include:

<h4>📊 Overview</h4>
<p>Brief summary of total emails and main themes</p>

<h4>📂 Email Groups</h4>
<div class="email-group">
<div class="email-group-title">Category Name (X emails)</div>
<ul>
<li>Brief description of emails in this category</li>
</ul>
</div>

<h4>⚠️ Urgent Items</h4>
<div class="urgent-item">Any security alerts, deadlines, or time-sensitive items</div>

<h4>✅ Action Items</h4>
<div class="action-item">
<ul>
<li>Specific actions the user should take</li>
<li>Items requiring response or review</li>
</ul>
</div>

Keep the summary concise but comprehensive. Group similar emails together and highlight the most important information.

UNREAD EMAILS TO SUMMARIZE:
${emailsText}

SUMMARY:`;
    }

    // Call Hack Club AI API for summarization
    async callHackClubAI(prompt, retryCount = 0) {
        try {
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    messages: [
                        {
                            role: 'user',
                            content: prompt
                        }
                    ]
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Hack Club AI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
            }

            const data = await response.json();
            
            // Handle the response structure
            if (data.choices && data.choices.length > 0) {
                return data.choices[0].message.content.trim();
            } else if (data.message) {
                return data.message.trim();
            } else {
                throw new Error('Unexpected response format from Hack Club AI');
            }
        } catch (error) {
            console.error('EmailSummarizer: Hack Club AI API call failed:', error);
            
            if (retryCount < this.maxRetries) {
                console.log(`EmailSummarizer: Retrying API call (${retryCount + 1}/${this.maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                return this.callHackClubAI(prompt, retryCount + 1);
            }
            
            throw error;
        }
    }

    // Display summary in a nice overlay
    displaySummary(summaryResult) {
        // Remove existing summary if any
        this.hideSummary();

        const overlay = document.createElement('div');
        overlay.id = 'velocitas-summary-overlay';
        
        // Remove <br> tags from summary for compactness
        function cleanSummary(summary) {
            // Remove all <br> tags (single or multiple)
            return summary.replace(/<br\s*\/?\s*>/gi, '');
        }

        if (summaryResult.success) {
            overlay.innerHTML = `
                <div class="velocitas-summary-container">
                    <div class="velocitas-summary-header">
                        <h3>📧 Unread Email Summary</h3>
                        <button class="velocitas-close-btn">&times;</button>
                    </div>
                    <div class="velocitas-summary-meta">
                        <span class="velocitas-email-count">${summaryResult.emailCount} unread emails</span>
                        <span class="velocitas-timestamp">${new Date(summaryResult.timestamp).toLocaleString()}</span>
                    </div>
                    <div class="velocitas-summary-content">
                        ${cleanSummary(summaryResult.summary)}
                    </div>
                    <div class="velocitas-summary-footer">
                        <button class="velocitas-refresh-btn">🔄 Refresh Summary</button>
                    </div>
                </div>
            `;
        } else {
            overlay.innerHTML = `
                <div class="velocitas-summary-container">
                    <div class="velocitas-summary-header">
                        <h3>📧 Email Summary</h3>
                        <button class="velocitas-close-btn">&times;</button>
                    </div>
                    <div class="velocitas-summary-error">
                        <p>❌ ${summaryResult.message}</p>
                    </div>
                </div>
            `;
        }

        // Apply styles
        this.applySummaryStyles(overlay);
        
        // Add styles and overlay to page
        document.head.insertAdjacentHTML('beforeend', this.getSummaryStyles());
        document.body.appendChild(overlay);

        // Add event listeners after the overlay is added to DOM
        this.addOverlayEventListeners();

        console.log('EmailSummarizer: Summary displayed');
    }

    // Add event listeners for overlay buttons
    addOverlayEventListeners() {
        const closeBtn = document.querySelector('.velocitas-close-btn');
        const refreshBtn = document.querySelector('.velocitas-refresh-btn');
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideSummary();
            });
        }
        
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshSummary();
            });
        }
    }

    // Hide summary overlay
    hideSummary() {
        const overlay = document.getElementById('velocitas-summary-overlay');
        const styles = document.getElementById('velocitas-summary-styles');
        
        if (overlay) {
            overlay.remove();
        }
        if (styles) {
            styles.remove();
        }
    }

    // Apply styles to summary overlay
    applySummaryStyles(overlay) {
        overlay.style.cssText = `
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: 100% !important;
            background: rgba(0, 0, 0, 0.5) !important;
            z-index: 10000 !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            backdrop-filter: blur(2px) !important;
        `;
    }

    // Get CSS styles for summary display
    getSummaryStyles() {
        return `
            <style id="velocitas-summary-styles">
            .velocitas-summary-container {
                background: #ffffff !important;
                border: 1px solid #dadce0 !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1) !important;
                max-width: 650px !important;
                width: 90% !important;
                max-height: 80vh !important;
                overflow: hidden !important;
                font-family: 'Google Sans', Roboto, RobotoDraft, Helvetica, Arial, sans-serif !important;
                display: flex !important;
                flex-direction: column !important;
            }
            
            .velocitas-summary-header {
                background: #ffffff !important;
                color: #202124 !important;
                padding: 16px 20px 12px !important;
                border-bottom: 1px solid #e8eaed !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                flex-shrink: 0 !important;
            }
            
            .velocitas-summary-header h3 {
                margin: 0 !important;
                font-size: 16px !important;
                font-weight: 500 !important;
                color: #202124 !important;
            }
            
            .velocitas-close-btn {
                background: transparent !important;
                border: none !important;
                color: #5f6368 !important;
                font-size: 20px !important;
                cursor: pointer !important;
                padding: 6px !important;
                border-radius: 50% !important;
                width: 32px !important;
                height: 32px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                transition: background-color 0.2s ease !important;
            }
            
            .velocitas-close-btn:hover {
                background: #f1f3f4 !important;
            }
            
            .velocitas-summary-meta {
                padding: 8px 20px !important;
                background: #fffbf0 !important;
                border-bottom: 1px solid #e8eaed !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                font-size: 13px !important;
                color: #5f6368 !important;
                flex-shrink: 0 !important;
            }
            
            .velocitas-email-count {
                font-weight: 500 !important;
                color: #202124 !important;
            }
            
            .velocitas-timestamp {
                color: #5f6368 !important;
                font-size: 12px !important;
            }
            
            .velocitas-summary-content {
                padding: 16px 20px !important;
                line-height: 1.4 !important;
                color: #202124 !important;
                font-size: 13px !important;
                background: #ffffff !important;
                overflow-y: auto !important;
                flex: 1 !important;
            }
            
            .velocitas-summary-content h4 {
                font-size: 14px !important;
                font-weight: 500 !important;
                color: #202124 !important;
                margin: 12px 0 6px 0 !important;
                padding-bottom: 3px !important;
                border-bottom: 2px solid #ffd700 !important;
            }
            
            .velocitas-summary-content h4:first-child {
                margin-top: 0 !important;
            }
            
            .velocitas-summary-content p {
                margin: 6px 0 !important;
                line-height: 1.4 !important;
            }
            
            .velocitas-summary-content ul {
                margin: 4px 0 8px 0 !important;
                padding-left: 16px !important;
                list-style-type: none !important;
            }
            
            .velocitas-summary-content li {
                margin: 3px 0 !important;
                padding-left: 0 !important;
                position: relative !important;
                line-height: 1.3 !important;
            }
            
            .velocitas-summary-content li:before {
                content: "•" !important;
                position: absolute !important;
                left: -10px !important;
                color: #ffd700 !important;
                font-weight: bold !important;
            }
            
            .velocitas-summary-content .email-group {
                background: #fffbf0 !important;
                border: 1px solid #fff3cd !important;
                border-radius: 6px !important;
                padding: 8px 10px !important;
                margin: 4px 0 !important;
            }
            
            .velocitas-summary-content .email-group-title {
                font-weight: 600 !important;
                color: #cc8c00 !important;
                margin-bottom: 2px !important;
                font-size: 13px !important;
            }
            
            .velocitas-summary-content .email-group ul {
                margin: 0 !important;
            }
            
            .velocitas-summary-content .email-group p {
                margin: 2px 0 !important;
            }
            
            .velocitas-summary-content .urgent-item {
                background: #fff8e1 !important;
                border-left: 3px solid #ff9800 !important;
                padding: 8px 10px !important;
                margin: 4px 0 !important;
                border-radius: 0 4px 4px 0 !important;
                font-size: 13px !important;
            }
            
            .velocitas-summary-content .action-item {
                background: #fffbf0 !important;
                border-left: 3px solid #ffd700 !important;
                padding: 8px 10px !important;
                margin: 4px 0 !important;
                border-radius: 0 4px 4px 0 !important;
                font-size: 13px !important;
            }
            
            .velocitas-summary-content .action-item ul,
            .velocitas-summary-content .urgent-item ul {
                margin: 2px 0 0 0 !important;
                padding-left: 12px !important;
            }
            
            .velocitas-summary-content .action-item li,
            .velocitas-summary-content .urgent-item li {
                margin: 2px 0 !important;
            }
            
            .velocitas-summary-error {
                padding: 20px !important;
                text-align: center !important;
                color: #5f6368 !important;
                background: #ffffff !important;
            }
            
            .velocitas-summary-footer {
                padding: 12px 20px !important;
                border-top: 1px solid #e8eaed !important;
                text-align: center !important;
                background: #ffffff !important;
                flex-shrink: 0 !important;
            }
            
            .velocitas-refresh-btn {
                background: #ffd700 !important;
                color: #333333 !important;
                border: none !important;
                padding: 6px 14px !important;
                border-radius: 4px !important;
                font-size: 13px !important;
                font-weight: 500 !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
            }
            
            .velocitas-refresh-btn:hover {
                background: #ffcc00 !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
            }
            </style>
        `;
    }

    // Refresh summary with current unread emails
    async refreshSummary() {
        this.hideSummary();
        
        // Show loading state
        const overlay = document.createElement('div');
        overlay.id = 'velocitas-summary-overlay';
        overlay.innerHTML = `
            <div class="velocitas-summary-container">
                <div class="velocitas-summary-header">
                    <h3>📧 Generating Summary...</h3>
                </div>
                <div class="velocitas-summary-content" style="text-align: center; padding: 40px;">
                    <div class="velocitas-spinner"></div>
                    <p>Analyzing your unread emails...</p>
                </div>
            </div>
        `;
        
        this.applySummaryStyles(overlay);
        document.head.insertAdjacentHTML('beforeend', this.getSummaryStyles());
        document.body.appendChild(overlay);
        
        // Generate new summary
        const unreadEmails = this.extractUnreadEmails();
        const summaryResult = await this.generateSummary(unreadEmails);
        
        // Display the result
        this.displaySummary(summaryResult);
    }

    // Get status information
    getStatus() {
        const unreadEmails = this.extractUnreadEmails();
        return {
            unreadCount: unreadEmails.length,
            hasApiKey: true, // Always true since no API key is needed
            isProcessing: this.isProcessing,
            apiProvider: 'Hack Club AI'
        };
    }

    // Clear cached data
    clearCache() {
        this.cache.clear();
        console.log('EmailSummarizer: Cache cleared');
    }

    // Cleanup method
    cleanup() {
        // Remove injected button
        const summaryButton = document.getElementById('velocitas-summary-btn');
        if (summaryButton) {
            summaryButton.remove();
        }
        
        // Remove button styles
        const buttonStyles = document.getElementById('velocitas-summary-btn-styles');
        if (buttonStyles) {
            buttonStyles.remove();
        }
        
        // Hide any open summary
        this.hideSummary();
        
        // Clear cache
        this.cache.clear();
        
        console.log('EmailSummarizer: Cleanup completed');
    }
}