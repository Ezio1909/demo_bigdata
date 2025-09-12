// Events Management for GitHub Events Dashboard
class EventsManager {
    constructor() {
        this.currentPage = 1;
        this.currentFilters = {
            event_type: '',
            event_category: '',
            hours_back: CONFIG.DEFAULT_TIME_RANGE,
            page_size: CONFIG.DEFAULT_PAGE_SIZE
        };
        this.isLoading = false;
        this.hasMoreEvents = true;
        this.allEvents = [];
    }
    
    // Initialize events functionality
    async initialize() {
        await this.loadEventTypes();
        await this.loadEventCategories();
        await this.loadRecentEvents();
    }
    
    // Load available event types for filter dropdown
    async loadEventTypes() {
        try {
            const eventTypes = await api.getEventTypes();
            const select = document.getElementById('eventTypeFilter');
            
            if (select && eventTypes) {
                // Clear existing options except the first one
                select.innerHTML = '<option value="">All Event Types</option>';
                
                eventTypes.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = `${UTILS.getEventIcon(type)} ${type}`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading event types:', error);
        }
    }
    
    // Load available event categories for filter dropdown
    async loadEventCategories() {
        try {
            const categories = await api.getEventCategories();
            const select = document.getElementById('eventCategoryFilter');
            
            if (select && categories) {
                // Clear existing options except the first one
                select.innerHTML = '<option value="">All Categories</option>';
                
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category.charAt(0).toUpperCase() + category.slice(1);
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading event categories:', error);
        }
    }
    
    // Load recent events
    async loadRecentEvents(reset = true) {
        if (this.isLoading) return;
        
        this.isLoading = true;
        const eventsList = document.getElementById('eventsList');
        
        try {
            if (reset) {
                this.currentPage = 1;
                this.allEvents = [];
                eventsList.innerHTML = '<div class="loading">Loading recent events...</div>';
            } else {
                // Show loading indicator for pagination
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'loading';
                loadingDiv.textContent = 'Loading more events...';
                eventsList.appendChild(loadingDiv);
            }
            
            const params = {
                ...this.currentFilters,
                page: this.currentPage,
                page_size: CONFIG.DEFAULT_PAGE_SIZE
            };
            
            const response = await api.getEvents(params);
            
            if (response && response.events) {
                if (reset) {
                    this.allEvents = response.events;
                } else {
                    this.allEvents = [...this.allEvents, ...response.events];
                }
                
                this.hasMoreEvents = response.has_more;
                this.renderEvents();
                
                if (!reset) {
                    // Remove loading indicator
                    const loadingIndicator = eventsList.querySelector('.loading');
                    if (loadingIndicator) {
                        loadingIndicator.remove();
                    }
                }
            }
            
        } catch (error) {
            console.error('Error loading events:', error);
            APIErrorHandler.handle(error, 'loading events');
            
            if (reset) {
                eventsList.innerHTML = '<div class="no-data">Failed to load events</div>';
            }
        } finally {
            this.isLoading = false;
        }
    }
    
    // Render events in the events list
    renderEvents() {
        const eventsList = document.getElementById('eventsList');
        if (!eventsList) return;
        
        if (this.allEvents.length === 0) {
            eventsList.innerHTML = '<div class="no-data">No events found</div>';
            return;
        }
        
        // Clear existing content
        eventsList.innerHTML = '';
        
        // Render each event
        this.allEvents.forEach(event => {
            const eventElement = this.createEventElement(event);
            eventsList.appendChild(eventElement);
        });
        
        // Add load more button if there are more events
        if (this.hasMoreEvents && !this.isLoading) {
            const loadMoreButton = document.createElement('button');
            loadMoreButton.textContent = 'Load More Events';
            loadMoreButton.className = 'load-more-btn';
            loadMoreButton.onclick = () => this.loadMoreEvents();
            eventsList.appendChild(loadMoreButton);
        }
    }
    
    // Create HTML element for a single event
    createEventElement(event) {
        const eventDiv = document.createElement('div');
        eventDiv.className = 'event-item';
        
        const eventIcon = UTILS.getEventIcon(event.event_type);
        const relativeTime = UTILS.formatRelativeTime(event.created_at);
        
        // Create event title based on event type and data
        const eventTitle = this.generateEventTitle(event);
        
        // Create repository link if available
        const repoLink = event.repo_name ? 
            `<a href="https://github.com/${event.repo_name}" target="_blank" rel="noopener">${event.repo_name}</a>` :
            'Unknown repository';
        
        // Create actor link if available
        const actorLink = event.actor_login ?
            `<a href="https://github.com/${event.actor_login}" target="_blank" rel="noopener">${event.actor_login}</a>` :
            'Unknown actor';
        
        eventDiv.innerHTML = `
            <div class="event-icon">${eventIcon}</div>
            <div class="event-details">
                <div class="event-title">${eventTitle}</div>
                <div class="event-meta">
                    <span>👤 ${actorLink}</span>
                    <span>📦 ${repoLink}</span>
                    <span>🏷️ ${event.event_type}</span>
                    ${event.action ? `<span>⚡ ${event.action}</span>` : ''}
                    ${event.org_login ? `<span>🏢 ${event.org_login}</span>` : ''}
                </div>
            </div>
            <div class="event-time" title="${new Date(event.created_at).toLocaleString()}">
                ${relativeTime}
            </div>
        `;
        
        return eventDiv;
    }
    
    // Generate human-readable event title
    generateEventTitle(event) {
        const actor = event.actor_login || 'Someone';
        const repo = event.repo_name || 'a repository';
        
        switch (event.event_type) {
            case 'PushEvent':
                const ref = event.ref ? event.ref.replace('refs/heads/', '') : 'branch';
                return `${actor} pushed to ${ref} in ${repo}`;
            
            case 'PullRequestEvent':
                const action = event.action || 'updated';
                return `${actor} ${action} a pull request in ${repo}`;
            
            case 'IssuesEvent':
                const issueAction = event.action || 'updated';
                return `${actor} ${issueAction} an issue in ${repo}`;
            
            case 'WatchEvent':
                return `${actor} starred ${repo}`;
            
            case 'ForkEvent':
                return `${actor} forked ${repo}`;
            
            case 'CreateEvent':
                const refType = event.ref_type || 'repository';
                return `${actor} created ${refType} in ${repo}`;
            
            case 'DeleteEvent':
                const deleteRefType = event.ref_type || 'branch';
                return `${actor} deleted ${deleteRefType} in ${repo}`;
            
            case 'ReleaseEvent':
                const releaseAction = event.action || 'published';
                return `${actor} ${releaseAction} a release in ${repo}`;
            
            case 'IssueCommentEvent':
                return `${actor} commented on an issue in ${repo}`;
            
            case 'PullRequestReviewEvent':
                return `${actor} reviewed a pull request in ${repo}`;
            
            case 'MemberEvent':
                return `${actor} was added as a collaborator to ${repo}`;
            
            default:
                return `${actor} performed ${event.event_type} in ${repo}`;
        }
    }
    
    // Apply filters to events
    async applyFilters() {
        const eventTypeFilter = document.getElementById('eventTypeFilter');
        const eventCategoryFilter = document.getElementById('eventCategoryFilter');
        
        this.currentFilters = {
            ...this.currentFilters,
            event_type: eventTypeFilter?.value || '',
            event_category: eventCategoryFilter?.value || ''
        };
        
        await this.loadRecentEvents(true);
    }
    
    // Load more events (pagination)
    async loadMoreEvents() {
        if (!this.hasMoreEvents || this.isLoading) return;
        
        this.currentPage++;
        await this.loadRecentEvents(false);
    }
    
    // Update time range for events
    updateTimeRange(hoursBack) {
        this.currentFilters.hours_back = hoursBack;
        this.loadRecentEvents(true);
    }
    
    // Refresh events
    async refreshEvents() {
        await this.loadRecentEvents(true);
    }
    
    // Search events (if implemented)
    searchEvents(query) {
        // This could be implemented to filter events by text search
        // For now, we'll just show a message
        console.log('Search functionality not implemented yet:', query);
    }
}

// Global events manager instance
const eventsManager = new EventsManager();

// Functions called from HTML
function applyFilters() {
    eventsManager.applyFilters();
}

function loadMoreEvents() {
    eventsManager.loadMoreEvents();
}

// Add CSS for events
const eventsStyles = document.createElement('style');
eventsStyles.textContent = `
    .event-item {
        animation: slideInFromRight 0.3s ease-out;
    }
    
    @keyframes slideInFromRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .event-meta a {
        color: var(--primary-color);
        text-decoration: none;
        font-weight: 500;
    }
    
    .event-meta a:hover {
        text-decoration: underline;
    }
    
    .load-more-btn {
        width: 100%;
        padding: 12px;
        margin-top: 20px;
        background: var(--background-color);
        border: 2px dashed var(--border-color);
        border-radius: 8px;
        cursor: pointer;
        font-size: 14px;
        color: var(--text-secondary);
        transition: all 0.2s;
    }
    
    .load-more-btn:hover {
        background: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
    }
`;
document.head.appendChild(eventsStyles);
