import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class GitHubEventsClient:
    """Client for fetching GitHub events from the public API"""
    
    def __init__(self):
        self.base_url = Config.GITHUB_API_BASE_URL
        self.session = requests.Session()
        self.last_etag = None
        self.rate_limit_remaining = Config.REQUESTS_PER_HOUR
        self.rate_limit_reset_time = None
        
        # Set up authentication if token is provided
        if Config.GITHUB_TOKEN:
            self.session.headers.update({
                'Authorization': f'Bearer {Config.GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })
        else:
            self.session.headers.update({
                'Accept': 'application/vnd.github.v3+json',
                'X-GitHub-Api-Version': '2022-11-28'
            })
    
    def fetch_events(self) -> List[Dict]:
        """
        Fetch recent GitHub events from the public events API
        Returns a list of event dictionaries
        """
        url = f"{self.base_url}{Config.GITHUB_EVENTS_ENDPOINT}"
        
        # Check rate limit before making request
        if not self._can_make_request():
            reset_in = int(self.rate_limit_reset_time - time.time()) if self.rate_limit_reset_time else None
            logger.warning(f"Rate limit exceeded. Skipping this fetch cycle. remaining={self.rate_limit_remaining} reset_in={reset_in}s")
            return []
        
        try:
            # Use ETag for conditional requests to save on rate limits
            headers = {}
            if self.last_etag:
                headers['If-None-Match'] = self.last_etag
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            # Update rate limit information
            self._update_rate_limit_info(response)
            
            if response.status_code == 304:
                # No new events since last fetch
                logger.debug("No new events since last fetch (304 Not Modified)")
                return []
            
            if response.status_code == 200:
                # Update ETag for next request
                self.last_etag = response.headers.get('ETag')
                
                events = response.json()
                logger.info(f"Successfully fetched {len(events)} GitHub events")
                
                # Add processing timestamp to each event
                current_time = datetime.utcnow().isoformat()
                for event in events:
                    event['processed_at'] = current_time
                
                return events[:Config.MAX_EVENTS_PER_FETCH]
            
            if response.status_code in (403, 429):
                logger.warning(f"GitHub rate limited request: status={response.status_code} remaining={self.rate_limit_remaining} reset={self.rate_limit_reset_time}")
                return []
            
            logger.error(f"GitHub API request failed: {response.status_code} - {response.text}")
            return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching GitHub events: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching GitHub events: {e}")
            return []
    
    def _can_make_request(self) -> bool:
        """Check if we can make a request without hitting rate limits"""
        if self.rate_limit_remaining <= 0:
            if self.rate_limit_reset_time and time.time() < self.rate_limit_reset_time:
                return False
        return True
    
    def _update_rate_limit_info(self, response: requests.Response):
        """Update rate limit information from response headers"""
        try:
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', self.rate_limit_remaining))
            reset_timestamp = response.headers.get('X-RateLimit-Reset')
            if reset_timestamp:
                self.rate_limit_reset_time = int(reset_timestamp)
            limit = response.headers.get('X-RateLimit-Limit')
            used = response.headers.get('X-RateLimit-Used')
            logger.debug(f"RateLimit: limit={limit} remaining={self.rate_limit_remaining} used={used} reset={self.rate_limit_reset_time}")
        except (ValueError, TypeError):
            # If we can't parse the headers, just continue
            pass
    
    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return {
            'remaining': self.rate_limit_remaining,
            'reset_time': self.rate_limit_reset_time,
            'can_make_request': self._can_make_request()
        }
