#!/usr/bin/env python3
"""
GitHub Events Producer
Fetches GitHub events from the public API and publishes them to Kafka
"""

import logging
import time
import signal
import sys
from datetime import datetime
from github.client import GitHubEventsClient
from kafka_io.producer import GitHubEventsKafkaProducer
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('github_producer.log')
    ]
)
logger = logging.getLogger(__name__)

class GitHubEventProducerService:
    """Main service class for the GitHub event producer"""
    
    def __init__(self):
        self.running = False
        self.github_client = None
        self.kafka_producer = None
        
        # Statistics
        self.stats = {
            'total_events_fetched': 0,
            'total_events_sent': 0,
            'fetch_cycles': 0,
            'errors': 0,
            'start_time': None
        }
    
    def initialize(self):
        """Initialize the service components"""
        try:
            # Validate configuration
            Config.validate()
            
            # Initialize GitHub client
            self.github_client = GitHubEventsClient()
            logger.info("GitHub client initialized")
            
            # Initialize Kafka producer
            self.kafka_producer = GitHubEventsKafkaProducer()
            logger.info("Kafka producer initialized")
            
            self.stats['start_time'] = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            return False
    
    def run(self):
        """Main run loop"""
        if not self.initialize():
            logger.error("Service initialization failed. Exiting.")
            return
        
        self.running = True
        logger.info(f"GitHub Event Producer started. Fetch interval: {Config.FETCH_INTERVAL_SECONDS}s")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            while self.running:
                cycle_start_time = time.time()
                
                # Fetch events from GitHub
                events = self._fetch_events()
                
                if events:
                    # Send events to Kafka
                    sent_count = self._send_events(events)
                    self.stats['total_events_sent'] += sent_count
                
                self.stats['fetch_cycles'] += 1
                
                # Log statistics periodically
                if self.stats['fetch_cycles'] % 10 == 0:
                    self._log_statistics()
                
                # Calculate sleep time to maintain consistent interval
                cycle_duration = time.time() - cycle_start_time
                sleep_time = max(0, Config.FETCH_INTERVAL_SECONDS - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.stats['errors'] += 1
        
        finally:
            self._shutdown()
    
    def _fetch_events(self):
        """Fetch events from GitHub API"""
        try:
            events = self.github_client.fetch_events()
            self.stats['total_events_fetched'] += len(events)
            
            if events:
                logger.debug(f"Fetched {len(events)} events from GitHub API")
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            self.stats['errors'] += 1
            return []
    
    def _send_events(self, events):
        """Send events to Kafka"""
        try:
            sent_count = self.kafka_producer.send_events(events)
            logger.debug(f"Sent {sent_count} events to Kafka")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending events to Kafka: {e}")
            self.stats['errors'] += 1
            return 0
    
    def _log_statistics(self):
        """Log service statistics"""
        uptime = datetime.utcnow() - self.stats['start_time']
        rate_limit_status = self.github_client.get_rate_limit_status()
        
        logger.info(f"Statistics - Uptime: {uptime}, "
                   f"Cycles: {self.stats['fetch_cycles']}, "
                   f"Events Fetched: {self.stats['total_events_fetched']}, "
                   f"Events Sent: {self.stats['total_events_sent']}, "
                   f"Errors: {self.stats['errors']}, "
                   f"Rate Limit Remaining: {rate_limit_status['remaining']}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")
        self.running = False
    
    def _shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down GitHub Event Producer...")
        
        if self.kafka_producer:
            self.kafka_producer.close()
        
        # Final statistics
        self._log_statistics()
        logger.info("GitHub Event Producer shutdown complete")

def main():
    """Main entry point"""
    logger.info("Starting GitHub Event Producer Service")
    
    service = GitHubEventProducerService()
    service.run()

if __name__ == "__main__":
    main()
