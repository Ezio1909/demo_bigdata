// Main Application Controller for GitHub Events Dashboard
class GitHubEventsDashboard {
    constructor() {
        this.isInitialized = false;
        this.autoRefreshInterval = null;
        this.currentTimeRange = 24;
        this.isAutoRefreshEnabled = false;
        this.lastUpdateTime = null;
        this.eventSource = null;
    }
    
    // Initialize the dashboard
    async initialize() {
        if (this.isInitialized) return;
        
        try {
            console.log('Initializing GitHub Events Dashboard...');
            
            // Lock UI to 24h
            const hoursBackSelect = document.getElementById('hoursBack');
            if (hoursBackSelect) {
                hoursBackSelect.value = '24';
                hoursBackSelect.disabled = true;
                const label = hoursBackSelect.parentElement?.querySelector('label');
                if (label) label.textContent = 'Time Range: Last 24 Hours';
            }
            const autoRefreshCheckbox = document.getElementById('autoRefresh');
            if (autoRefreshCheckbox) {
                autoRefreshCheckbox.checked = false;
                autoRefreshCheckbox.disabled = true;
            }
            const refreshBtn = document.getElementById('refreshBtn');
            if (refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.textContent = '🔄 Auto (SSE)';
            }
            
            // Initialize components
            chartManager.initializeCharts();
            tableManager.initializeSorting();
            await eventsManager.initialize();
            
            // Load initial pull (fallback) while SSE connects
            await this.loadDashboardData();
            
            // Setup SSE stream
            this.setupSSE();
            
            // No auto-refresh when SSE is used
            this.isInitialized = true;
            console.log('Dashboard initialization complete');
            UTILS.showNotification('Dashboard loaded (SSE enabled)', 'success');
            
        } catch (error) {
            console.error('Dashboard initialization failed:', error);
            APIErrorHandler.handle(error, 'initializing dashboard');
        }
    }

    setupSSE() {
        try {
            if (this.eventSource) {
                this.eventSource.close();
            }
            const streamUrl = `${CONFIG.API_BASE_URL}/stream`;
            const es = new EventSource(streamUrl);
            this.eventSource = es;
            
            es.onopen = () => {
                console.log('SSE connected');
                updateConnectionStatus(true);
            };
            
            es.onerror = (e) => {
                console.warn('SSE error', e);
                updateConnectionStatus(false);
            };
            
            es.onmessage = (evt) => {
                try {
                    const stats = JSON.parse(evt.data);
                    if (!stats) return;
                    this.updateOverviewCards(stats);
                    chartManager.updateCharts(stats);
                    tableManager.updateTables(stats);
                    this.lastUpdateTime = new Date();
                    updateConnectionStatus(true);
                } catch (err) {
                    console.error('Failed to parse SSE payload', err);
                }
            };
        } catch (err) {
            console.error('Failed to setup SSE', err);
        }
    }

    // Load all dashboard data (one-shot pull)
    async loadDashboardData() {
        try {
            const stats = await api.getDashboardStats(24);
            if (stats) {
                this.updateOverviewCards(stats);
                chartManager.updateCharts(stats);
                tableManager.updateTables(stats);
                this.lastUpdateTime = new Date();
                updateConnectionStatus(true);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            APIErrorHandler.handle(error, 'loading dashboard data');
        }
    }
    
    // Update overview cards with statistics
    updateOverviewCards(stats) {
        try {
            document.getElementById('totalEvents').textContent = 
                UTILS.formatNumber(stats.total_events);
            
            document.getElementById('uniqueRepos').textContent = 
                UTILS.formatNumber(stats.unique_repositories);
            
            document.getElementById('uniqueActors').textContent = 
                UTILS.formatNumber(stats.unique_actors);
            
            document.getElementById('eventTypesCount').textContent = 
                UTILS.formatNumber(stats.event_types_count);
                
        } catch (error) {
            console.error('Error updating overview cards:', error);
        }
    }
    
    // Disable auto refresh related features in SSE mode
    setupAutoRefresh() { /* no-op in SSE mode */ }
    updateTimeRange() { /* locked to 24h */ }
    toggleAutoRefresh() { /* locked off in SSE mode */ }
    
    // Setup event listeners
    setupEventListeners() {
        // Time range selector
        const hoursBackSelect = document.getElementById('hoursBack');
        if (hoursBackSelect) {
            hoursBackSelect.addEventListener('change', (e) => {
                this.updateTimeRange(parseInt(e.target.value));
            });
        }
        
        // Auto-refresh toggle
        const autoRefreshCheckbox = document.getElementById('autoRefresh');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.addEventListener('change', (e) => {
                this.toggleAutoRefresh(e.target.checked);
            });
        }
        
        // Window focus/blur for pausing refresh
        window.addEventListener('focus', () => {
            if (this.isAutoRefreshEnabled) {
                this.setupAutoRefresh();
                this.refreshData();
            }
        });
        
        window.addEventListener('blur', () => {
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
            }
        });
        
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.isAutoRefreshEnabled) {
                this.setupAutoRefresh();
                this.refreshData();
            } else if (document.visibilityState === 'hidden') {
                if (this.autoRefreshInterval) {
                    clearInterval(this.autoRefreshInterval);
                }
            }
        });
        
        // Error modal close
        window.addEventListener('click', (e) => {
            const modal = document.getElementById('errorModal');
            if (e.target === modal) {
                this.closeErrorModal();
            }
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeErrorModal();
            } else if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
                e.preventDefault();
                this.refreshData();
            }
        });
    }
    
    // Check API health
    async checkAPIHealth() {
        try {
            const health = await api.healthCheck();
            console.log('API Health Check:', health);
            
            if (health.status !== 'healthy') {
                UTILS.showNotification('API health check shows issues', 'warning');
            }
            
        } catch (error) {
            console.error('API health check failed:', error);
            UTILS.showNotification('Cannot connect to API server', 'error');
        }
    }
    
    // Refresh all data
    async refreshData() {
        console.log('Refreshing dashboard data...');
        
        try {
            // Show loading state
            const refreshBtn = document.getElementById('refreshBtn');
            if (refreshBtn) {
                refreshBtn.textContent = '🔄 Refreshing...';
                refreshBtn.disabled = true;
            }
            
            // Clear cache to ensure fresh data
            api.clearCache();
            
            // Load fresh data
            await Promise.all([
                this.loadDashboardData(),
                eventsManager.refreshEvents()
            ]);
            
            console.log('Dashboard refresh complete');
            
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            APIErrorHandler.handle(error, 'refreshing dashboard');
        } finally {
            // Reset refresh button
            const refreshBtn = document.getElementById('refreshBtn');
            if (refreshBtn) {
                refreshBtn.textContent = '🔄 Refresh';
                refreshBtn.disabled = false;
            }
        }
    }
    
    // Update time range
    async updateTimeRange(hoursBack) {
        this.currentTimeRange = hoursBack;
        
        // Update events time range
        eventsManager.updateTimeRange(hoursBack);
        
        // Refresh dashboard data
        await this.loadDashboardData();
        
        console.log(`Time range updated to ${hoursBack} hours`);
    }
    
    // Toggle auto-refresh
    toggleAutoRefresh(enabled) {
        this.isAutoRefreshEnabled = enabled;
        this.setupAutoRefresh();
        
        const message = enabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled';
        UTILS.showNotification(message, 'info');
        
        console.log(message);
    }
    
    // Show error modal
    showErrorModal(message) {
        const modal = document.getElementById('errorModal');
        const messageElement = document.getElementById('errorMessage');
        
        if (modal && messageElement) {
            messageElement.textContent = message;
            modal.classList.add('show');
        }
    }
    
    // Close error modal
    closeErrorModal() {
        const modal = document.getElementById('errorModal');
        if (modal) {
            modal.classList.remove('show');
        }
    }
    
    // Handle application errors
    handleError(error, context = '') {
        console.error(`Application error ${context}:`, error);
        
        const message = APIErrorHandler.handle(error, context);
        this.showErrorModal(message);
    }
    
    // Cleanup resources
    destroy() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        chartManager.destroyCharts();
        api.clearCache();
        
        console.log('Dashboard destroyed');
    }
}

// Global dashboard instance
const dashboard = new GitHubEventsDashboard();

// Global functions called from HTML
function updateTimeRange() {
    const hoursBack = document.getElementById('hoursBack').value;
    dashboard.updateTimeRange(parseInt(hoursBack));
}

function refreshData() {
    dashboard.refreshData();
}

function toggleAutoRefresh() {
    const isEnabled = document.getElementById('autoRefresh').checked;
    dashboard.toggleAutoRefresh(isEnabled);
}

function closeErrorModal() {
    dashboard.closeErrorModal();
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    dashboard.initialize();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    dashboard.destroy();
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    dashboard.handleError(event.error, 'global error handler');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    dashboard.handleError(event.reason, 'unhandled promise rejection');
});

// Export dashboard instance for debugging
window.dashboard = dashboard;
