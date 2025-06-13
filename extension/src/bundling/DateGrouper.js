/**
 * Date grouping functionality for organizing emails by date
 */

import { DateCategories, VelocitasClasses } from '../util/Constants.js';
import DomUtils from '../util/DomUtils.js';

class DateGrouper {
    constructor() {
        this.groupMessagesByDate = true;
        this.loadSettings();
    }

    loadSettings() {
        chrome.storage.local.get(['groupMessagesByDate'], (result) => {
            this.groupMessagesByDate = result.groupMessagesByDate !== false;
        });
    }

    /**
     * Group emails by date categories
     */
    groupEmailsByDate() {
        console.log("Velocitas: Attempting to group emails by date.");
        this.clearExistingGroups();

        const emailRows = DomUtils.getGmailEmailRows();
        if (!emailRows.length) {
            console.log("Velocitas: No email rows found to group.");
            return;
        }

        const emailContainer = DomUtils.getEmailContainer(emailRows);
        if (!emailContainer) {
            console.warn("Velocitas: Email container not found.");
            return;
        }

        const dateThresholds = this.calculateDateThresholds();
        let currentGroup = null;

        Array.from(emailRows).forEach(row => {
            const emailDateStr = DomUtils.extractDate(row);
            if (!emailDateStr) {
                console.warn("Velocitas: Could not find date for row:", row);
                return;
            }

            const category = this.categorizeDate(emailDateStr, dateThresholds);
            
            if (category !== currentGroup) {
                this.createDateHeader(emailContainer, row, category);
                currentGroup = category;
            }
        });

        console.log("Velocitas: Email grouping completed.");
    }

    /**
     * Calculate date thresholds for categorization
     */
    calculateDateThresholds() {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        const last7DaysThreshold = new Date(today);
        last7DaysThreshold.setDate(today.getDate() - 6);
        const last30DaysThreshold = new Date(today);
        last30DaysThreshold.setDate(today.getDate() - 29);

        return {
            now,
            today,
            yesterday,
            last7DaysThreshold,
            last30DaysThreshold
        };
    }

    /**
     * Categorize email date into predefined categories
     */
    categorizeDate(emailDateStr, thresholds) {
        let emailDate = new Date(emailDateStr);

        if (isNaN(emailDate.getTime())) {
            // Fallback for relative dates like "Nov 12"
            const simpleDateMatch = emailDateStr.match(/^([a-zA-Z]{3})\s(\d{1,2})$/);
            if (simpleDateMatch) {
                emailDate = new Date(`${simpleDateMatch[0]}, ${thresholds.now.getFullYear()}`);
            }
            if (isNaN(emailDate.getTime())) {
                console.warn("Velocitas: Could not parse date:", emailDateStr);
                return DateCategories.OLDER;
            }
        }

        const emailDateDayOnly = new Date(emailDate.getFullYear(), emailDate.getMonth(), emailDate.getDate());

        if (emailDateDayOnly.getTime() === thresholds.today.getTime()) {
            return DateCategories.TODAY;
        } else if (emailDateDayOnly.getTime() === thresholds.yesterday.getTime()) {
            return DateCategories.YESTERDAY;
        } else if (emailDateDayOnly >= thresholds.last7DaysThreshold) {
            return DateCategories.LAST_7_DAYS;
        } else if (emailDateDayOnly >= thresholds.last30DaysThreshold) {
            return DateCategories.LAST_30_DAYS;
        } else {
            return DateCategories.OLDER;
        }
    }

    /**
     * Create and insert date header
     */
    createDateHeader(emailContainer, beforeRow, category) {
        const headerId = `velocitas-group-${category.replace(/\s+/g, '-')}`;
        
        // Remove existing header with same ID
        const existingHeader = document.getElementById(headerId);
        if (existingHeader) {
            existingHeader.remove();
        }

        const headerElement = document.createElement('tr');
        headerElement.id = headerId;
        headerElement.classList.add(VelocitasClasses.DATE_GROUP_HEADER);
        
        const headerCell = document.createElement('td');
        const colCount = beforeRow.cells.length > 0 ? beforeRow.cells.length : 6;
        headerCell.colSpan = colCount;
        headerCell.textContent = category;
        
        this.styleHeaderCell(headerCell);
        headerElement.appendChild(headerCell);
        
        try {
            emailContainer.insertBefore(headerElement, beforeRow);
            console.log(`Velocitas: Added header for ${category}`);
        } catch (error) {
            console.error("Velocitas: Error inserting header:", error);
        }
    }

    /**
     * Style the header cell
     */
    styleHeaderCell(headerCell) {
        headerCell.style.cssText = `
            background-color: #FFFACD !important;
            color: #4A4A4A !important;
            padding: 8px 18px !important;
            font-weight: bold !important;
            font-size: 13px !important;
            border-top: 1px solid #FFEE58 !important;
            border-bottom: 1px solid #FFEE58 !important;
            pointer-events: none !important;
            user-select: none !important;
        `;
    }

    /**
     * Clear existing date group headers
     */
    clearExistingGroups() {
        const headers = document.querySelectorAll(`.${VelocitasClasses.DATE_GROUP_HEADER}`);
        headers.forEach(header => header.remove());
    }
}

export default DateGrouper;