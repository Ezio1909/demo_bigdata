#!/usr/bin/env python3
"""
GitHub Events Producer API Service
Provides REST API for controlling the GitHub events producer
"""

import logging
import sys
import asyncio
import threading
from datetime import datetime
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn

# Import the producer components
from github_client import GitHubEventsClient
from kafka_producer import GitHubEventsKafkaProducer
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProducerStatus(BaseModel):
    status: str
    is_running: bool
    start_time: Optional[datetime] = None
    total_events_fetched: int = 0
    total_events_sent: int = 0
    fetch_cycles: int = 0
    errors: int = 0
    last_fetch_time: Optional[datetime] = None
    rate_limit_remaining: Optional[int] = None

class ProducerConfig(BaseModel):
    fetch_interval_seconds: int = 30
    max_events_per_fetch: int = 100
    github_token: Optional[str] = None

app = FastAPI(
    title="GitHub Events Producer API",
    description="REST API for controlling GitHub events producer",
    version="1.0.0"
)

# Global producer state
producer_status = ProducerStatus(
    status="stopped",
    is_running=False
)

# Producer components
github_client: Optional[GitHubEventsClient] = None
kafka_producer: Optional[GitHubEventsKafkaProducer] = None
producer_thread: Optional[threading.Thread] = None
stop_event = threading.Event()

def producer_worker():
    """Background worker that fetches and sends events"""
    global producer_status
    
    try:
        producer_status.status = "running"
        producer_status.start_time = datetime.now()
        
        logger.info("Producer worker started")
        
        while not stop_event.is_set():
            cycle_start_time = datetime.now()
            
            try:
                # Fetch events from GitHub
                events = github_client.fetch_events()
                producer_status.total_events_fetched += len(events)
                producer_status.last_fetch_time = datetime.now()
                
                if events:
                    # Send events to Kafka
                    sent_count = kafka_producer.send_events(events)
                    producer_status.total_events_sent += sent_count
                    logger.info(f"Sent {sent_count} events to Kafka")
                
                producer_status.fetch_cycles += 1
                
                # Get rate limit status
                rate_limit_status = github_client.get_rate_limit_status()
                producer_status.rate_limit_remaining = rate_limit_status['remaining']
                
            except Exception as e:
                logger.error(f"Error in producer cycle: {e}")
                producer_status.errors += 1
            
            # Wait for next cycle
            cycle_duration = (datetime.now() - cycle_start_time).total_seconds()
            sleep_time = max(0, Config.FETCH_INTERVAL_SECONDS - cycle_duration)
            
            if stop_event.wait(sleep_time):
                break
                
    except Exception as e:
        logger.error(f"Producer worker error: {e}")
        producer_status.status = "error"
        producer_status.errors += 1
    finally:
        producer_status.status = "stopped"
        producer_status.is_running = False
        logger.info("Producer worker stopped")

def initialize_components():
    """Initialize GitHub client and Kafka producer"""
    global github_client, kafka_producer
    
    try:
        # Initialize GitHub client
        github_client = GitHubEventsClient()
        logger.info("GitHub client initialized")
        
        # Initialize Kafka producer
        kafka_producer = GitHubEventsKafkaProducer()
        logger.info("Kafka producer initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        return False

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "producer_status": producer_status.status,
        "components_initialized": github_client is not None and kafka_producer is not None
    }

@app.get("/status", response_model=ProducerStatus)
async def get_status():
    """Get current producer status"""
    return producer_status

@app.post("/start")
async def start_producer(background_tasks: BackgroundTasks):
    """Start the producer"""
    global producer_thread, stop_event
    
    if producer_status.is_running:
        raise HTTPException(status_code=400, detail="Producer is already running")
    
    if not initialize_components():
        raise HTTPException(status_code=500, detail="Failed to initialize components")
    
    # Reset stop event
    stop_event.clear()
    
    # Start producer thread
    producer_thread = threading.Thread(target=producer_worker, daemon=True)
    producer_thread.start()
    
    producer_status.is_running = True
    
    logger.info("Producer started via API")
    
    return {
        "message": "Producer started successfully",
        "status": producer_status.status
    }

@app.post("/stop")
async def stop_producer():
    """Stop the producer"""
    global producer_thread, stop_event
    
    if not producer_status.is_running:
        raise HTTPException(status_code=400, detail="Producer is not running")
    
    # Signal stop
    stop_event.set()
    
    # Wait for thread to finish
    if producer_thread and producer_thread.is_alive():
        producer_thread.join(timeout=10)
    
    producer_status.is_running = False
    producer_status.status = "stopped"
    
    logger.info("Producer stopped via API")
    
    return {
        "message": "Producer stopped successfully",
        "status": producer_status.status
    }

@app.post("/config")
async def update_config(config: ProducerConfig):
    """Update producer configuration"""
    try:
        # Update configuration
        Config.FETCH_INTERVAL_SECONDS = config.fetch_interval_seconds
        Config.MAX_EVENTS_PER_FETCH = config.max_events_per_fetch
        
        if config.github_token:
            Config.GITHUB_TOKEN = config.github_token
            # Reinitialize GitHub client with new token
            if github_client:
                github_client.session.headers.update({
                    'Authorization': f'token {config.github_token}'
                })
        
        logger.info("Configuration updated")
        
        return {
            "message": "Configuration updated successfully",
            "config": {
                "fetch_interval_seconds": Config.FETCH_INTERVAL_SECONDS,
                "max_events_per_fetch": Config.MAX_EVENTS_PER_FETCH,
                "has_github_token": bool(Config.GITHUB_TOKEN)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")

@app.get("/stats")
async def get_stats():
    """Get detailed producer statistics"""
    uptime = None
    if producer_status.start_time:
        uptime = (datetime.now() - producer_status.start_time).total_seconds()
    
    return {
        "status": producer_status.status,
        "is_running": producer_status.is_running,
        "uptime_seconds": uptime,
        "total_events_fetched": producer_status.total_events_fetched,
        "total_events_sent": producer_status.total_events_sent,
        "fetch_cycles": producer_status.fetch_cycles,
        "errors": producer_status.errors,
        "last_fetch_time": producer_status.last_fetch_time,
        "rate_limit_remaining": producer_status.rate_limit_remaining,
        "fetch_interval_seconds": Config.FETCH_INTERVAL_SECONDS,
        "max_events_per_fetch": Config.MAX_EVENTS_PER_FETCH
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GitHub Events Producer API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "start": "/start",
            "stop": "/stop",
            "config": "/config",
            "stats": "/stats",
            "documentation": "/docs"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting GitHub Events Producer API")
    initialize_components()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Producer API")
    
    # Stop producer if running
    if producer_status.is_running:
        stop_event.set()
        if producer_thread and producer_thread.is_alive():
            producer_thread.join(timeout=5)
    
    # Close Kafka producer
    if kafka_producer:
        kafka_producer.close()

def main():
    """Main entry point"""
    logger.info("Starting GitHub Events Producer API Service")
    
    uvicorn.run(
        "producer_api:app",
        host="0.0.0.0",
        port=8001,
        log_level="info"
    )

if __name__ == "__main__":
    main()
