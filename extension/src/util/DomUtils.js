/**
 * Utility functions for DOM manipulation and email data extraction
 */

class DomUtils {
    /**
     * Convert HTML string to DOM element
     */
    static htmlToElement(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstChild;
    }

    /**
     * Extract date from Gmail email row
     */
    static extractDate(emailRow) {
        const dateSelectors = [
            'td.xW.xY span[title]',
            'span[title*=":"]',
            '.xW span[title]',
            '.xY span[title]',
            'td span[title]'
        ];
        
        for (const selector of dateSelectors) {
            const dateElement = emailRow.querySelector(selector);
            if (dateElement && dateElement.title) {
                return dateElement.title;
            }
        }
        
        return null;
    }

    /**
     * Extract sender from Gmail email row
     */
    static extractSender(emailRow) {
        const senderSelectors = [
            '.yW',
            '.go span[email]',
            '.yX span[email]',
            'span[email]'
        ];
        
        for (const selector of senderSelectors) {
            const senderElement = emailRow.querySelector(selector);
            if (senderElement) {
                return senderElement.textContent || senderElement.getAttribute('email');
            }
        }
        
        return 'Unknown Sender';
    }

    /**
     * Extract subject from Gmail email row
     */
    static extractSubject(emailRow) {
        const subjectSelectors = [
            '.bog',
            '.yW + .xX .xW',
            '.y6 span[id]'
        ];
        
        for (const selector of subjectSelectors) {
            const subjectElement = emailRow.querySelector(selector);
            if (subjectElement) {
                return subjectElement.textContent.trim();
            }
        }
        
        return 'No Subject';
    }

    /**
     * Check if email row is unread
     */
    static isUnread(emailRow) {
        return emailRow.classList.contains('zE');
    }

    /**
     * Check if email row is starred
     */
    static isStarred(emailRow) {
        return emailRow.querySelector('.T-KT-Jp') !== null;
    }

    /**
     * Get Gmail email rows with multiple fallback selectors
     */
    static getGmailEmailRows() {
        const possibleSelectors = [
            'tr[jsmodel]',
            'tr[role="row"]',
            'tr.zA',
            'div[role="main"] tr.zA',
            '[role="main"] tr[jsmodel]',
            '[data-thread-perm-id]',
            'tr[data-thread-id]',
            '[role="main"] tbody tr',
            '[role="main"] tr'
        ];
        
        for (const selector of possibleSelectors) {
            try {
                const rows = document.querySelectorAll(selector);
                if (rows.length > 0) {
                    // Validate that these look like email rows
                    const firstRow = rows[0];
                    const hasEmailIndicators = firstRow.querySelector('span[email]') || 
                                             firstRow.querySelector('[data-hovercard-id]') ||
                                             firstRow.querySelector('.yW') ||
                                             firstRow.querySelector('.bog') ||
                                             firstRow.textContent.includes('@') ||
                                             firstRow.querySelector('td.xY');
                    
                    if (hasEmailIndicators) {
                        return rows;
                    }
                }
            } catch (error) {
                console.warn(`Velocitas: Error with selector ${selector}:`, error);
            }
        }
        
        return [];
    }

    /**
     * Get the container for email rows
     */
    static getEmailContainer(emailRows) {
        if (!emailRows || !emailRows.length) return null;
        
        let container = emailRows[0].closest('tbody');
        if (!container) {
            container = emailRows[0].closest('table');
        }
        if (!container) {
            container = emailRows[0].parentElement;
        }
        
        return container;
    }
}

export default DomUtils;