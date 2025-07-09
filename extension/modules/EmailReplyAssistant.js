// EmailReplyAssistant.js - AI-powered email reply composition assistant
window.EmailReplyAssistant = class EmailReplyAssistant {
    constructor() {
        this.apiUrl = 'https://ai.hackclub.com/chat/completions';
        this.replyPanel = null;
        this.currentEmailContent = null;
        this.originalEmailContent = null;
        this.isProcessing = false;
        this.conversationHistory = [];
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.maxHistoryLength = 10;
        this.isReplyMode = false;
        this.composeTextarea = null;
        this.draftContent = '';
    }

    // Initialize the reply assistant
    async init() {
        console.log('EmailReplyAssistant: Initializing...');
        
        // Wait for Gmail to load properly
        setTimeout(() => {
            this.setupReplyDetection();
            console.log('EmailReplyAssistant: Initialized successfully');
        }, 3000);
    }

    // Set up detection for when user enters reply mode
    setupReplyDetection() {
        // Monitor for compose/reply windows
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.checkForReplyCompose(node);
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Initial check for existing compose windows
        this.checkForReplyCompose(document);
    }

    // Check if a reply/compose window is present
    checkForReplyCompose(container) {
        // Look for Gmail compose/reply containers
        const composeSelectors = [
            '[role="region"][aria-label*="Re:"]',
            '[role="region"][data-compose-id]',
            '.aoI[role="region"]',
            '.M9[jslog*="reply"]',
            '.ip.adB'
        ];

        for (const selector of composeSelectors) {
            const composeWindow = container.querySelector ? container.querySelector(selector) : null;
            
            if (composeWindow && !composeWindow.hasAttribute('data-velocitas-assistant')) {
                console.log('EmailReplyAssistant: Found compose window:', composeWindow);
                this.handleReplyDetected(composeWindow);
                break;
            }
        }
    }

    // Handle when a reply window is detected
    async handleReplyDetected(composeWindow) {
        composeWindow.setAttribute('data-velocitas-assistant', 'true');
        
        console.log('EmailReplyAssistant: Reply mode detected');
        this.isReplyMode = true;

        // Find the compose textarea
        this.findComposeTextarea(composeWindow);
        
        // Extract original email content for context
        await this.extractOriginalEmailContent();
        
        // Create the AI assistant panel
        this.createReplyAssistantPanel(composeWindow);
    }

    // Find the compose textarea element
    findComposeTextarea(composeWindow) {
        const textareaSelectors = [
            '[aria-label="Message Body"]',
            '.Am.aiL.Al.editable',
            '[contenteditable="true"][role="textbox"]',
            '.aO7 .Am.aiL',
            '#\\:sg'
        ];

        for (const selector of textareaSelectors) {
            const textarea = composeWindow.querySelector(selector);
            if (textarea) {
                this.composeTextarea = textarea;
                console.log('EmailReplyAssistant: Found compose textarea:', textarea);
                this.setupTextareaMonitoring();
                break;
            }
        }
    }

    // Monitor changes to the compose textarea
    setupTextareaMonitoring() {
        if (!this.composeTextarea) return;

        // Monitor content changes
        const observer = new MutationObserver(() => {
            this.draftContent = this.getTextareaContent();
        });

        observer.observe(this.composeTextarea, {
            childList: true,
            subtree: true,
            characterData: true
        });

        // Also listen for input events
        this.composeTextarea.addEventListener('input', () => {
            this.draftContent = this.getTextareaContent();
        });
    }

    // Get content from the compose textarea
    getTextareaContent() {
        if (!this.composeTextarea) return '';
        
        // Handle both plain text and rich text editors
        if (this.composeTextarea.innerHTML) {
            return this.composeTextarea.innerHTML;
        } else if (this.composeTextarea.textContent) {
            return this.composeTextarea.textContent;
        } else if (this.composeTextarea.value) {
            return this.composeTextarea.value;
        }
        
        return '';
    }

    // Set content in the compose textarea
    setTextareaContent(content) {
        if (!content || !content.trim()) {
            console.warn('EmailReplyAssistant: No content to set');
            return;
        }

        console.log('EmailReplyAssistant: Setting content in textarea:', content.substring(0, 100) + '...');
        
        // Enhanced selector strategy for Gmail compose areas
        const composeSelectors = [
            // Primary Gmail compose selectors
            'div[aria-label="Message Body"][contenteditable="true"]',
            '[aria-label="Message Body"]',
            'textarea[aria-label="Message Body"]',
            
            // Alternative selectors for different Gmail views
            '.Am.aiL.Al.editable[contenteditable="true"]',
            '.Am.Al.editable[contenteditable="true"]',
            'div[contenteditable="true"][role="textbox"]',
            '.aO7 .Am.aiL',
            '.editable[contenteditable="true"]',
            
            // Fallback selectors
            '[contenteditable="true"][spellcheck="true"]',
            'div[contenteditable="true"][dir="ltr"]',
            '#\\:sg'
        ];

        let contentSet = false;
        let targetElement = null;

        // Try each selector in order of preference
        for (const selector of composeSelectors) {
            const element = document.querySelector(selector);
            if (element && this.isVisibleAndEditable(element)) {
                targetElement = element;
                console.log('EmailReplyAssistant: Found compose element with selector:', selector);
                break;
            }
        }

        // If no element found, try to find it within the stored compose window
        if (!targetElement && this.composeTextarea) {
            targetElement = this.composeTextarea;
            console.log('EmailReplyAssistant: Using stored compose textarea');
        }

        if (!targetElement) {
            console.error('EmailReplyAssistant: No suitable compose element found');
            return;
        }

        // Clear existing content first
        this.clearTextareaContent(targetElement);

        // Set content based on element type
        if (targetElement.tagName === 'TEXTAREA') {
            // Plain text textarea
            console.log('EmailReplyAssistant: Setting content in plain text textarea');
            targetElement.value = content;
            this.triggerInputEvents(targetElement);
            contentSet = true;
        } else if (targetElement.getAttribute('contenteditable') === 'true') {
            // Rich text editor
            console.log('EmailReplyAssistant: Setting content in rich text editor');
            
            // Convert plain text to HTML, preserving line breaks
            const htmlContent = this.textToHtml(content);
            
            // Set content using different methods for reliability
            targetElement.innerHTML = htmlContent;
            
            // Also try setting via innerText for some Gmail versions
            if (!targetElement.innerHTML || targetElement.innerHTML === htmlContent) {
                targetElement.innerText = content;
            }
            
            this.triggerInputEvents(targetElement);
            contentSet = true;
        }

        if (contentSet) {
            // Update internal state
            this.draftContent = content;
            
            // Focus the element
            this.focusElement(targetElement);
            
            // Trigger additional events that Gmail might need
            this.triggerGmailSpecificEvents(targetElement);
            
            console.log('EmailReplyAssistant: Content successfully set');
        } else {
            console.warn('EmailReplyAssistant: Failed to set content');
        }
    }

    // Helper method to check if an element is visible and editable
    isVisibleAndEditable(element) {
        if (!element) return false;
        
        const style = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        
        return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            rect.width > 0 &&
            rect.height > 0 &&
            !element.disabled &&
            !element.readOnly
        );
    }

    // Helper method to clear textarea content
    clearTextareaContent(element) {
        if (element.tagName === 'TEXTAREA') {
            element.value = '';
        } else if (element.getAttribute('contenteditable') === 'true') {
            element.innerHTML = '';
            element.innerText = '';
        }
    }

    // Helper method to convert plain text to HTML
    textToHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/\n/g, '<br>')
            .replace(/\r/g, '');
    }

    // Helper method to trigger input events
    triggerInputEvents(element) {
        const events = [
            new Event('input', { bubbles: true, cancelable: true }),
            new Event('change', { bubbles: true, cancelable: true }),
            new Event('keyup', { bubbles: true, cancelable: true }),
            new Event('paste', { bubbles: true, cancelable: true })
        ];

        events.forEach(event => {
            try {
                element.dispatchEvent(event);
            } catch (error) {
                console.warn('EmailReplyAssistant: Failed to dispatch event:', error);
            }
        });
    }

    // Helper method to focus element safely
    focusElement(element) {
        try {
            element.focus();
            
            // For contenteditable elements, also set cursor to end
            if (element.getAttribute('contenteditable') === 'true') {
                const range = document.createRange();
                const sel = window.getSelection();
                
                if (element.childNodes.length > 0) {
                    range.setStartAfter(element.childNodes[element.childNodes.length - 1]);
                } else {
                    range.setStart(element, 0);
                }
                
                range.collapse(true);
                sel.removeAllRanges();
                sel.addRange(range);
            }
        } catch (error) {
            console.warn('EmailReplyAssistant: Failed to focus element:', error);
        }
    }

    // Helper method to trigger Gmail-specific events
    triggerGmailSpecificEvents(element) {
        // Gmail sometimes listens for these specific events
        const gmailEvents = [
            'DOMNodeInserted',
            'DOMSubtreeModified',
            'textInput'
        ];

        gmailEvents.forEach(eventType => {
            try {
                const event = new Event(eventType, { bubbles: true, cancelable: true });
                element.dispatchEvent(event);
            } catch (error) {
                // Some events might not be supported in all browsers
                console.debug('EmailReplyAssistant: Event not supported:', eventType);
            }
        });

        // Also trigger a manual check for Gmail's internal state
        setTimeout(() => {
            if (element.getAttribute('contenteditable') === 'true') {
                // Simulate typing by creating a temporary text node
                const tempText = document.createTextNode('');
                element.appendChild(tempText);
                element.removeChild(tempText);
            }
        }, 100);
    }

    // Extract the original email content that we're replying to
    async extractOriginalEmailContent() {
        // Try to find the original email content in the thread
        const emailContentSelectors = [
            '.ii.gt .a3s.aiL',
            '.adn.ads .a3s',
            '.gs .ii .a3s',
            '.h7 .ii.gt'
        ];

        let originalContent = null;

        for (const selector of emailContentSelectors) {
            const elements = document.querySelectorAll(selector);
            if (elements.length > 0) {
                // Get the most recent email (usually the last one)
                const lastEmail = elements[elements.length - 1];
                originalContent = this.extractEmailDetails(lastEmail);
                break;
            }
        }

        if (originalContent) {
            this.originalEmailContent = originalContent;
            console.log('EmailReplyAssistant: Extracted original email content');
        } else {
            console.warn('EmailReplyAssistant: Could not extract original email content');
        }
    }

    // Extract email details from an element
    extractEmailDetails(emailElement) {
        const container = emailElement.closest('.ii.gt') || emailElement.closest('.adn.ads') || emailElement;
        
        // Extract sender
        const senderElement = container.querySelector('[email]') || 
                            container.querySelector('.go span[name]') ||
                            container.querySelector('.yW');
        const sender = senderElement ? 
                      (senderElement.getAttribute('email') || senderElement.textContent.trim()) : 
                      'Unknown sender';

        // Extract subject
        const subjectElement = document.querySelector('.hP') || 
                             document.querySelector('.bog') ||
                             container.querySelector('[role="heading"]');
        const subject = subjectElement ? subjectElement.textContent.trim() : 'No subject';

        // Extract date
        const dateElement = container.querySelector('.g3') ||
                          container.querySelector('[title*=":"]');
        const date = dateElement ? 
                    (dateElement.getAttribute('title') || dateElement.textContent.trim()) : 
                    'Unknown date';

        // Extract body
        const body = emailElement.textContent || emailElement.innerText || '';

        return {
            sender,
            subject,
            date,
            body: body.trim().substring(0, 3000) // Limit length for context
        };
    }

    // Create the AI assistant panel
    createReplyAssistantPanel(composeWindow) {
        // Find the compose form container
        const formContainer = composeWindow.querySelector('form') || composeWindow;
        
        if (!formContainer) {
            console.warn('EmailReplyAssistant: Could not find form container');
            return;
        }

        // Create the assistant panel
        this.replyPanel = document.createElement('div');
        this.replyPanel.id = 'velocitas-reply-assistant';
        this.replyPanel.className = 'velocitas-reply-panel';
        this.replyPanel.innerHTML = `
            <div class="velocitas-reply-header">
                <h3>AI Reply Assistant</h3>
                <div class="velocitas-reply-controls">
                    <button class="velocitas-reply-clear" aria-label="Clear conversation" title="Clear conversation">🗑️</button>
                    <button class="velocitas-reply-toggle" aria-label="Toggle assistant panel">−</button>
                </div>
            </div>
            <div class="velocitas-reply-content">
                <div class="velocitas-reply-messages" id="velocitas-reply-messages">
                    <div class="velocitas-reply-welcome">
                        <p><strong>AI Reply Assistant Ready!</strong></p>
                        <p>I can help you:</p>
                        <ul>
                            <li>Draft a complete reply</li>
                            <li>Improve your current draft</li>
                            <li>Adjust tone (formal, casual, friendly)</li>
                            <li>Make it shorter or more detailed</li>
                            <li>Add specific points or remove sections</li>
                        </ul>
                        <p><em>Try: "Write a professional reply accepting their proposal" or "Make this more concise"</em></p>
                    </div>
                </div>
                <div class="velocitas-reply-input-container">
                    <textarea 
                        id="velocitas-reply-input" 
                        class="velocitas-reply-input" 
                        placeholder="Tell me how to help with your reply..."
                        rows="2"
                    ></textarea>
                    <button 
                        id="velocitas-reply-send" 
                        class="velocitas-reply-send"
                        aria-label="Send message"
                    >
                        ➤
                    </button>
                </div>
                <div class="velocitas-reply-actions">
                    <button class="velocitas-action-btn" data-action="draft">✍️ Draft Reply</button>
                    <button class="velocitas-action-btn" data-action="improve">✨ Improve Draft</button>
                    <button class="velocitas-action-btn" data-action="formal">👔 Make Formal</button>
                    <button class="velocitas-action-btn" data-action="casual">😊 Make Casual</button>
                </div>
            </div>
        `;

        // Insert the panel above the compose textarea
        const textareaContainer = formContainer.querySelector('.aoD') || 
                                formContainer.querySelector('.aDl') ||
                                this.composeTextarea?.parentElement ||
                                formContainer;

        if (textareaContainer) {
            textareaContainer.parentNode.insertBefore(this.replyPanel, textareaContainer);
        } else {
            formContainer.appendChild(this.replyPanel);
        }

        // Add styles and event listeners
        this.addReplyAssistantStyles();
        this.setupReplyEventListeners();

        console.log('EmailReplyAssistant: Assistant panel created');
    }

    // Setup event listeners for the reply assistant panel
    setupReplyEventListeners() {
        if (!this.replyPanel) return;

        // Toggle button
        const toggleBtn = this.replyPanel.querySelector('.velocitas-reply-toggle');
        const content = this.replyPanel.querySelector('.velocitas-reply-content');
        
        if (toggleBtn && content) {
            toggleBtn.addEventListener('click', () => {
                const isCollapsed = content.style.display === 'none';
                content.style.display = isCollapsed ? 'block' : 'none';
                toggleBtn.textContent = isCollapsed ? '−' : '+';
            });
        }

        // Clear conversation button
        const clearBtn = this.replyPanel.querySelector('.velocitas-reply-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearConversation();
            });
        }

        // Send button and input
        const sendBtn = this.replyPanel.querySelector('#velocitas-reply-send');
        const inputTextarea = this.replyPanel.querySelector('#velocitas-reply-input');
        
        if (sendBtn && inputTextarea) {
            sendBtn.addEventListener('click', () => {
                this.sendAssistantMessage();
            });

            inputTextarea.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendAssistantMessage();
                }
            });

            // Auto-resize
            inputTextarea.addEventListener('input', () => {
                this.autoResizeTextarea(inputTextarea);
            });
        }

        // Quick action buttons
        const actionButtons = this.replyPanel.querySelectorAll('.velocitas-action-btn');
        actionButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.getAttribute('data-action');
                this.handleQuickAction(action);
            });
        });
    }

    // Handle quick action buttons
    async handleQuickAction(action) {
        let prompt = '';
        
        switch (action) {
            case 'draft':
                prompt = 'Write a professional reply to this email';
                break;
            case 'improve':
                if (!this.draftContent.trim()) {
                    this.addAssistantMessage('assistant', 'Please write some content in the compose box first, then I can help improve it.');
                    return;
                }
                prompt = 'Improve this draft email to make it clearer and more professional';
                break;
            case 'formal':
                if (!this.draftContent.trim()) {
                    this.addAssistantMessage('assistant', 'Please write some content in the compose box first, then I can make it more formal.');
                    return;
                }
                prompt = 'Rewrite this email in a more formal and professional tone';
                break;
            case 'casual':
                if (!this.draftContent.trim()) {
                    this.addAssistantMessage('assistant', 'Please write some content in the compose box first, then I can make it more casual.');
                    return;
                }
                prompt = 'Rewrite this email in a more casual and friendly tone';
                break;
        }

        if (prompt) {
            this.addAssistantMessage('user', prompt);
            await this.processAssistantRequest(prompt);
        }
    }

    // Send a message to the AI assistant
    async sendAssistantMessage() {
        const inputTextarea = this.replyPanel.querySelector('#velocitas-reply-input');
        const message = inputTextarea.value.trim();
        
        if (!message || this.isProcessing) {
            return;
        }

        // Add user message
        this.addAssistantMessage('user', message);
        
        // Clear input
        inputTextarea.value = '';
        inputTextarea.style.height = 'auto';
        
        // Process the request
        await this.processAssistantRequest(message);
    }

    // Process AI assistant request
    async processAssistantRequest(userMessage) {
        this.isProcessing = true;
        this.showTypingIndicator();

        try {
            const response = await this.generateAssistantResponse(userMessage);
            this.removeTypingIndicator();
            
            // Check if this is a draft/rewrite request or if the response looks like draft content
            if (this.isDraftOrRewriteRequest(userMessage, response) || this.isResponseDraftContent(response)) {
                this.addDraftMessage(response);
            } else {
                this.addAssistantMessage('assistant', response);
            }
            
        } catch (error) {
            console.error('EmailReplyAssistant: Error generating response:', error);
            this.removeTypingIndicator();
            this.addAssistantMessage('assistant', '❌ Sorry, I encountered an error. Please try again.');
        } finally {
            this.isProcessing = false;
        }
    }

    // Check if the request is for drafting or rewriting
    isDraftOrRewriteRequest(userMessage, response) {
        const draftKeywords = ['write', 'draft', 'compose', 'create', 'rewrite', 'improve', 'formal', 'casual'];
        const messageWords = userMessage.toLowerCase();
        
        return draftKeywords.some(keyword => messageWords.includes(keyword)) && 
               response.length > 100; // Assume longer responses are draft content
    }

    // Check if the AI response looks like draft content that can be applied
    isResponseDraftContent(response) {
        // Check for email-like patterns and substantial content
        const emailPatterns = [
            /dear|hi|hello|greetings/i,
            /thank you|thanks|appreciate/i,
            /regards|sincerely|best/i,
            /please|would you|could you/i,
            /I hope|I am|I would/i
        ];
        
        // Must be substantial content (more than 150 chars) and contain email-like patterns
        if (response.length < 150) {
            return false;
        }
        
        // Check if it contains multiple email-like patterns
        const patternMatches = emailPatterns.filter(pattern => pattern.test(response)).length;
        
        // If it has 2+ email patterns, it's likely draft content
        if (patternMatches >= 2) {
            return true;
        }
        
        // Also check for paragraph structure (multiple sentences)
        const sentences = response.split(/[.!?]+/).filter(s => s.trim().length > 10);
        
        // If it has multiple sentences and at least one email pattern, treat as draft
        return sentences.length >= 2 && patternMatches >= 1;
    }

    // Add a draft message with apply button
    addDraftMessage(content) {
        const messagesContainer = this.replyPanel.querySelector('#velocitas-reply-messages');
        const placeholder = messagesContainer.querySelector('.velocitas-reply-welcome');
        
        if (placeholder) {
            placeholder.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'velocitas-reply-message velocitas-reply-draft';
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        // Generate unique IDs for this draft
        const draftId = 'draft-' + Date.now();
        const applyId = 'apply-' + draftId;
        const editId = 'edit-' + draftId;
        
        messageDiv.innerHTML = `
            <div class="velocitas-message-header">
                <span class="velocitas-message-role">AI Draft</span>
                <span class="velocitas-message-time">${timestamp}</span>
            </div>
            <div class="velocitas-message-content">
                <div class="velocitas-draft-content">${this.formatDraftContent(content)}</div>
                <div class="velocitas-draft-actions">
                    <button class="velocitas-apply-draft" id="${applyId}" data-draft-content="${this.escapeDraftContent(content)}">
                        ✅ Apply to Email
                    </button>
                    <button class="velocitas-edit-draft" id="${editId}" data-draft-content="${this.escapeDraftContent(content)}">
                        ✏️ Edit & Apply
                    </button>
                </div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        
        // Set up event listeners for the draft buttons
        document.getElementById(applyId).addEventListener('click', () => {
            const content = document.getElementById(applyId).getAttribute('data-draft-content');
            this.applyDraft(content);
        });
        
        document.getElementById(editId).addEventListener('click', () => {
            const content = document.getElementById(editId).getAttribute('data-draft-content');
            this.editDraft(content);
        });
        
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Format draft content for display
    formatDraftContent(content) {
        // Clean and format the content
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    // Escape content for button onclick attributes
    escapeDraftContent(content) {
        return content
            .replace(/'/g, "\\'")
            .replace(/"/g, '\\"')
            .replace(/\n/g, '\\n');
    }

    // Apply draft to the compose textarea
    applyDraft(content) {
        // Unescape the content
        const unescapedContent = content
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
            .replace(/\\n/g, '\n');
        
        // Use the enhanced setTextareaContent method
        this.setTextareaContent(unescapedContent);
        
        // Show success message
        this.addAssistantMessage('assistant', '✅ Draft applied to your email! The content has been injected into the compose box.');
    }

    // Edit and apply draft (opens in a simple dialog)
    editDraft(content) {
        // Unescape the content
        const unescapedContent = content
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
            .replace(/\\n/g, '\n');
        
        // Use the enhanced setTextareaContent method
        this.setTextareaContent(unescapedContent);
        
        // Show success message with editing instructions
        this.addAssistantMessage('assistant', '✅ Draft applied to the compose box! You can now edit it directly. The content should appear in the message body area where you can make any changes before sending.');
    }

    // Generate AI assistant response
    async generateAssistantResponse(userMessage, retryCount = 0) {
        try {
            // Add user message to conversation history
            this.conversationHistory.push({
                role: 'user',
                content: userMessage
            });

            // Keep history manageable
            if (this.conversationHistory.length > this.maxHistoryLength) {
                this.conversationHistory = this.conversationHistory.slice(-this.maxHistoryLength);
            }

            const messages = this.createAssistantMessages(userMessage);
            
            const response = await fetch(this.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    messages: messages
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
            }

            const data = await response.json();
            
            let aiResponse;
            if (data.choices && data.choices.length > 0) {
                aiResponse = data.choices[0].message.content.trim();
            } else if (data.message) {
                aiResponse = data.message.trim();
            } else {
                throw new Error('Unexpected response format from API');
            }

            // Add AI response to history
            this.conversationHistory.push({
                role: 'assistant',
                content: aiResponse
            });

            return aiResponse;

        } catch (error) {
            console.error('EmailReplyAssistant: API call failed:', error);
            
            if (retryCount < this.maxRetries) {
                console.log(`EmailReplyAssistant: Retrying (${retryCount + 1}/${this.maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                return this.generateAssistantResponse(userMessage, retryCount + 1);
            }
            
            throw error;
        }
    }

    // Create messages array for AI request
    createAssistantMessages(userMessage) {
        const systemPrompt = this.createReplySystemPrompt();
        const messages = [
            {
                role: 'system',
                content: systemPrompt
            }
        ];

        // Add conversation history
        messages.push(...this.conversationHistory);

        return messages;
    }

    // Create system prompt for reply assistance
    createReplySystemPrompt() {
        let prompt = `You are an expert email assistant helping the user compose a professional and effective email reply. 

ORIGINAL EMAIL CONTEXT:`;

        if (this.originalEmailContent) {
            prompt += `
From: ${this.originalEmailContent.sender}
Subject: ${this.originalEmailContent.subject}
Date: ${this.originalEmailContent.date}

Original Email Content:
${this.originalEmailContent.body}
`;
        } else {
            prompt += `
(Original email content not available - help based on user's requests)
`;
        }

        if (this.draftContent && this.draftContent.trim()) {
            prompt += `

CURRENT DRAFT:
${this.draftContent}
`;
        }

        prompt += `

INSTRUCTIONS:
- Help compose professional, clear, and appropriate email replies
- Consider the context of the original email when drafting responses
- When asked to write/draft/compose a complete email, provide the full email content ready to send
- When asked to improve/rewrite, modify the existing draft
- Adapt tone as requested (formal, casual, friendly, etc.)
- Be concise but complete
- Use proper email etiquette and formatting
- Include appropriate greetings and sign-offs when drafting complete emails
- For complete drafts, don't include subject lines (Gmail handles that)
- Focus on the body content of the reply

Be helpful and provide exactly what the user needs for their email communication.`;

        return prompt;
    }

    // Add message to assistant conversation
    addAssistantMessage(role, content) {
        const messagesContainer = this.replyPanel.querySelector('#velocitas-reply-messages');
        const placeholder = messagesContainer.querySelector('.velocitas-reply-welcome');
        
        if (placeholder) {
            placeholder.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `velocitas-reply-message velocitas-reply-${role}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="velocitas-message-header">
                <span class="velocitas-message-role">${role === 'user' ? 'You' : 'AI Assistant'}</span>
                <span class="velocitas-message-time">${timestamp}</span>
            </div>
            <div class="velocitas-message-content">${this.formatMessageContent(content)}</div>
        `;

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Format message content
    formatMessageContent(content) {
        // For user messages, escape HTML to prevent XSS
        if (!content.includes('<')) {
            return this.escapeHtml(content).replace(/\n/g, '<br>');
        }
        
        // For AI responses, allow basic HTML formatting
        return content;
    }

    // Escape HTML characters
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Show typing indicator
    showTypingIndicator() {
        const messagesContainer = this.replyPanel.querySelector('#velocitas-reply-messages');
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'velocitas-reply-message velocitas-reply-assistant velocitas-typing-indicator';
        typingDiv.id = 'velocitas-typing-indicator';
        typingDiv.innerHTML = `
            <div class="velocitas-message-header">
                <span class="velocitas-message-role">AI Assistant</span>
            </div>
            <div class="velocitas-message-content">
                <div class="velocitas-typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;

        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Remove typing indicator
    removeTypingIndicator() {
        const typingIndicator = this.replyPanel.querySelector('#velocitas-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Auto-resize textarea
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        const maxHeight = 120;
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = newHeight + 'px';
    }

    // Clear conversation history
    clearConversation() {
        this.conversationHistory = [];
        const messagesContainer = this.replyPanel.querySelector('#velocitas-reply-messages');
        messagesContainer.innerHTML = `
            <div class="velocitas-reply-welcome">
                <p><strong>AI Reply Assistant Ready!</strong></p>
                <p>I can help you:</p>
                <ul>
                    <li>Draft a complete reply</li>
                    <li>Improve your current draft</li>
                    <li>Adjust tone (formal, casual, friendly)</li>
                    <li>Make it shorter or more detailed</li>
                    <li>Add specific points or remove sections</li>
                </ul>
                <p><em>Try: "Write a professional reply accepting their proposal" or "Make this more concise"</em></p>
            </div>
        `;
    }

    // Add styles for the reply assistant
    addReplyAssistantStyles() {
        if (document.getElementById('velocitas-reply-assistant-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'velocitas-reply-assistant-styles';
        styles.textContent = `
            .velocitas-reply-panel {
                background: #ffffff !important;
                border: 1px solid #e8eaed !important;
                border-radius: 8px !important;
                margin: 0 0 16px 0 !important;
                font-family: 'Google Sans', Roboto, Arial, sans-serif !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
                overflow: hidden !important;
                max-width: 100% !important;
            }

            .velocitas-reply-header {
                background: #f8f9fa !important;
                border-bottom: 1px solid #e8eaed !important;
                padding: 12px 16px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
            }

            .velocitas-reply-header h3 {
                margin: 0 !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                color: #202124 !important;
            }

            .velocitas-reply-controls {
                display: flex !important;
                gap: 8px !important;
            }

            .velocitas-reply-clear,
            .velocitas-reply-toggle {
                background: transparent !important;
                border: none !important;
                color: #5f6368 !important;
                font-size: 14px !important;
                cursor: pointer !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
                transition: background-color 0.2s ease !important;
            }

            .velocitas-reply-clear:hover,
            .velocitas-reply-toggle:hover {
                background: #f1f3f4 !important;
            }

            .velocitas-reply-content {
                display: flex !important;
                flex-direction: column !important;
            }

            .velocitas-reply-messages {
                max-height: 300px !important;
                overflow-y: auto !important;
                padding: 16px !important;
                min-height: 100px !important;
            }

            .velocitas-reply-welcome {
                color: #202124 !important;
                font-size: 13px !important;
            }

            .velocitas-reply-welcome p {
                margin: 8px 0 !important;
            }

            .velocitas-reply-welcome ul {
                margin: 8px 0 !important;
                padding-left: 20px !important;
            }

            .velocitas-reply-welcome li {
                margin: 4px 0 !important;
            }

            .velocitas-reply-message {
                margin-bottom: 16px !important;
                font-size: 13px !important;
            }

            .velocitas-message-header {
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
                margin-bottom: 6px !important;
            }

            .velocitas-message-role {
                font-weight: 500 !important;
                font-size: 12px !important;
            }

            .velocitas-reply-user .velocitas-message-role {
                color: #1a73e8 !important;
            }

            .velocitas-reply-assistant .velocitas-message-role,
            .velocitas-reply-draft .velocitas-message-role {
                color: #34a853 !important;
            }

            .velocitas-message-time {
                font-size: 11px !important;
                color: #5f6368 !important;
            }

            .velocitas-message-content {
                background: #f8f9fa !important;
                padding: 10px 12px !important;
                border-radius: 8px !important;
                line-height: 1.4 !important;
            }

            .velocitas-reply-user .velocitas-message-content {
                background: #e3f2fd !important;
                border: 1px solid #bbdefb !important;
            }

            .velocitas-reply-assistant .velocitas-message-content,
            .velocitas-reply-draft .velocitas-message-content {
                background: #f1f8e9 !important;
                border: 1px solid #c8e6c9 !important;
            }

            .velocitas-draft-content {
                margin-bottom: 12px !important;
                padding: 8px !important;
                background: white !important;
                border: 1px solid #ddd !important;
                border-radius: 4px !important;
                font-style: italic !important;
            }

            .velocitas-draft-actions {
                display: flex !important;
                gap: 8px !important;
                flex-wrap: wrap !important;
            }

            .velocitas-apply-draft,
            .velocitas-edit-draft {
                background: #1a73e8 !important;
                color: white !important;
                border: none !important;
                padding: 6px 12px !important;
                border-radius: 4px !important;
                font-size: 12px !important;
                cursor: pointer !important;
                transition: background-color 0.2s ease !important;
            }

            .velocitas-apply-draft:hover,
            .velocitas-edit-draft:hover {
                background: #1557b0 !important;
            }

            .velocitas-edit-draft {
                background: #34a853 !important;
            }

            .velocitas-edit-draft:hover {
                background: #2d8f47 !important;
            }

            .velocitas-typing-dots {
                display: flex !important;
                gap: 4px !important;
            }

            .velocitas-typing-dots span {
                width: 6px !important;
                height: 6px !important;
                border-radius: 50% !important;
                background: #5f6368 !important;
                animation: velocitas-typing-bounce 1.4s infinite ease-in-out both !important;
            }

            .velocitas-typing-dots span:nth-child(1) { animation-delay: -0.32s !important; }
            .velocitas-typing-dots span:nth-child(2) { animation-delay: -0.16s !important; }

            @keyframes velocitas-typing-bounce {
                0%, 80%, 100% { 
                    transform: scale(0) !important;
                } 40% { 
                    transform: scale(1) !important;
                }
            }

            .velocitas-reply-input-container {
                border-top: 1px solid #e8eaed !important;
                padding: 12px 16px !important;
                display: flex !important;
                gap: 8px !important;
                align-items: flex-end !important;
            }

            .velocitas-reply-input {
                flex: 1 !important;
                border: 1px solid #dadce0 !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-size: 13px !important;
                font-family: inherit !important;
                resize: none !important;
                min-height: 20px !important;
                max-height: 120px !important;
                line-height: 1.4 !important;
            }

            .velocitas-reply-input:focus {
                outline: none !important;
                border-color: #1a73e8 !important;
                box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2) !important;
            }

            .velocitas-reply-send {
                background: #1a73e8 !important;
                color: white !important;
                border: none !important;
                border-radius: 6px !important;
                padding: 8px 12px !important;
                font-size: 14px !important;
                cursor: pointer !important;
                transition: background-color 0.2s ease !important;
                min-width: 40px !important;
                height: 36px !important;
            }

            .velocitas-reply-send:hover {
                background: #1557b0 !important;
            }

            .velocitas-reply-actions {
                padding: 8px 16px 12px 16px !important;
                border-top: 1px solid #f0f0f0 !important;
                display: flex !important;
                gap: 8px !important;
                flex-wrap: wrap !important;
            }

            .velocitas-action-btn {
                background: #f8f9fa !important;
                border: 1px solid #dadce0 !important;
                color: #3c4043 !important;
                padding: 6px 12px !important;
                border-radius: 4px !important;
                font-size: 12px !important;
                cursor: pointer !important;
                transition: all 0.2s ease !important;
                white-space: nowrap !important;
            }

            .velocitas-action-btn:hover {
                background: #e8eaed !important;
                border-color: #bdc1c6 !important;
            }

            .velocitas-action-btn:active {
                background: #dadce0 !important;
            }

            /* Make sure the panel doesn't interfere with Gmail's compose layout */
            .velocitas-reply-panel {
                position: relative !important;
                z-index: 1000 !important;
            }
        `;

        document.head.appendChild(styles);
    }

    // Get status information
    getStatus() {
        return {
            isReplyMode: this.isReplyMode,
            hasOriginalContent: !!this.originalEmailContent,
            isProcessing: this.isProcessing,
            conversationLength: this.conversationHistory.length,
            panelExists: !!this.replyPanel,
            textareaFound: !!this.composeTextarea,
            apiProvider: 'Hack Club AI'
        };
    }

    // Cleanup method
    cleanup() {
        // Remove reply panel
        if (this.replyPanel) {
            this.replyPanel.remove();
            this.replyPanel = null;
        }

        // Remove styles
        const styles = document.getElementById('velocitas-reply-assistant-styles');
        if (styles) {
            styles.remove();
        }

        // Clear state
        this.originalEmailContent = null;
        this.conversationHistory = [];
        this.isProcessing = false;
        this.isReplyMode = false;
        this.composeTextarea = null;
        this.draftContent = '';
        
        console.log('EmailReplyAssistant: Cleanup completed');
    }
}