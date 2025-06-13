/**
 * Constants used throughout the Velocitas extension
 */

export const VelocitasClasses = {
    VELOCITAS: 'velocitas-modern-theme',
    DATE_GROUP_HEADER: 'velocitas-date-group-header',
    BUNDLED_MESSAGE: 'velocitas-bundled-message',
    BUNDLE_ROW: 'velocitas-bundle-row',
    VIEW_ALL_LINK: 'velocitas-view-all-link'
};

export const GmailClasses = {
    UNREAD: 'zE',
    STARRED: 'T-KT-Jp',
    SELECTED: 'PE'
};

export const Selectors = {
    MAIN: '[role="main"]',
    EMAIL_ROWS: 'tr[jsmodel], tr[role="row"], tr.zA',
    TABLE_BODY: 'tbody',
    POSSIBLE_MESSAGE_LISTS: '.Cp',
    CHECKBOXES: 'input[type="checkbox"]',
    REFRESH: '[data-tooltip="Refresh"]',
    INBOX_TAB: '[data-tooltip="Inbox"]',
    PAGECHANGING_BUTTONS: '.ar9.T-I-J3'
};

export const TableBodySelectors = {
    MESSAGE_NODES: 'tr.zA, tr[jsmodel]'
};

export const ORDER_INCREMENT = 10;

export const Element = {
    BUNDLE: 'bundle',
    UNBUNDLED_MESSAGE: 'unbundled_message',
    DATE_DIVIDER: 'date_divider'
};

export const DateCategories = {
    TODAY: 'Today',
    YESTERDAY: 'Yesterday',
    LAST_7_DAYS: 'Last 7 days',
    LAST_30_DAYS: 'Last 30 days',
    OLDER: 'Older'
};