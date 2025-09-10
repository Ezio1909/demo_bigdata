// API Client for GitHub Events Dashboard
class GitHubEventsAPI {
    constructor(baseUrl = CONFIG.API_BASE_URL) {
        this.baseUrl = baseUrl;
        this.cache = new Map();
        this.retryCount = 0;
    }
    
    // Generic API request method
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const method = (options.method || 'GET').toUpperCase();
        const headers = { ...(options.headers || {}) };
        // Avoid forcing Content-Type on GET to prevent CORS preflight
        if (method !== 'GET' && !headers['Content-Type'] && options.body) {
            headers['Content-Type'] = 'application/json';
        }
        const requestOptions = { method, headers, ...options };
        
        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.retryCount = 0; // Reset retry count on success
            return data;
            
        } catch (error) {
            console.error(`API request failed: ${url}`, error);
            
            // Retry logic for network errors
            if (this.retryCount < CONFIG.MAX_RETRIES && this.isNetworkError(error)) {
                this.retryCount++;
                console.log(`Retrying request (${this.retryCount}/${CONFIG.MAX_RETRIES})...`);
                
                await this.delay(CONFIG.RETRY_DELAY * this.retryCount);
                return this.request(endpoint, options);
            }
            
            throw error;
        }
    }
    
    // Check if error is a network error (worth retrying)
    isNetworkError(error) {
        return error.name === 'TypeError' || 
               error.message.includes('fetch') ||
               error.message.includes('network');
    }
    
    // Delay utility for retries
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Get cached data if available and not expired
    getCachedData(key) {
        const cached = this.cache.get(key);
        if (cached && (Date.now() - cached.timestamp) < CONFIG.CACHE_DURATION) {
            return cached.data;
        }
        return null;
    }
    
    // Set cached data
    setCachedData(key, data) {
        this.cache.set(key, {
            data,
            timestamp: Date.now()
        });
    }
    
    // Health check
    async healthCheck() {
        return this.request('/health');
    }
    
    // Get dashboard statistics
    async getDashboardStats(hoursBack = 24) {
        const cacheKey = `stats-${hoursBack}`;
        const cached = this.getCachedData(cacheKey);
        
        if (cached) {
            return cached;
        }
        
        // Directly target query service endpoints
        const data = await this.request(`/stats?hours_back=${hoursBack}`);
        this.setCachedData(cacheKey, data);
        return data;
    }
    
    // Get events with filtering and pagination
    async getEvents(params = {}) {
        const queryParams = new URLSearchParams();
        
        // Add non-null parameters to query string
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined && value !== '') {
                queryParams.append(key, value);
            }
        });
        
        const cacheKey = `events-${queryParams.toString()}`;
        const cached = this.getCachedData(cacheKey);
        
        if (cached) {
            return cached;
        }
        
        // Directly target query service endpoints
        const data = await this.request(`/events?${queryParams.toString()}`);
        this.setCachedData(cacheKey, data);
        return data;
    }
    
    // Get available event types
    async getEventTypes(hoursBack = CONFIG.DEFAULT_TIME_RANGE) {
        const cacheKey = `event-types-${hoursBack}`;
        const cached = this.getCachedData(cacheKey);
        if (cached) return cached;
        const stats = await this.getDashboardStats(hoursBack);
        const types = (stats?.event_type_stats || []).map(s => s.event_type).filter(Boolean);
        this.setCachedData(cacheKey, types);
        return types;
    }
    
    // Get available event categories
    async getEventCategories(hoursBack = CONFIG.DEFAULT_TIME_RANGE) {
        const cacheKey = `event-categories-${hoursBack}`;
        const cached = this.getCachedData(cacheKey);
        if (cached) return cached;
        const stats = await this.getDashboardStats(hoursBack);
        const cats = (stats?.event_category_stats || []).map(s => s.event_category).filter(Boolean);
        this.setCachedData(cacheKey, cats);
        return cats;
    }
    
    // Clear cache
    clearCache() {
        this.cache.clear();
    }
    
    // Clear expired cache entries
    clearExpiredCache() {
        const now = Date.now();
        for (const [key, value] of this.cache.entries()) {
            if ((now - value.timestamp) >= CONFIG.CACHE_DURATION) {
                this.cache.delete(key);
            }
        }
    }
}

// API Error Handler
class APIErrorHandler {
    static handle(error, context = '') {
        console.error(`API Error ${context}:`, error);
        
        let userMessage = 'An unexpected error occurred';
        
        if (error.message.includes('Failed to fetch')) {
            userMessage = 'Unable to connect to the server. Please check your connection.';
        } else if (error.message.includes('HTTP 404')) {
            userMessage = 'The requested data was not found.';
        } else if (error.message.includes('HTTP 500')) {
            userMessage = 'Server error. Please try again later.';
        } else if (error.message.includes('HTTP 503')) {
            userMessage = 'Service temporarily unavailable. Please try again later.';
        } else if (error.message) {
            userMessage = error.message;
        }
        
        // Show error notification
        UTILS.showNotification(userMessage, 'error');
        
        // Update connection status
        updateConnectionStatus(false);
        
        return userMessage;
    }
}

// Connection Status Management
function updateConnectionStatus(isConnected) {
    const statusElement = document.getElementById('connectionStatus');
    const lastUpdateElement = document.getElementById('lastUpdate');
    
    if (isConnected) {
        statusElement.className = 'status-connected';
        statusElement.textContent = '●';
        lastUpdateElement.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } else {
        statusElement.className = 'status-disconnected';
        statusElement.textContent = '●';
        lastUpdateElement.textContent = 'Connection lost';
    }
}

// Create global API instance
const api = new GitHubEventsAPI();

// Periodic cache cleanup
setInterval(() => {
    api.clearExpiredCache();
}, CONFIG.CACHE_DURATION);
