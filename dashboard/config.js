// Configuration for the GitHub Events Dashboard
const CONFIG = {
    // API Configuration
    // Direct to query service (bypass Nginx, uses CORS)
    API_BASE_URL: 'http://localhost:8003',
    
    // Refresh Configuration
    AUTO_REFRESH_INTERVAL: 1000, // 10 seconds
    
    // Chart Configuration
    CHART_COLORS: {
        primary: '#2563eb',
        secondary: '#64748b',
        success: '#059669',
        warning: '#d97706',
        error: '#dc2626',
        info: '#0891b2',
        purple: '#7c3aed',
        pink: '#db2777',
        orange: '#ea580c',
        teal: '#0d9488'
    },
    
    // Event Type Icons
    EVENT_ICONS: {
        'PushEvent': '📤',
        'PullRequestEvent': '🔀',
        'IssuesEvent': '🐛',
        'IssueCommentEvent': '💬',
        'WatchEvent': '⭐',
        'ForkEvent': '🍴',
        'CreateEvent': '✨',
        'DeleteEvent': '🗑️',
        'PublicEvent': '🌍',
        'ReleaseEvent': '🚀',
        'MemberEvent': '👥',
        'TeamEvent': '🏢',
        'CommitCommentEvent': '💭',
        'PullRequestReviewEvent': '👀',
        'PullRequestReviewCommentEvent': '📝',
        'default': '📊'
    },
    
    // Event Category Colors
    CATEGORY_COLORS: {
        'code': '#2563eb',
        'issues': '#dc2626',
        'social': '#059669',
        'repository': '#7c3aed',
        'releases': '#ea580c',
        'collaboration': '#0891b2',
        'other': '#64748b'
    },
    
    // Default Settings
    DEFAULT_TIME_RANGE: 24, // hours (locked)
    DEFAULT_PAGE_SIZE: 20,
    MAX_EVENTS_DISPLAY: 100,
    
    // Animation Settings
    CHART_ANIMATION_DURATION: 750,
    UPDATE_ANIMATION_DURATION: 300,
    
    // Error Handling
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000, // 1 second
    
    // Data Formatting
    DATE_FORMAT: 'MMM dd, yyyy HH:mm:ss',
    RELATIVE_TIME_THRESHOLD: 3600000, // 1 hour in milliseconds
    
    // Performance
    DEBOUNCE_DELAY: 300, // milliseconds
    CACHE_DURATION: 10000, // 10 seconds
    
    // Feature Flags
    FEATURES: {
        AUTO_REFRESH: true,
        EXPORT_FUNCTIONALITY: true,
        REAL_TIME_UPDATES: true,
        ADVANCED_FILTERING: true
    }
};

// Utility functions
const UTILS = {
    // Format numbers with commas
    formatNumber: (num) => {
        if (num === null || num === undefined) return '-';
        return new Intl.NumberFormat().format(num);
    },
    
    // Format relative time
    formatRelativeTime: (timestamp) => {
        const now = new Date();
        const time = new Date(timestamp);
        const diff = now - time;
        
        if (diff < CONFIG.RELATIVE_TIME_THRESHOLD) {
            // Use relative time for recent events
            const minutes = Math.floor(diff / 60000);
            const seconds = Math.floor((diff % 60000) / 1000);
            
            if (minutes > 0) {
                return `${minutes}m ago`;
            } else {
                return `${seconds}s ago`;
            }
        } else {
            // Use absolute time for older events
            return time.toLocaleString();
        }
    },
    
    // Get event icon
    getEventIcon: (eventType) => {
        return CONFIG.EVENT_ICONS[eventType] || CONFIG.EVENT_ICONS.default;
    },
    
    // Get category color
    getCategoryColor: (category) => {
        return CONFIG.CATEGORY_COLORS[category] || CONFIG.CATEGORY_COLORS.other;
    },
    
    // Debounce function
    debounce: (func, delay) => {
        let timeoutId;
        return (...args) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(null, args), delay);
        };
    },
    
    // Generate random color from palette
    getRandomColor: () => {
        const colors = Object.values(CONFIG.CHART_COLORS);
        return colors[Math.floor(Math.random() * colors.length)];
    },
    
    // Truncate text
    truncateText: (text, maxLength) => {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },
    
    // Generate CSV from data
    generateCSV: (data, headers) => {
        const csvContent = [
            headers.join(','),
            ...data.map(row => headers.map(header => 
                JSON.stringify(row[header] || '')
            ).join(','))
        ].join('\n');
        
        return csvContent;
    },
    
    // Download file
    downloadFile: (content, filename, contentType = 'text/csv') => {
        const blob = new Blob([content], { type: contentType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    },
    
    // Show notification
    showNotification: (message, type = 'info') => {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        `;
        
        // Set background color based on type
        const colors = {
            'info': '#2563eb',
            'success': '#059669',
            'warning': '#d97706',
            'error': '#dc2626'
        };
        notification.style.backgroundColor = colors[type] || colors.info;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-in';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }
};

// Add CSS for notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(notificationStyles);
