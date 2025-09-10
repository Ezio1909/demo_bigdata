// Table Management for GitHub Events Dashboard
class TableManager {
    constructor() {
        this.tables = new Map();
    }
    
    // Update top repositories table
    updateTopRepositoriesTable(repositories) {
        const tableBody = document.querySelector('#topReposTable tbody');
        if (!tableBody || !repositories) return;
        
        // Clear existing rows
        tableBody.innerHTML = '';
        
        if (repositories.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="no-data">No repositories found</td></tr>';
            return;
        }
        
        // Add repository rows
        repositories.forEach(repo => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="repo-info">
                        <strong>${this.escapeHtml(repo.repo_name)}</strong>
                        <div class="repo-id">ID: ${repo.repo_id}</div>
                    </div>
                </td>
                <td>
                    <span class="metric-value">${UTILS.formatNumber(repo.event_count)}</span>
                </td>
                <td>
                    <span class="metric-value">${UTILS.formatNumber(repo.unique_actors)}</span>
                </td>
                <td>
                    <div class="event-types-list">
                        ${repo.event_types.slice(0, 3).map(type => 
                            `<span class="event-type-badge" title="${type}">${UTILS.getEventIcon(type)}</span>`
                        ).join('')}
                        ${repo.event_types.length > 3 ? 
                            `<span class="more-types">+${repo.event_types.length - 3}</span>` : ''
                        }
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        this.tables.set('topRepositories', repositories);
    }
    
    // Update top actors table
    updateTopActorsTable(actors) {
        const tableBody = document.querySelector('#topActorsTable tbody');
        if (!tableBody || !actors) return;
        
        // Clear existing rows
        tableBody.innerHTML = '';
        
        if (actors.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="no-data">No actors found</td></tr>';
            return;
        }
        
        // Add actor rows
        actors.forEach(actor => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>
                    <div class="actor-info">
                        <strong>${this.escapeHtml(actor.actor_login)}</strong>
                        <div class="actor-id">ID: ${actor.actor_id}</div>
                    </div>
                </td>
                <td>
                    <span class="metric-value">${UTILS.formatNumber(actor.event_count)}</span>
                </td>
                <td>
                    <span class="metric-value">${UTILS.formatNumber(actor.repo_count)}</span>
                </td>
                <td>
                    <div class="event-types-list">
                        ${actor.event_types.slice(0, 3).map(type => 
                            `<span class="event-type-badge" title="${type}">${UTILS.getEventIcon(type)}</span>`
                        ).join('')}
                        ${actor.event_types.length > 3 ? 
                            `<span class="more-types">+${actor.event_types.length - 3}</span>` : ''
                        }
                    </div>
                </td>
            `;
            tableBody.appendChild(row);
        });
        
        this.tables.set('topActors', actors);
    }
    
    // Update all tables with dashboard stats
    updateTables(dashboardStats) {
        if (!dashboardStats) return;
        
        try {
            this.updateTopRepositoriesTable(dashboardStats.top_repositories);
            this.updateTopActorsTable(dashboardStats.top_actors);
        } catch (error) {
            console.error('Error updating tables:', error);
        }
    }
    
    // Export table data as CSV
    exportTableAsCSV(tableId) {
        const data = this.tables.get(this.getTableDataKey(tableId));
        if (!data || data.length === 0) {
            UTILS.showNotification('No data to export', 'warning');
            return;
        }
        
        try {
            let csvContent, filename, headers;
            
            if (tableId === 'topReposTable') {
                headers = ['Repository Name', 'Repository ID', 'Event Count', 'Unique Actors', 'Event Types'];
                csvContent = UTILS.generateCSV(data.map(repo => ({
                    'Repository Name': repo.repo_name,
                    'Repository ID': repo.repo_id,
                    'Event Count': repo.event_count,
                    'Unique Actors': repo.unique_actors,
                    'Event Types': repo.event_types.join('; ')
                })), headers);
                filename = `top-repositories-${new Date().toISOString().split('T')[0]}.csv`;
                
            } else if (tableId === 'topActorsTable') {
                headers = ['Actor Login', 'Actor ID', 'Event Count', 'Repository Count', 'Event Types'];
                csvContent = UTILS.generateCSV(data.map(actor => ({
                    'Actor Login': actor.actor_login,
                    'Actor ID': actor.actor_id,
                    'Event Count': actor.event_count,
                    'Repository Count': actor.repo_count,
                    'Event Types': actor.event_types.join('; ')
                })), headers);
                filename = `top-actors-${new Date().toISOString().split('T')[0]}.csv`;
            }
            
            if (csvContent && filename) {
                UTILS.downloadFile(csvContent, filename, 'text/csv');
                UTILS.showNotification('Table exported successfully', 'success');
            }
            
        } catch (error) {
            console.error('Error exporting table:', error);
            UTILS.showNotification('Failed to export table', 'error');
        }
    }
    
    // Get table data key from table ID
    getTableDataKey(tableId) {
        const mapping = {
            'topReposTable': 'topRepositories',
            'topActorsTable': 'topActors'
        };
        return mapping[tableId];
    }
    
    // Escape HTML to prevent XSS
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Add sorting functionality to tables
    addSortingToTable(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        const headers = table.querySelectorAll('th');
        headers.forEach((header, index) => {
            if (header.textContent.trim() === '') return; // Skip empty headers
            
            header.style.cursor = 'pointer';
            header.style.userSelect = 'none';
            header.addEventListener('click', () => {
                this.sortTable(tableId, index);
            });
            
            // Add sort indicator
            const sortIndicator = document.createElement('span');
            sortIndicator.className = 'sort-indicator';
            sortIndicator.innerHTML = ' ↕️';
            header.appendChild(sortIndicator);
        });
    }
    
    // Sort table by column
    sortTable(tableId, columnIndex) {
        const table = document.getElementById(tableId);
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        // Skip if no data rows
        if (rows.length === 0 || rows[0].cells.length === 1) return;
        
        // Determine sort direction
        const header = table.querySelectorAll('th')[columnIndex];
        const currentDirection = header.getAttribute('data-sort-direction') || 'asc';
        const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';
        
        // Clear all sort indicators
        table.querySelectorAll('th').forEach(th => {
            th.removeAttribute('data-sort-direction');
            const indicator = th.querySelector('.sort-indicator');
            if (indicator) indicator.innerHTML = ' ↕️';
        });
        
        // Set new sort direction
        header.setAttribute('data-sort-direction', newDirection);
        const indicator = header.querySelector('.sort-indicator');
        if (indicator) {
            indicator.innerHTML = newDirection === 'asc' ? ' ↑' : ' ↓';
        }
        
        // Sort rows
        rows.sort((a, b) => {
            const aText = a.cells[columnIndex].textContent.trim();
            const bText = b.cells[columnIndex].textContent.trim();
            
            // Try to parse as numbers first
            const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
            const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
            
            if (!isNaN(aNum) && !isNaN(bNum)) {
                return newDirection === 'asc' ? aNum - bNum : bNum - aNum;
            } else {
                return newDirection === 'asc' ? 
                    aText.localeCompare(bText) : 
                    bText.localeCompare(aText);
            }
        });
        
        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // Initialize sorting for all tables
    initializeSorting() {
        this.addSortingToTable('topReposTable');
        this.addSortingToTable('topActorsTable');
    }
}

// Global table manager instance
const tableManager = new TableManager();

// Export table function (called from HTML)
function exportTable(tableId) {
    tableManager.exportTableAsCSV(tableId);
}

// Add CSS for table enhancements
const tableStyles = document.createElement('style');
tableStyles.textContent = `
    .repo-info, .actor-info {
        line-height: 1.4;
    }
    
    .repo-id, .actor-id {
        font-size: 11px;
        color: var(--text-secondary);
        margin-top: 2px;
    }
    
    .metric-value {
        font-weight: 600;
        color: var(--primary-color);
    }
    
    .event-types-list {
        display: flex;
        align-items: center;
        gap: 4px;
        flex-wrap: wrap;
    }
    
    .event-type-badge {
        font-size: 14px;
        opacity: 0.8;
        transition: opacity 0.2s;
    }
    
    .event-type-badge:hover {
        opacity: 1;
    }
    
    .more-types {
        font-size: 11px;
        color: var(--text-secondary);
        background: var(--background-color);
        padding: 2px 6px;
        border-radius: 10px;
        font-weight: 500;
    }
    
    .sort-indicator {
        font-size: 12px;
        opacity: 0.6;
    }
    
    th[data-sort-direction] .sort-indicator {
        opacity: 1;
        color: var(--primary-color);
    }
`;
document.head.appendChild(tableStyles);
