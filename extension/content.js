// Main content script - initializes extension after modules are loaded
(() => {
    'use strict';

    // Prevent multiple initialization
    if (window.VelocitasExtensionInstance) {
        console.log('Velocitas: Already initialized, skipping...');
        return;
    }

    // Initialize the extension
    function initializeExtension() {
        console.log('Velocitas: Checking module availability...');
        console.log('DateHeaderManager available:', !!window.DateHeaderManager);
        console.log('EmailLabeler available:', !!window.EmailLabeler);
        console.log('EmailSummarizer available:', !!window.EmailSummarizer);
        console.log('IndividualEmailSummarizer available:', !!window.IndividualEmailSummarizer);
        console.log('EmailChatbox available:', !!window.EmailChatbox);
        console.log('EmailReplyAssistant available:', !!window.EmailReplyAssistant);
        console.log('VelocitasExtension available:', !!window.VelocitasExtension);
        
        // Check if required classes are available
        if (!window.DateHeaderManager || !window.EmailLabeler || !window.EmailSummarizer || !window.IndividualEmailSummarizer || !window.EmailChatbox || !window.EmailReplyAssistant || !window.VelocitasExtension) {
            console.error('Velocitas: Required modules not loaded');
            console.log('Available window properties:', Object.keys(window).filter(key => key.includes('Velocitas') || key.includes('DateHeader') || key.includes('EmailLabeler') || key.includes('EmailSummarizer') || key.includes('IndividualEmail') || key.includes('EmailChatbox') || key.includes('EmailReply')));
            
            // Retry after a short delay in case modules are still loading
            setTimeout(() => {
                console.log('Velocitas: Retrying initialization...');
                initializeExtension();
            }, 500);
            return;
        }

        try {
            // Create and initialize the extension instance
            console.log('Velocitas: Creating extension instance...');
            window.VelocitasExtensionInstance = new window.VelocitasExtension();
            
            console.log('Velocitas: Initializing extension...');
            window.VelocitasExtensionInstance.init().catch(error => {
                console.error('Velocitas: Failed to initialize:', error);
            });

            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {
                if (window.VelocitasExtensionInstance && window.VelocitasExtensionInstance.cleanup) {
                    window.VelocitasExtensionInstance.cleanup();
                }
            });

            console.log('Velocitas: Extension initialized successfully with AI email labeling, summarization, and chatbox');
        } catch (initError) {
            console.error('Velocitas: Failed to create extension instance:', initError);
        }
    }

    // Wait for DOM to be ready, then initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeExtension);
    } else {
        // DOM is already ready, but give modules a moment to load
        setTimeout(initializeExtension, 100);
    }

    console.log('Velocitas: Content script loaded, waiting for DOM ready...');

})();