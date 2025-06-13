/**
 * Test for DateGrouper functionality
 */

import DateGrouper from '../src/bundling/DateGrouper.js';

describe('DateGrouper', () => {
    let dateGrouper;

    beforeEach(() => {
        dateGrouper = new DateGrouper();
        
        // Mock DOM
        document.body.innerHTML = `
            <div role="main">
                <table>
                    <tbody>
                        <tr class="zA">
                            <td class="xW xY">
                                <span title="Nov 15, 2024, 10:30 AM">Nov 15</span>
                            </td>
                        </tr>
                        <tr class="zA">
                            <td class="xW xY">
                                <span title="Nov 14, 2024, 2:15 PM">Nov 14</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    });

    test('should calculate date thresholds correctly', () => {
        const thresholds = dateGrouper.calculateDateThresholds();
        
        expect(thresholds.today).toBeInstanceOf(Date);
        expect(thresholds.yesterday).toBeInstanceOf(Date);
        expect(thresholds.last7DaysThreshold).toBeInstanceOf(Date);
        expect(thresholds.last30DaysThreshold).toBeInstanceOf(Date);
    });

    test('should categorize dates correctly', () => {
        const thresholds = dateGrouper.calculateDateThresholds();
        const today = new Date().toISOString().split('T')[0];
        
        expect(dateGrouper.categorizeDate(today, thresholds)).toBe('Today');
    });

    test('should clear existing groups', () => {
        // Add a mock header
        document.body.innerHTML += '<tr class="velocitas-date-group-header"><td>Test Header</td></tr>';
        
        dateGrouper.clearExistingGroups();
        
        const headers = document.querySelectorAll('.velocitas-date-group-header');
        expect(headers.length).toBe(0);
    });
});