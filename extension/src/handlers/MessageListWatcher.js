/**
 * Watcher that coordinates message list observations
 */

import MessageListObserver from './MessageListObserver.js';

class MessageListWatcher {
    constructor(callback) {
        this.callback = callback;
        this.messageListObserver = new MessageListObserver(callback);
        this.isObserving = false;
    }

    observe() {
        if (!this.isObserving) {
            this.messageListObserver.observe();
            this.isObserving = true;
        }
    }

    disconnect() {
        if (this.isObserving) {
            this.messageListObserver.disconnect();
            this.isObserving = false;
        }
    }

    reconnect() {
        this.disconnect();
        // Small delay before reconnecting to allow DOM to settle
        setTimeout(() => {
            this.observe();
        }, 100);
    }
}

export default MessageListWatcher;