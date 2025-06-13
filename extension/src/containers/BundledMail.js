/**
 * BundledMail - manages all email bundles and their state
 */

class BundledMail {
    constructor() {
        this.bundles = new Map();
        this.openBundleLabel = null;
        this.currentPageNumber = 1;
    }

    setBundles(bundlesByLabel, pageNumber = 1) {
        this.bundles.clear();
        Object.entries(bundlesByLabel).forEach(([label, bundle]) => {
            this.bundles.set(label, bundle);
        });
        this.currentPageNumber = pageNumber;
    }

    getBundle(label) {
        return this.bundles.get(label);
    }

    getAllBundles() {
        return Array.from(this.bundles.values());
    }

    getBundleCount() {
        return this.bundles.size;
    }

    setOpenBundle(label) {
        this.openBundleLabel = label;
    }

    getLabelOfOpenedBundle() {
        return this.openBundleLabel;
    }

    closeBundle() {
        this.openBundleLabel = null;
    }

    hasOpenBundle() {
        return this.openBundleLabel !== null;
    }

    getCurrentPageNumber() {
        return this.currentPageNumber;
    }

    getBundleLabels() {
        return Array.from(this.bundles.keys());
    }

    getTotalMessageCount() {
        return this.getAllBundles().reduce((total, bundle) => {
            return total + bundle.getMessageCount();
        }, 0);
    }

    getUnreadBundleCount() {
        return this.getAllBundles().filter(bundle => bundle.hasUnreadMessages()).length;
    }

    clear() {
        this.bundles.clear();
        this.openBundleLabel = null;
        this.currentPageNumber = 1;
    }
}

export default BundledMail;