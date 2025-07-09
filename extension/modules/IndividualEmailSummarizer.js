// IndividualEmailSummarizer.js - Individual email summarization module
window.IndividualEmailSummarizer = class IndividualEmailSummarizer {
    constructor() {
        this.cache = new Map();
        this.apiUrl = 'https://ai.hackclub.com/chat/completions';
        this.sidebarPanel = null;
        this.currentEmailId = null;
        this.emailObserver = null;
        this.isProcessing = false;
        this.maxRetries = 3;
        this.retryDelay = 1000;
    }

    // Initialize the individual email summarizer
    async init() {
        console.log('IndividualEmailSummarizer: Initializing...');
        
        // Wait a bit for Gmail to load completely
        setTimeout(() => {
            console.log('IndividualEmailSummarizer: Setting up email click detection...');
            this.setupEmailClickDetection();
            
            console.log('IndividualEmailSummarizer: Creating sidebar panel...');
            this.createSidebarPanel();
            
            console.log('IndividualEmailSummarizer: Initialized successfully');
        }, 3000); // Wait 3 seconds for Gmail to load
    }

    // Set up detection for when emails are clicked/opened
    setupEmailClickDetection() {
        console.log('IndividualEmailSummarizer: Setting up email click detection...');
        
        // Use MutationObserver to detect when Gmail opens an email
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    // Check for various Gmail email view patterns
                    this.checkForOpenEmailInMutations(mutation);
                }
            });
        });

        // Start observing Gmail's main content area
        const gmailContent = document.querySelector('[role="main"]') || document.body;
        observer.observe(gmailContent, {
            childList: true,
            subtree: true
        });

        this.emailObserver = observer;
        console.log('IndividualEmailSummarizer: MutationObserver set up');

        // Also listen for URL changes (Gmail is a SPA)
        let lastUrl = location.href;
        const urlObserver = new MutationObserver(() => {
            const url = location.href;
            if (url !== lastUrl) {
                lastUrl = url;
                console.log('IndividualEmailSummarizer: URL changed to:', url);
                
                // Check if we're viewing an individual email vs inbox list
                this.handleUrlChange(url);
            }
        });
        
        urlObserver.observe(document, { subtree: true, childList: true });
        
        // Also check for emails that might already be open
        setTimeout(() => {
            console.log('IndividualEmailSummarizer: Checking for already open emails...');
            this.handleUrlChange(window.location.href);
        }, 1000);
    }

    // Handle URL changes to detect email vs inbox view
    handleUrlChange(url) {
        const isEmailView = this.isEmailViewUrl(url);
        
        if (isEmailView) {
            console.log('IndividualEmailSummarizer: Detected email view URL, checking for email...');
            // Wait a bit for Gmail to load the email content
            setTimeout(() => this.checkForOpenEmail(), 1500);
        } else {
            console.log('IndividualEmailSummarizer: Not in email view, showing placeholder');
            this.showInboxPlaceholder();
        }
    }

    // Check if the current URL represents an individual email view
    isEmailViewUrl(url) {
        // Gmail email URLs have patterns like:
        // https://mail.google.com/mail/u/0/#inbox/FMfcgzQbfxhlhnqNqbmWhSzqBKrxGVjr
        // https://mail.google.com/mail/u/5/#sent/FMfcgzQbfxhlhnqNqbmWhSzqBKrxGVjr
        const urlPattern = /#(inbox|sent|drafts|spam|trash|starred|important|all)\/[a-zA-Z0-9_-]+$/;
        return urlPattern.test(url);
    }

    // Show placeholder for inbox/list view
    showInboxPlaceholder() {
        if (!this.sidebarPanel) return;

        const content = this.sidebarPanel.querySelector('.velocitas-panel-content');
        content.innerHTML = `
            <div class="velocitas-panel-placeholder">
                <p>Click on an email to load an individual summary</p>
            </div>
        `;
        
        this.currentEmailId = null;
    }

    // Check for open email in mutations
    checkForOpenEmailInMutations(mutation) {
        const addedNodes = Array.from(mutation.addedNodes);
        
        addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                // Check if this node or its children contain email content
                const emailContainers = [
                    node.querySelector ? node.querySelector('[data-thread-id]') : null,
                    node.querySelector ? node.querySelector('.ii.gt') : null,
                    node.querySelector ? node.querySelector('.nH.if') : null,
                    node.matches && node.matches('[data-thread-id]') ? node : null,
                    node.matches && node.matches('.ii.gt') ? node : null
                ].filter(Boolean);

                emailContainers.forEach(container => {
                    if (container) {
                        const threadId = container.getAttribute('data-thread-id') || 
                                       container.querySelector('[data-thread-id]')?.getAttribute('data-thread-id') ||
                                       'detected-email-' + Date.now();
                        
                        if (threadId && threadId !== this.currentEmailId) {
                            console.log('IndividualEmailSummarizer: Detected new email via mutations:', threadId);
                            this.currentEmailId = threadId;
                            this.handleEmailOpened(container);
                        }
                    }
                });
            }
        });
    }

    // Check for currently open email
    checkForOpenEmail() {
        // Try multiple selectors to find the email container
        const emailSelectors = [
            '[data-thread-id]',
            '.nH.if',
            '.ii.gt',
            '.adn.ads',
            '.h7'
        ];

        let emailContainer = null;
        let threadId = null;

        // Try each selector
        for (const selector of emailSelectors) {
            const container = document.querySelector(selector);
            if (container && this.hasEmailContent(container)) {
                emailContainer = container;
                threadId = container.getAttribute('data-thread-id') || 
                         this.extractThreadIdFromUrl() ||
                         'email-' + Date.now();
                break;
            }
        }

        if (emailContainer && threadId) {
            console.log('IndividualEmailSummarizer: Found email container:', emailContainer, 'Thread ID:', threadId);
            
            if (threadId !== this.currentEmailId) {
                this.currentEmailId = threadId;
                this.handleEmailOpened(emailContainer);
            }
        } else {
            console.log('IndividualEmailSummarizer: No email container found');
            // If we're in an email URL but can't find content, show loading
            if (this.isEmailViewUrl(window.location.href)) {
                this.showLoadingState();
                // Retry after a short delay
                setTimeout(() => this.checkForOpenEmail(), 1000);
            } else {
                this.showInboxPlaceholder();
            }
        }
    }

    // Extract thread ID from URL
    extractThreadIdFromUrl() {
        const url = window.location.href;
        const match = url.match(/#(inbox|sent|drafts|spam|trash|starred|important|all)\/([a-zA-Z0-9_-]+)$/);
        return match ? match[2] : null;
    }

    // Check if container has meaningful email content
    hasEmailContent(container) {
        if (!container) return false;
        
        const text = container.textContent.trim();
        return text.length > 100 && (
            container.querySelector('h2') || // Subject
            container.querySelector('[email]') || // Sender
            container.querySelector('.go') || // Header info
            container.querySelector('.ii.gt') || // Email body
            container.querySelector('.a3s.aiL') // Email content
        );
    }

    // Handle when an email is opened
    async handleEmailOpened(emailContainer) {
        console.log('IndividualEmailSummarizer: Email opened, extracting content...');
        
        // Show loading state in sidebar
        this.showLoadingState();
        
        // Extract email content
        const emailContent = this.extractEmailContent(emailContainer);
        
        if (!emailContent.subject && !emailContent.body) {
            console.log('IndividualEmailSummarizer: No meaningful content found');
            this.showError('Unable to extract email content for summarization.');
            
            // Clear chatbox content when no email content is available
            if (window.VelocitasExtensionInstance && window.VelocitasExtensionInstance.emailChatbox) {
                window.VelocitasExtensionInstance.emailChatbox.clearEmailContent();
            }
            return;
        }

        // Share email content with chatbox
        if (window.VelocitasExtensionInstance && window.VelocitasExtensionInstance.emailChatbox) {
            window.VelocitasExtensionInstance.emailChatbox.setEmailContent(emailContent);
        }

        // Check cache first
        const cacheKey = this.generateCacheKey(emailContent);
        if (this.cache.has(cacheKey)) {
            console.log('IndividualEmailSummarizer: Using cached summary');
            this.displaySummary(this.cache.get(cacheKey));
            return;
        }

        // Generate summary
        try {
            const summary = await this.generateSummary(emailContent);
            
            // Cache the result
            this.cache.set(cacheKey, summary);
            
            // Display summary
            this.displaySummary(summary);
            
        } catch (error) {
            console.error('IndividualEmailSummarizer: Error generating summary:', error);
            this.showError('Failed to generate email summary. Please try again.');
        }
    }

    // Extract email content from the Gmail interface
    extractEmailContent(container) {
        const emailContent = {
            subject: '',
            sender: '',
            date: '',
            body: '',
            attachments: []
        };

        try {
            // Extract subject
            const subjectElement = container.querySelector('h2') ||
                                 container.querySelector('[data-legacy-thread-id]') ||
                                 container.querySelector('.hP');
            if (subjectElement) {
                emailContent.subject = subjectElement.textContent.trim();
            }

            // Extract sender
            const senderElement = container.querySelector('[email]') ||
                                container.querySelector('.go span') ||
                                container.querySelector('.gD');
            if (senderElement) {
                emailContent.sender = senderElement.getAttribute('email') || 
                                    senderElement.textContent.trim();
            }

            // Extract date
            const dateElement = container.querySelector('.g3') ||
                              container.querySelector('[title*=":"]');
            if (dateElement) {
                emailContent.date = dateElement.getAttribute('title') || 
                                  dateElement.textContent.trim();
            }

            // Extract email body - look for the main content area
            const bodySelectors = [
                '.ii.gt div',
                '.ii.gt',
                '.aHU',
                '.a3s.aiL',
                '.a3s.aXjCH',
                '.Am.Al.editable',
                '.Am.aO9.T-I-J3.J-J5-Ji'
            ];

            for (const selector of bodySelectors) {
                const bodyElement = container.querySelector(selector);
                if (bodyElement && bodyElement.textContent.trim().length > 50) {
                    emailContent.body = bodyElement.textContent.trim();
                    break;
                }
            }

            // If no body found, try to get any meaningful text content
            if (!emailContent.body) {
                const allText = container.textContent.trim();
                if (allText.length > 100) {
                    emailContent.body = allText.substring(0, 2000) + 
                                      (allText.length > 2000 ? '...' : '');
                }
            }

            // Extract attachments info
            const attachmentElements = container.querySelectorAll('[data-tooltip="Download"]') ||
                                     container.querySelectorAll('.aZo');
            emailContent.attachments = Array.from(attachmentElements).map(el => {
                const name = el.getAttribute('data-tooltip') || 
                           el.textContent.trim() || 
                           'Attachment';
                return { name };
            });

            console.log('IndividualEmailSummarizer: Extracted email content:', {
                subject: emailContent.subject.substring(0, 50),
                sender: emailContent.sender,
                bodyLength: emailContent.body.length,
                attachments: emailContent.attachments.length
            });

        } catch (error) {
            console.error('IndividualEmailSummarizer: Error extracting email content:', error);
        }

        return emailContent;
    }

    // Generate cache key for email content
    generateCacheKey(emailContent) {
        const key = `${emailContent.subject}_${emailContent.sender}_${emailContent.body.substring(0, 100)}`;
        return btoa(key).replace(/[+/=]/g, ''); // Base64 encode and clean
    }

    // Generate summary using Hack Club AI
    async generateSummary(emailContent, retryCount = 0) {
        if (this.isProcessing) {
            throw new Error('Summary generation already in progress');
        }

        this.isProcessing = true;

        try {
            const prompt = this.createSummaryPrompt(emailContent);
            
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
                throw new Error(`API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
            }

            const data = await response.json();
            
            let summary;
            if (data.choices && data.choices.length > 0) {
                summary = data.choices[0].message.content.trim();
            } else if (data.message) {
                summary = data.message.trim();
            } else {
                throw new Error('Unexpected response format from API');
            }

            return {
                success: true,
                summary: summary,
                timestamp: new Date().toISOString(),
                emailContent: emailContent
            };

        } catch (error) {
            console.error('IndividualEmailSummarizer: API call failed:', error);
            
            if (retryCount < this.maxRetries) {
                console.log(`IndividualEmailSummarizer: Retrying (${retryCount + 1}/${this.maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                return this.generateSummary(emailContent, retryCount + 1);
            }
            
            throw error;
        } finally {
            this.isProcessing = false;
        }
    }

    // Create prompt for email summarization
    createSummaryPrompt(emailContent) {
        return `You are an expert email assistant. Please provide a concise, well-structured summary of this email.

Format your response using simple HTML:
- Use <h4> for section headers
- Use <p> for paragraphs  
- Use <ul> and <li> for lists
- Use <strong> for emphasis
- For urgent items, wrap in: <div class="urgent-item">content</div>
- For action items, wrap in: <div class="action-item">content</div>

Your summary should include:

<h4>📋 Quick Summary</h4>
<p>Brief 2-3 sentence overview of the email's main purpose and key points</p>

<h4>🔍 Key Details</h4>
<ul>
<li>Important information, dates, numbers, or specifics mentioned</li>
<li>Key people or organizations involved</li>
</ul>

<h4>⚠️ Urgent Items</h4>
<div class="urgent-item">Any deadlines, time-sensitive information, or urgent requests</div>

<h4>✅ Action Items</h4>
<div class="action-item">
<ul>
<li>What the sender wants you to do</li>
<li>Any responses or follow-up needed</li>
<li>Deadlines or next steps</li>
</ul>
</div>

<h4>🎯 Priority Level</h4>
<p>High/Medium/Low and why</p>

Keep the summary concise but comprehensive. Focus on actionable information and key takeaways.

EMAIL TO SUMMARIZE:
Subject: ${emailContent.subject}
From: ${emailContent.sender}
Date: ${emailContent.date}
${emailContent.attachments.length > 0 ? `Attachments: ${emailContent.attachments.map(a => a.name).join(', ')}` : ''}

Content:
${emailContent.body}

SUMMARY:`;
    }

    // Create the sidebar panel
    createSidebarPanel() {
        // Find the Gmail sidebar where labels are shown
        const labelSection = document.querySelector('.nM') ||
                            document.querySelector('[aria-label="Labels"]') ||
                            document.querySelector('.yJ');

        if (!labelSection) {
            console.warn('IndividualEmailSummarizer: Could not find Gmail sidebar');
            return;
        }

        // Create the summary panel
        const summaryPanel = document.createElement('div');
        summaryPanel.id = 'velocitas-individual-summary-panel';
        summaryPanel.className = 'velocitas-summary-panel';
        summaryPanel.innerHTML = `
            <div class="velocitas-panel-header">
                <h3>Email Summary</h3>
                <div class="velocitas-panel-controls">
                    <button class="velocitas-panel-reload" aria-label="Reload email summary">↻</button>
                    <button class="velocitas-panel-toggle" aria-label="Toggle summary panel">−</button>
                </div>
            </div>
            <div class="velocitas-panel-content">
                <div class="velocitas-panel-placeholder">
                    <p>Click on an email to load an individual summary</p>
                </div>
            </div>
        `;

        // Insert the panel after the labels section
        labelSection.parentNode.insertBefore(summaryPanel, labelSection.nextSibling);

        // Add toggle functionality
        const toggleBtn = summaryPanel.querySelector('.velocitas-panel-toggle');
        const content = summaryPanel.querySelector('.velocitas-panel-content');
        
        toggleBtn.addEventListener('click', () => {
            const isCollapsed = content.style.display === 'none';
            content.style.display = isCollapsed ? 'block' : 'none';
            toggleBtn.textContent = isCollapsed ? '−' : '+';
            toggleBtn.setAttribute('aria-label', isCollapsed ? 'Collapse summary panel' : 'Expand summary panel');
        });

        // Add reload functionality
        const reloadBtn = summaryPanel.querySelector('.velocitas-panel-reload');
        reloadBtn.addEventListener('click', () => {
            this.reloadCurrentSummary();
        });

        // Add styles
        this.addPanelStyles();

        this.sidebarPanel = summaryPanel;
        console.log('IndividualEmailSummarizer: Sidebar panel created');
    }

    // Add styles for the sidebar panel
    addPanelStyles() {
        if (document.getElementById('velocitas-individual-summary-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'velocitas-individual-summary-styles';
        styles.textContent = `
            .velocitas-summary-panel {
                background: #ffffff !important;
                border: 1px solid #e8eaed !important;
                border-radius: 8px !important;
                margin: 12px 0 !important;
                font-family: 'Google Sans', Roboto, Arial, sans-serif !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
                overflow: hidden !important;
            }

            .velocitas-panel-header {
                background: #f8f9fa !important;
                border-bottom: 1px solid #e8eaed !important;
                padding: 12px 16px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
            }

            .velocitas-panel-header h3 {
                margin: 0 !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                color: #202124 !important;
            }

            .velocitas-panel-controls {
                display: flex !important;
                gap: 8px !important;
            }

            .velocitas-panel-reload,
            .velocitas-panel-toggle {
                background: transparent !important;
                border: none !important;
                color: #5f6368 !important;
                font-size: 16px !important;
                cursor: pointer !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
                transition: background-color 0.2s ease !important;
            }

            .velocitas-panel-reload:hover,
            .velocitas-panel-toggle:hover {
                background: #f1f3f4 !important;
            }

            .velocitas-panel-content {
                padding: 16px !important;
                max-height: 400px !important;
                overflow-y: auto !important;
                font-size: 13px !important;
                line-height: 1.4 !important;
            }

            .velocitas-panel-placeholder {
                text-align: center !important;
                color: #5f6368 !important;
                padding: 20px !important;
            }

            .velocitas-panel-placeholder p {
                margin: 0 !important;
                font-style: italic !important;
            }

            .velocitas-summary-loading {
                text-align: center !important;
                padding: 20px !important;
                color: #5f6368 !important;
            }

            .velocitas-summary-spinner {
                width: 24px !important;
                height: 24px !important;
                border: 2px solid #f3f3f3 !important;
                border-top: 2px solid #1a73e8 !important;
                border-radius: 50% !important;
                animation: velocitas-spin 1s linear infinite !important;
                margin: 0 auto 12px auto !important;
            }

            @keyframes velocitas-spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .velocitas-summary-content h4 {
                font-size: 13px !important;
                font-weight: 500 !important;
                color: #202124 !important;
                margin: 12px 0 6px 0 !important;
                border-bottom: 1px solid #e8eaed !important;
                padding-bottom: 4px !important;
            }

            .velocitas-summary-content h4:first-child {
                margin-top: 0 !important;
            }

            .velocitas-summary-content p {
                margin: 6px 0 !important;
                color: #202124 !important;
            }

            .velocitas-summary-content ul {
                margin: 4px 0 8px 0 !important;
                padding-left: 16px !important;
            }

            .velocitas-summary-content li {
                margin: 2px 0 !important;
                color: #202124 !important;
            }

            .velocitas-summary-content .urgent-item {
                background: #fff3cd !important;
                border-left: 3px solid #ff9800 !important;
                padding: 8px 12px !important;
                margin: 6px 0 !important;
                border-radius: 0 4px 4px 0 !important;
            }

            .velocitas-summary-content .action-item {
                background: #e8f5e8 !important;
                border-left: 3px solid #34a853 !important;
                padding: 8px 12px !important;
                margin: 6px 0 !important;
                border-radius: 0 4px 4px 0 !important;
            }

            .velocitas-summary-error {
                background: #fce8e6 !important;
                border: 1px solid #f28b82 !important;
                color: #d93025 !important;
                padding: 12px !important;
                border-radius: 4px !important;
                margin: 8px 0 !important;
            }

            .velocitas-summary-meta {
                font-size: 11px !important;
                color: #5f6368 !important;
                margin-top: 12px !important;
                padding-top: 8px !important;
                border-top: 1px solid #e8eaed !important;
            }
        `;

        document.head.appendChild(styles);
    }

    // Show loading state in the sidebar panel
    showLoadingState() {
        if (!this.sidebarPanel) return;

        const content = this.sidebarPanel.querySelector('.velocitas-panel-content');
        content.innerHTML = `
            <div class="velocitas-summary-loading">
                <div class="velocitas-summary-spinner"></div>
                <p>Generating AI summary...</p>
            </div>
        `;
    }

    // Display the summary in the sidebar panel
    displaySummary(summaryResult) {
        console.log('IndividualEmailSummarizer: Displaying summary:', summaryResult);
        
        if (!this.sidebarPanel) {
            console.error('IndividualEmailSummarizer: No sidebar panel found for display');
            return;
        }

        const content = this.sidebarPanel.querySelector('.velocitas-panel-content');
        
        if (summaryResult.success) {
            console.log('IndividualEmailSummarizer: Summary content:', summaryResult.summary);
            content.innerHTML = `
                <div class="velocitas-summary-content">
                    ${summaryResult.summary}
                    <div class="velocitas-summary-meta">
                        Generated at ${new Date(summaryResult.timestamp).toLocaleString()}
                    </div>
                </div>
            `;
            console.log('IndividualEmailSummarizer: Summary displayed successfully');
        } else {
            console.error('IndividualEmailSummarizer: Summary failed:', summaryResult.message);
            content.innerHTML = `
                <div class="velocitas-summary-error">
                    <p>❌ ${summaryResult.message || 'Failed to generate summary'}</p>
                </div>
            `;
        }
    }

    // Show error in the sidebar panel
    showError(message) {
        if (!this.sidebarPanel) return;

        const content = this.sidebarPanel.querySelector('.velocitas-panel-content');
        content.innerHTML = `
            <div class="velocitas-summary-error">
                <p>❌ ${message}</p>
            </div>
        `;
    }

    // Clear the current summary
    clearSummary() {
        if (!this.sidebarPanel) return;

        const content = this.sidebarPanel.querySelector('.velocitas-panel-content');
        content.innerHTML = `
            <div class="velocitas-panel-placeholder">
                <p>Click on an email to load an individual summary</p>
            </div>
        `;
        
        this.currentEmailId = null;
    }

    // Reload the current email summary
    reloadCurrentSummary() {
        if (!this.currentEmailId || !this.isEmailViewUrl(window.location.href)) {
            console.log('IndividualEmailSummarizer: No current email to reload or not in email view');
            this.showError('Please open an email first, then try reloading the summary.');
            return;
        }

        console.log('IndividualEmailSummarizer: Reloading current summary...');
        
        // Show loading immediately
        this.showLoadingState();
        
        // Find the current email container with improved detection
        const emailSelectors = [
            '[data-thread-id]',
            '.nH.if',
            '.ii.gt',
            '.adn.ads',
            '.h7'
        ];

        let currentEmailContainer = null;
        
        for (const selector of emailSelectors) {
            const container = document.querySelector(selector);
            if (container && this.hasEmailContent(container)) {
                currentEmailContainer = container;
                break;
            }
        }
        
        if (currentEmailContainer) {
            const emailContent = this.extractEmailContent(currentEmailContainer);
            const cacheKey = this.generateCacheKey(emailContent);
            
            // Remove from cache to force regeneration
            this.cache.delete(cacheKey);
            
            // Force regeneration
            this.currentEmailId = null; // Reset to force new processing
            this.handleEmailOpened(currentEmailContainer);
        } else {
            console.warn('IndividualEmailSummarizer: Could not find current email container for reload');
            this.showError('Unable to find email content for reload. Please refresh the page and try again.');
        }
    }

    // Test function to manually trigger email detection (for debugging)
    testEmailDetection() {
        console.log('IndividualEmailSummarizer: Manual test triggered');
        console.log('Current URL:', window.location.href);
        
        // Try to find any email containers
        const containers = [
            document.querySelector('[data-thread-id]'),
            document.querySelector('.nH.if'),
            document.querySelector('.ii.gt'),
            document.querySelector('.aHU'),
            document.querySelector('.a3s.aiL')
        ];
        
        console.log('Found containers:', containers.filter(Boolean));
        
        // Try to detect email content
        const testContainer = containers.find(c => c && c.textContent.trim().length > 100);
        
        if (testContainer) {
            console.log('Testing with container:', testContainer);
            this.currentEmailId = 'test-' + Date.now();
            this.handleEmailOpened(testContainer);
        } else {
            console.log('No suitable email container found for testing');
            // Create a test summary anyway
            this.displaySummary({
                success: true,
                summary: `
                    <h4>📋 Quick Summary</h4>
                    <p>This is a test summary to verify the display functionality is working correctly.</p>
                    
                    <h4>🔍 Key Details</h4>
                    <ul>
                        <li>Test email detection system is active</li>
                        <li>Summary panel is functioning</li>
                    </ul>
                    
                    <h4>✅ Action Items</h4>
                    <div class="action-item">
                        <ul>
                            <li>Check browser console for debugging information</li>
                            <li>Verify email detection is working properly</li>
                        </ul>
                    </div>
                    
                    <h4>🎯 Priority Level</h4>
                    <p>Medium - Testing functionality</p>
                `,
                timestamp: new Date().toISOString()
            });
        }
    }

    // Get status information
    getStatus() {
        return {
            cacheSize: this.cache.size,
            isProcessing: this.isProcessing,
            currentEmailId: this.currentEmailId,
            panelExists: !!this.sidebarPanel,
            apiProvider: 'Hack Club AI'
        };
    }

    // Clear cached summaries
    clearCache() {
        this.cache.clear();
        console.log('IndividualEmailSummarizer: Cache cleared');
    }

    // Cleanup method
    cleanup() {
        // Disconnect observer
        if (this.emailObserver) {
            this.emailObserver.disconnect();
            this.emailObserver = null;
        }

        // Remove sidebar panel
        if (this.sidebarPanel) {
            this.sidebarPanel.remove();
            this.sidebarPanel = null;
        }

        // Remove styles
        const styles = document.getElementById('velocitas-individual-summary-styles');
        if (styles) {
            styles.remove();
        }

        // Clear cache
        this.cache.clear();
        
        // Reset state
        this.currentEmailId = null;
        this.isProcessing = false;
        
        console.log('IndividualEmailSummarizer: Cleanup completed');
    }
}