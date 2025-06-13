/**
 * Observer for Gmail's message list to detect email changes
 */

import { Selectors, VelocitasClasses } from '../util/Constants.js';

class MessageListObserver {
    constructor(callback) {
        this.callback = callback;
        this.observer = null;
        this.debounceTimeout = null;
    }

    observe() {
        const messageList = this.findMessageList();
        
        if (!messageList) {
            console.warn('Velocitas: Could not find message list for observer');
            return;
        }

        const config = {
            childList: true,
            subtree: true,
            attributes: false
        };

        this.observer = new MutationObserver((mutations) => {
            this.debouncedCallback(mutations);
        });

        this.observer.observe(messageList, config);
        console.log('Velocitas: MessageListObserver started');
    }

    findMessageList() {
        const possibleSelectors = [
            Selectors.POSSIBLE_MESSAGE_LISTS,
            Selectors.TABLE_BODY,
            '[role="main"] table',
            '.nH.bkK'
        ];

        for (const selector of possibleSelectors) {
            const element = document.querySelector(selector);
            if (element) {
                return element;
            }
        }

        return null;
    }

    debouncedCallback(mutations) {
        clearTimeout(this.debounceTimeout);
        this.debounceTimeout = setTimeout(() => {
            // Filter mutations to only respond to email-related changes
            const relevantMutations = mutations.filter(mutation => {
                return Array.from(mutation.addedNodes).some(node => 
                    node.nodeType === Node.ELEMENT_NODE && 
                    (node.matches && node.matches('tr') || 
                     node.querySelector && node.querySelector('tr'))
                ) || Array.from(mutation.removedNodes).some(node => 
                    node.nodeType === Node.ELEMENT_NODE && 
                    (node.matches && node.matches('tr') || 
                     node.classList && node.classList.contains(VelocitasClasses.DATE_GROUP_HEADER))
                );
            });

            if (relevantMutations.length > 0) {
                this.callback(relevantMutations);
            }
        }, 500);
    }

    disconnect() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
            console.log('Velocitas: MessageListObserver disconnected');
        }
        
        if (this.debounceTimeout) {
            clearTimeout(this.debounceTimeout);
            this.debounceTimeout = null;
        }
    }
}

export default MessageListObserver;