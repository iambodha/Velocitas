/**
 * Bundle container - represents a group of related emails
 */

import DomUtils from '../util/DomUtils.js';

class Bundle {
    constructor(label) {
        this.label = label;
        this.messages = [];
        this.bundleRow = null;
        this.order = 0;
        this.isOpen = false;
    }

    getLabel() {
        return this.label;
    }

    addMessage(message) {
        this.messages.push(message);
    }

    getMessages() {
        return this.messages;
    }

    getMessageCount() {
        return this.messages.length;
    }

    setBundleRow(bundleRow) {
        this.bundleRow = bundleRow;
    }

    getBundleRow() {
        return this.bundleRow;
    }

    setOrder(order) {
        this.order = order;
    }

    getOrder() {
        return this.order;
    }

    hasUnreadMessages() {
        return this.messages.some(message => DomUtils.isUnread(message));
    }

    getLatestMessage() {
        return this.messages.length > 0 ? this.messages[0] : null;
    }

    getSenders() {
        const senders = new Set();
        this.messages.forEach(message => {
            const sender = DomUtils.extractSender(message);
            senders.add(sender);
        });
        return Array.from(senders);
    }

    open() {
        this.isOpen = true;
        this.messages.forEach(message => {
            message.style.display = '';
        });
    }

    close() {
        this.isOpen = false;
        this.messages.forEach(message => {
            message.style.display = 'none';
        });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
        return this.isOpen;
    }
}

export default Bundle;