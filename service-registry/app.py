#!/usr/bin/env python3
"""
Service Registry - Central registry for all microservices
Provides health checks, service discovery, and monitoring
"""

import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import asyncio
import aiohttp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service definitions
SERVICES = {
    "github-producer": {
        "name": "GitHub Events Producer",
        "url": "http://github-producer-service:8001",
        "health_endpoint": "/health",
        "description": "Fetches GitHub events and publishes to Kafka"
    },
    "spark-streaming": {
        "name": "Spark Streaming Service", 
        "url": "http://spark-streaming-service:8002",
        "health_endpoint": "/health",
        "description": "Processes Kafka events and writes to Iceberg"
    },
    "data-query": {
        "name": "Data Query Service",
        "url": "http://data-query-service:8003", 
        "health_endpoint": "/health",
        "description": "Queries Iceberg data via REST API"
    }
}

class ServiceStatus(BaseModel):
    name: str
    status: str
    url: str
    last_check: datetime
    response_time_ms: Optional[float] = None
    error: Optional[str] = None

class ServiceRegistry(BaseModel):
    services: List[ServiceStatus]
    overall_status: str
    last_updated: datetime

app = FastAPI(
    title="GitHub Events Service Registry",
    description="Central registry and health monitoring for all microservices",
    version="1.0.0"
)

# In-memory service status cache
service_status_cache: Dict[str, ServiceStatus] = {}

async def check_service_health(service_name: str, service_config: dict) -> ServiceStatus:
    """Check health of a single service"""
    start_time = datetime.now()
    
    try:
        async with aiohttp.ClientSession() as session:
            health_url = f"{service_config['url']}{service_config['health_endpoint']}"
            
            async with session.get(health_url, timeout=5) as response:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status == 200:
                    return ServiceStatus(
                        name=service_config['name'],
                        status="healthy",
                        url=service_config['url'],
                        last_check=datetime.now(),
                        response_time_ms=response_time
                    )
                else:
                    return ServiceStatus(
                        name=service_config['name'],
                        status="unhealthy",
                        url=service_config['url'],
                        last_check=datetime.now(),
                        response_time_ms=response_time,
                        error=f"HTTP {response.status}"
                    )
                    
    except asyncio.TimeoutError:
        return ServiceStatus(
            name=service_config['name'],
            status="unhealthy",
            url=service_config['url'],
            last_check=datetime.now(),
            error="Timeout"
        )
    except Exception as e:
        return ServiceStatus(
            name=service_config['name'],
            status="unhealthy", 
            url=service_config['url'],
            last_check=datetime.now(),
            error=str(e)
        )

async def check_all_services():
    """Check health of all services"""
    tasks = []
    
    for service_name, service_config in SERVICES.items():
        task = check_service_health(service_name, service_config)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        service_name = list(SERVICES.keys())[i]
        if isinstance(result, Exception):
            service_config = SERVICES[service_name]
            result = ServiceStatus(
                name=service_config['name'],
                status="unhealthy",
                url=service_config['url'],
                last_check=datetime.now(),
                error=str(result)
            )
        
        service_status_cache[service_name] = result
    
    logger.info(f"Health check completed for {len(SERVICES)} services")

@app.get("/health")
async def registry_health():
    """Registry health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "services_monitored": len(SERVICES)
    }

@app.get("/services", response_model=ServiceRegistry)
async def get_all_services():
    """Get status of all services"""
    if not service_status_cache:
        await check_all_services()
    
    services = list(service_status_cache.values())
    
    # Determine overall status
    healthy_count = sum(1 for s in services if s.status == "healthy")
    overall_status = "healthy" if healthy_count == len(services) else "degraded"
    
    return ServiceRegistry(
        services=services,
        overall_status=overall_status,
        last_updated=datetime.now()
    )

@app.get("/services/{service_name}")
async def get_service_status(service_name: str):
    """Get status of a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check service health
    service_config = SERVICES[service_name]
    status = await check_service_health(service_name, service_config)
    
    return status

@app.post("/services/{service_name}/check")
async def force_health_check(service_name: str):
    """Force a health check for a specific service"""
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service_config = SERVICES[service_name]
    status = await check_service_health(service_name, service_config)
    
    # Update cache
    service_status_cache[service_name] = status
    
    return status

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "GitHub Events Service Registry",
        "version": "1.0.0",
        "services": list(SERVICES.keys()),
        "endpoints": {
            "health": "/health",
            "all_services": "/services",
            "service_status": "/services/{service_name}",
            "force_check": "/services/{service_name}/check",
            "documentation": "/docs"
        }
    }

# Background task for periodic health checks
async def periodic_health_checks():
    """Run health checks every 30 seconds"""
    while True:
        try:
            await check_all_services()
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Error in periodic health checks: {e}")
            await asyncio.sleep(30)

@app.on_event("startup")
async def startup_event():
    """Start background health check task"""
    logger.info("Starting Service Registry")
    asyncio.create_task(periodic_health_checks())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Service Registry")

def main():
    """Main entry point"""
    logger.info("Starting GitHub Events Service Registry")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()
