import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # GitHub API Configuration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_API_BASE_URL = 'https://api.github.com'
    GITHUB_EVENTS_ENDPOINT = '/events'
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'github-events')
    
    # Producer Configuration
    FETCH_INTERVAL_SECONDS = int(os.getenv('FETCH_INTERVAL_SECONDS', '3'))
    MAX_EVENTS_PER_FETCH = int(os.getenv('MAX_EVENTS_PER_FETCH', '100'))
    
    # Rate limiting to avoid hitting GitHub API limits
    REQUESTS_PER_HOUR = 5000 if GITHUB_TOKEN else 60
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        if not cls.GITHUB_TOKEN:
            print("Warning: No GitHub token provided. Rate limiting will be more restrictive.")
        
        if cls.FETCH_INTERVAL_SECONDS < 1:
            raise ValueError("FETCH_INTERVAL_SECONDS must be at least 1 second")
        
        return True
