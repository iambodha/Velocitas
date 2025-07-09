// EmailChatbox.js - Email Q&A chatbox module
window.EmailChatbox = class EmailChatbox {
    constructor() {
        this.apiUrl = 'https://ai.hackclub.com/chat/completions';
        this.chatPanel = null;
        this.currentEmailContent = null;
        this.isProcessing = false;
        this.chatHistory = [];
        this.maxRetries = 3;
        this.retryDelay = 1000;
        this.maxHistoryLength = 20; // Keep last 20 messages
    }

    // Initialize the email chatbox
    async init() {
        console.log('EmailChatbox: Initializing...');
        
        // Wait a bit for other components to load
        setTimeout(() => {
            console.log('EmailChatbox: Setting up chatbox...');
            this.createChatPanel();
            console.log('EmailChatbox: Initialized successfully');
        }, 3500); // Wait a bit longer than individual summarizer
    }

    // Set the current email content for the chatbox
    setEmailContent(emailContent) {
        console.log('EmailChatbox: Email content updated');
        this.currentEmailContent = emailContent;
        this.chatHistory = []; // Clear chat history when email changes
        this.clearChatMessages();
        this.showEmailLoadedState();
    }

    // Clear email content (when not in email view)
    clearEmailContent() {
        console.log('EmailChatbox: Email content cleared');
        this.currentEmailContent = null;
        this.chatHistory = [];
        this.showNoEmailState();
    }

    // Create the chat panel
    createChatPanel() {
        // Find the individual summary panel to insert the chat below it
        const summaryPanel = document.getElementById('velocitas-individual-summary-panel');
        
        if (!summaryPanel) {
            console.warn('EmailChatbox: Could not find individual summary panel, looking for sidebar');
            // Fallback: find the Gmail sidebar
            const labelSection = document.querySelector('.nM') ||
                                document.querySelector('[aria-label="Labels"]') ||
                                document.querySelector('.yJ');
            
            if (!labelSection) {
                console.warn('EmailChatbox: Could not find Gmail sidebar');
                return;
            }
            
            // Create the chat panel and insert after labels
            this.createChatPanelElement();
            labelSection.parentNode.insertBefore(this.chatPanel, labelSection.nextSibling);
        } else {
            // Insert chat panel after the summary panel
            this.createChatPanelElement();
            summaryPanel.parentNode.insertBefore(this.chatPanel, summaryPanel.nextSibling);
        }

        // Add styles
        this.addChatStyles();
        console.log('EmailChatbox: Chat panel created');
    }

    // Create the chat panel element
    createChatPanelElement() {
        this.chatPanel = document.createElement('div');
        this.chatPanel.id = 'velocitas-email-chatbox';
        this.chatPanel.className = 'velocitas-chat-panel';
        this.chatPanel.innerHTML = `
            <div class="velocitas-chat-header">
                <h3>Email Chatbot</h3>
                <div class="velocitas-chat-controls">
                    <button class="velocitas-chat-clear" aria-label="Clear chat history" title="Clear chat">🗑️</button>
                    <button class="velocitas-chat-toggle" aria-label="Toggle chat panel">−</button>
                </div>
            </div>
            <div class="velocitas-chat-content">
                <div class="velocitas-chat-messages" id="velocitas-chat-messages">
                    <div class="velocitas-chat-placeholder">
                        <p>Click on an email to start asking questions about it</p>
                    </div>
                </div>
                <div class="velocitas-chat-input-container">
                    <textarea 
                        id="velocitas-chat-input" 
                        class="velocitas-chat-input" 
                        placeholder="Ask a question about this email..."
                        rows="2"
                        disabled
                    ></textarea>
                    <button 
                        id="velocitas-chat-send" 
                        class="velocitas-chat-send"
                        aria-label="Send message"
                        disabled
                    >
                        ➤
                    </button>
                </div>
            </div>
        `;

        // Add event listeners
        this.setupEventListeners();
    }

    // Setup event listeners for the chat panel
    setupEventListeners() {
        // Toggle button
        const toggleBtn = this.chatPanel.querySelector('.velocitas-chat-toggle');
        const content = this.chatPanel.querySelector('.velocitas-chat-content');
        
        if (!toggleBtn || !content) {
            console.error('EmailChatbox: Toggle button or content not found!', {
                toggleBtn: !!toggleBtn,
                content: !!content,
                chatPanel: !!this.chatPanel
            });
            return;
        }
        
        console.log('EmailChatbox: Setting up toggle button event listener');
        
        toggleBtn.addEventListener('click', () => {
            const isCollapsed = content.style.display === 'none';
            content.style.display = isCollapsed ? 'block' : 'none';
            toggleBtn.textContent = isCollapsed ? '−' : '+';
            toggleBtn.setAttribute('aria-label', isCollapsed ? 'Collapse chat panel' : 'Expand chat panel');
        });

        // Clear chat button
        const clearBtn = this.chatPanel.querySelector('.velocitas-chat-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                console.log('EmailChatbox: Clear button clicked');
                this.clearChatHistory();
            });
        } else {
            console.error('EmailChatbox: Clear button not found!');
        }

        // Send button
        const sendBtn = this.chatPanel.querySelector('#velocitas-chat-send');
        const inputTextarea = this.chatPanel.querySelector('#velocitas-chat-input');
        
        if (sendBtn && inputTextarea) {
            sendBtn.addEventListener('click', () => {
                this.sendMessage();
            });

            // Enter key handling (Shift+Enter for new line, Enter to send)
            inputTextarea.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea
            inputTextarea.addEventListener('input', () => {
                this.autoResizeTextarea(inputTextarea);
            });
        } else {
            console.error('EmailChatbox: Send button or input textarea not found!', {
                sendBtn: !!sendBtn,
                inputTextarea: !!inputTextarea
            });
        }
        
        console.log('EmailChatbox: All event listeners set up successfully');
    }

    // Auto-resize textarea based on content
    autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        const maxHeight = 120; // Max 5 lines approximately
        const newHeight = Math.min(textarea.scrollHeight, maxHeight);
        textarea.style.height = newHeight + 'px';
    }

    // Send a message
    async sendMessage() {
        const inputTextarea = this.chatPanel.querySelector('#velocitas-chat-input');
        const message = inputTextarea.value.trim();
        
        if (!message || !this.currentEmailContent || this.isProcessing) {
            return;
        }

        // Add user message to chat
        this.addMessageToChat('user', message);
        
        // Clear input
        inputTextarea.value = '';
        inputTextarea.style.height = 'auto';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            // Generate AI response
            const response = await this.generateChatResponse(message);
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            // Add AI response to chat
            this.addMessageToChat('assistant', response);
            
        } catch (error) {
            console.error('EmailChatbox: Error generating response:', error);
            this.removeTypingIndicator();
            this.addMessageToChat('assistant', '❌ Sorry, I encountered an error while processing your question. Please try again.');
        }
    }

    // Generate AI response using the email content and chat history
    async generateChatResponse(userMessage, retryCount = 0) {
        if (this.isProcessing) {
            throw new Error('Already processing a message');
        }

        this.isProcessing = true;

        try {
            // Add user message to history
            this.chatHistory.push({
                role: 'user',
                content: userMessage
            });

            // Keep history manageable
            if (this.chatHistory.length > this.maxHistoryLength) {
                this.chatHistory = this.chatHistory.slice(-this.maxHistoryLength);
            }

            const messages = this.createChatMessages();
            
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
            this.chatHistory.push({
                role: 'assistant',
                content: aiResponse
            });

            return aiResponse;

        } catch (error) {
            console.error('EmailChatbox: API call failed:', error);
            
            if (retryCount < this.maxRetries) {
                console.log(`EmailChatbox: Retrying (${retryCount + 1}/${this.maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                return this.generateChatResponse(userMessage, retryCount + 1);
            }
            
            throw error;
        } finally {
            this.isProcessing = false;
        }
    }

    // Create messages array for the API call
    createChatMessages() {
        const systemPrompt = this.createSystemPrompt();
        const messages = [
            {
                role: 'system',
                content: systemPrompt
            }
        ];

        // Add chat history
        messages.push(...this.chatHistory);

        return messages;
    }

    // Create system prompt with email context
    createSystemPrompt() {
        return `You are an intelligent email assistant helping users understand and work with their emails. You have access to the current email content and can answer questions about it.

CURRENT EMAIL CONTEXT:
Subject: ${this.currentEmailContent?.subject || 'No subject'}
From: ${this.currentEmailContent?.sender || 'Unknown sender'}
Date: ${this.currentEmailContent?.date || 'Unknown date'}
${this.currentEmailContent?.attachments?.length > 0 ? `Attachments: ${this.currentEmailContent.attachments.map(a => a.name).join(', ')}` : ''}

Email Content:
${this.currentEmailContent?.body || 'No content available'}

INSTRUCTIONS:
- Answer questions specifically about this email
- Be helpful, concise, and accurate
- If asked about information not in the email, clearly state that
- Provide actionable insights when relevant
- Use a friendly, professional tone
- Format your responses with simple HTML when helpful (use <p>, <ul>, <li>, <strong>, <em>)
- If the user asks for summaries or key points, be specific to this email
- Help with understanding context, next steps, or implications

You are having a conversation with the user about this specific email. Answer their questions helpfully and accurately.`;
    }

    // Add a message to the chat display
    addMessageToChat(role, content) {
        const messagesContainer = this.chatPanel.querySelector('#velocitas-chat-messages');
        const placeholder = messagesContainer.querySelector('.velocitas-chat-placeholder');
        
        // Remove placeholder if it exists
        if (placeholder) {
            placeholder.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `velocitas-chat-message velocitas-chat-${role}`;
        
        const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        messageDiv.innerHTML = `
            <div class="velocitas-message-header">
                <span class="velocitas-message-role">${role === 'user' ? 'You' : 'AI Assistant'}</span>
                <span class="velocitas-message-time">${timestamp}</span>
            </div>
            <div class="velocitas-message-content">${this.formatMessageContent(content)}</div>
        `;

        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Format message content (preserve HTML for AI responses, escape for user messages)
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
        const messagesContainer = this.chatPanel.querySelector('#velocitas-chat-messages');
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'velocitas-chat-message velocitas-chat-assistant velocitas-typing-indicator';
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
        const typingIndicator = this.chatPanel.querySelector('#velocitas-typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    // Clear chat messages
    clearChatMessages() {
        const messagesContainer = this.chatPanel.querySelector('#velocitas-chat-messages');
        messagesContainer.innerHTML = `
            <div class="velocitas-chat-placeholder">
                <p>Click on an email to start asking questions about it</p>
            </div>
        `;
    }

    // Clear chat history
    clearChatHistory() {
        this.chatHistory = [];
        this.clearChatMessages();
        
        if (this.currentEmailContent) {
            this.showEmailLoadedState();
        }
    }

    // Show state when email is loaded
    showEmailLoadedState() {
        const messagesContainer = this.chatPanel.querySelector('#velocitas-chat-messages');
        const inputTextarea = this.chatPanel.querySelector('#velocitas-chat-input');
        const sendBtn = this.chatPanel.querySelector('#velocitas-chat-send');
        
        messagesContainer.innerHTML = `
            <div class="velocitas-chat-welcome">
                <p><strong>Email loaded!</strong> You can now ask questions about:</p>
                <ul>
                    <li>Key points and summary</li>
                    <li>Action items and deadlines</li>
                    <li>Context and background</li>
                    <li>Specific details or clarifications</li>
                    <li>Suggested responses</li>
                </ul>
                <p><em>Try asking: "What are the main action items?" or "What is this email about?"</em></p>
            </div>
        `;
        
        // Enable input
        inputTextarea.disabled = false;
        sendBtn.disabled = false;
        inputTextarea.placeholder = "Ask a question about this email...";
    }

    // Show state when no email is available
    showNoEmailState() {
        const messagesContainer = this.chatPanel.querySelector('#velocitas-chat-messages');
        const inputTextarea = this.chatPanel.querySelector('#velocitas-chat-input');
        const sendBtn = this.chatPanel.querySelector('#velocitas-chat-send');
        
        this.clearChatMessages();
        
        // Disable input
        inputTextarea.disabled = true;
        sendBtn.disabled = true;
        inputTextarea.placeholder = "Open an email to start chatting...";
        inputTextarea.value = '';
    }

    // Add styles for the chat panel
    addChatStyles() {
        if (document.getElementById('velocitas-email-chatbox-styles')) {
            return;
        }

        const styles = document.createElement('style');
        styles.id = 'velocitas-email-chatbox-styles';
        styles.textContent = `
            .velocitas-chat-panel {
                background: #ffffff !important;
                border: 1px solid #e8eaed !important;
                border-radius: 8px !important;
                margin: 12px 0 !important;
                font-family: 'Google Sans', Roboto, Arial, sans-serif !important;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
                overflow: hidden !important;
            }

            .velocitas-chat-header {
                background: #f8f9fa !important;
                border-bottom: 1px solid #e8eaed !important;
                padding: 12px 16px !important;
                display: flex !important;
                justify-content: space-between !important;
                align-items: center !important;
            }

            .velocitas-chat-header h3 {
                margin: 0 !important;
                font-size: 14px !important;
                font-weight: 500 !important;
                color: #202124 !important;
            }

            .velocitas-chat-controls {
                display: flex !important;
                gap: 8px !important;
            }

            .velocitas-chat-clear,
            .velocitas-chat-toggle {
                background: transparent !important;
                border: none !important;
                color: #5f6368 !important;
                font-size: 14px !important;
                cursor: pointer !important;
                padding: 4px 8px !important;
                border-radius: 4px !important;
                transition: background-color 0.2s ease !important;
            }

            .velocitas-chat-clear:hover,
            .velocitas-chat-toggle:hover {
                background: #f1f3f4 !important;
            }

            .velocitas-chat-content {
                display: flex !important;
                flex-direction: column !important;
                height: 400px !important;
            }

            .velocitas-chat-messages {
                flex: 1 !important;
                overflow-y: auto !important;
                padding: 16px !important;
                max-height: 320px !important;
            }

            .velocitas-chat-placeholder {
                text-align: center !important;
                color: #5f6368 !important;
                padding: 20px !important;
            }

            .velocitas-chat-placeholder p {
                margin: 0 !important;
                font-style: italic !important;
                font-size: 13px !important;
            }

            .velocitas-chat-welcome {
                color: #202124 !important;
                font-size: 13px !important;
            }

            .velocitas-chat-welcome p {
                margin: 8px 0 !important;
            }

            .velocitas-chat-welcome ul {
                margin: 8px 0 !important;
                padding-left: 20px !important;
            }

            .velocitas-chat-welcome li {
                margin: 4px 0 !important;
            }

            .velocitas-chat-message {
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

            .velocitas-chat-user .velocitas-message-role {
                color: #1a73e8 !important;
            }

            .velocitas-chat-assistant .velocitas-message-role {
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

            .velocitas-chat-user .velocitas-message-content {
                background: #e3f2fd !important;
                border: 1px solid #bbdefb !important;
            }

            .velocitas-chat-assistant .velocitas-message-content {
                background: #f1f8e9 !important;
                border: 1px solid #c8e6c9 !important;
            }

            .velocitas-message-content p {
                margin: 6px 0 !important;
            }

            .velocitas-message-content p:first-child {
                margin-top: 0 !important;
            }

            .velocitas-message-content p:last-child {
                margin-bottom: 0 !important;
            }

            .velocitas-message-content ul {
                margin: 6px 0 !important;
                padding-left: 16px !important;
            }

            .velocitas-message-content li {
                margin: 2px 0 !important;
            }

            .velocitas-typing-indicator .velocitas-message-content {
                padding: 10px 12px !important;
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

            .velocitas-chat-input-container {
                border-top: 1px solid #e8eaed !important;
                padding: 12px 16px !important;
                display: flex !important;
                gap: 8px !important;
                align-items: flex-end !important;
            }

            .velocitas-chat-input {
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

            .velocitas-chat-input:focus {
                outline: none !important;
                border-color: #1a73e8 !important;
                box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2) !important;
            }

            .velocitas-chat-input:disabled {
                background: #f8f9fa !important;
                color: #5f6368 !important;
                cursor: not-allowed !important;
            }

            .velocitas-chat-send {
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

            .velocitas-chat-send:hover:not(:disabled) {
                background: #1557b0 !important;
            }

            .velocitas-chat-send:disabled {
                background: #dadce0 !important;
                cursor: not-allowed !important;
            }
        `;

        document.head.appendChild(styles);
    }

    // Get status information
    getStatus() {
        return {
            hasEmailContent: !!this.currentEmailContent,
            isProcessing: this.isProcessing,
            chatHistoryLength: this.chatHistory.length,
            panelExists: !!this.chatPanel,
            apiProvider: 'Hack Club AI'
        };
    }

    // Cleanup method
    cleanup() {
        // Remove chat panel
        if (this.chatPanel) {
            this.chatPanel.remove();
            this.chatPanel = null;
        }

        // Remove styles
        const styles = document.getElementById('velocitas-email-chatbox-styles');
        if (styles) {
            styles.remove();
        }

        // Clear state
        this.currentEmailContent = null;
        this.chatHistory = [];
        this.isProcessing = false;
        
        console.log('EmailChatbox: Cleanup completed');
    }
}