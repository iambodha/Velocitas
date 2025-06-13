/**
 * BundleToggler - handles opening and closing of email bundles
 */

import { VelocitasClasses } from '../util/Constants.js';

class BundleToggler {
    constructor(bundledMail) {
        this.bundledMail = bundledMail;
        this.toggleBundle = this.toggleBundle.bind(this);
    }

    toggleBundle(label) {
        const bundle = this.bundledMail.getBundle(label);
        if (!bundle) {
            console.warn(`Velocitas: Bundle with label "${label}" not found`);
            return;
        }

        // Close other bundles first
        this.closeAllBundles();

        // Toggle the selected bundle
        const isOpen = bundle.toggle();
        
        if (isOpen) {
            this.bundledMail.setOpenBundle(label);
            this.updateBundleRowAppearance(bundle, true);
        } else {
            this.bundledMail.setOpenBundle(null);
            this.updateBundleRowAppearance(bundle, false);
        }

        console.log(`Velocitas: Bundle "${label}" ${isOpen ? 'opened' : 'closed'}`);
    }

    openBundle(label) {
        const bundle = this.bundledMail.getBundle(label);
        if (!bundle) return;

        this.closeAllBundles();
        bundle.open();
        this.bundledMail.setOpenBundle(label);
        this.updateBundleRowAppearance(bundle, true);
    }

    closeBundle(label) {
        const bundle = this.bundledMail.getBundle(label);
        if (!bundle) return;

        bundle.close();
        if (this.bundledMail.getLabelOfOpenedBundle() === label) {
            this.bundledMail.setOpenBundle(null);
        }
        this.updateBundleRowAppearance(bundle, false);
    }

    closeAllBundles() {
        const bundles = this.bundledMail.getAllBundles();
        bundles.forEach(bundle => {
            bundle.close();
            this.updateBundleRowAppearance(bundle, false);
        });
        this.bundledMail.setOpenBundle(null);
    }

    updateBundleRowAppearance(bundle, isOpen) {
        const bundleRow = bundle.getBundleRow();
        if (!bundleRow) return;

        const toggleIcon = bundleRow.querySelector('.bundle-toggle-icon');
        const viewAllLink = bundleRow.querySelector(`.${VelocitasClasses.VIEW_ALL_LINK}`);
        
        if (toggleIcon) {
            toggleIcon.textContent = isOpen ? '▼' : '▶';
        }

        if (viewAllLink) {
            viewAllLink.textContent = isOpen ? 'Hide emails' : `View all ${bundle.getMessageCount()} emails`;
        }

        // Update bundle row styling
        if (isOpen) {
            bundleRow.classList.add('bundle-open');
        } else {
            bundleRow.classList.remove('bundle-open');
        }
    }
}

export default BundleToggler;