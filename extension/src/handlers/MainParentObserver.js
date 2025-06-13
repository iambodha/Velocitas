/**
 * Observer for Gmail's main container to detect page changes
 */

import { Selectors } from '../util/Constants.js';

class MainParentObserver {
    constructor(callback) {
        this.callback = callback;
        this.observer = null;
    }

    observe() {
        const targetNode = document.querySelector(Selectors.MAIN) || document.body;
        
        if (!targetNode) {
            console.warn('Velocitas: Could not find main container for observer');
            return;
        }

        const config = {
            childList: true,
            subtree: true,
            attributes: false
        };

        this.observer = new MutationObserver((mutations) => {
            // Check if there are significant changes that warrant regrouping
            const hasSignificantChanges = mutations.some(mutation => {
                return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
            });

            if (hasSignificantChanges) {
                this.callback(mutations);
            }
        });

        this.observer.observe(targetNode, config);
        console.log('Velocitas: MainParentObserver started');
    }

    disconnect() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
            console.log('Velocitas: MainParentObserver disconnected');
        }
    }
}

export default MainParentObserver;