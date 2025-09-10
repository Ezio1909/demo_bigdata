#!/usr/bin/env python3
"""
GitHub Events REST API
Provides REST endpoints for querying GitHub events from Iceberg tables
"""

import logging
import sys
from datetime import datetime
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

from config import APIConfig
from models import (
    GitHubEvent, EventsResponse, DashboardStats, QueryParameters,
    HealthCheck, ErrorResponse
)
from data_service import GitHubEventsDataService
import json
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

# Global data service instance
data_service: GitHubEventsDataService = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global data_service
    
    # Startup
    logger.info("Starting GitHub Events API")
    data_service = GitHubEventsDataService()
    
    if not data_service.initialize():
        logger.error("Failed to initialize data service")
        raise Exception("Data service initialization failed")
    
    logger.info("API startup complete")
    yield
    
    # Shutdown
    logger.info("Shutting down GitHub Events API")
    if data_service:
        data_service.close()
    logger.info("API shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="GitHub Events API",
    description="REST API for real-time GitHub events monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_data_service() -> GitHubEventsDataService:
    """Dependency to get data service instance"""
    if not data_service:
        raise HTTPException(status_code=503, detail="Data service not available")
    return data_service

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message=str(exc),
            timestamp=datetime.now()
        ).dict()
    )

@app.get("/health", response_model=HealthCheck)
async def health_check(service: GitHubEventsDataService = Depends(get_data_service)):
    """Health check endpoint"""
    try:
        components = service.health_check()
        
        # Determine overall status
        status = "healthy" if all(
            "healthy" in comp_status for comp_status in components.values()
        ) else "unhealthy"
        
        return HealthCheck(
            status=status,
            timestamp=datetime.now(),
            components=components
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")

@app.get("/events", response_model=EventsResponse)
async def get_events(
    event_type: str = Query(None, description="Filter by event type"),
    event_category: str = Query(None, description="Filter by event category"),
    actor_login: str = Query(None, description="Filter by actor login"),
    repo_name: str = Query(None, description="Filter by repository name"),
    org_login: str = Query(None, description="Filter by organization login"),
    is_public: bool = Query(None, description="Filter by public/private status"),
    hours_back: int = Query(1, ge=1, le=24, description="Hours of data to retrieve"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    service: GitHubEventsDataService = Depends(get_data_service)
):
    """Get GitHub events with filtering and pagination"""
    try:
        params = QueryParameters(
            event_type=event_type,
            event_category=event_category,
            actor_login=actor_login,
            repo_name=repo_name,
            org_login=org_login,
            is_public=is_public,
            hours_back=hours_back,
            page=page,
            page_size=page_size
        )
        
        events, total_count = service.get_events(params)
        
        has_more = (page * page_size) < total_count
        
        return EventsResponse(
            events=events,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Error getting events: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get events: {e}")

@app.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    hours_back: int = Query(24, ge=1, le=24, description="Hours of data for statistics (forced to 24h)"),
    service: GitHubEventsDataService = Depends(get_data_service)
):
    """Get comprehensive dashboard statistics"""
    try:
        # Force a metadata refresh before reading to avoid stale snapshots
        try:
            if data_service and data_service.spark:
                data_service.spark.catalog.refreshTable(data_service.table_name)
        except Exception:
            pass
        stats = service.get_dashboard_stats(hours_back)
        
        if not stats:
            raise HTTPException(status_code=404, detail="No statistics available")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e}")

@app.get("/stream")
async def stream_metrics(service: GitHubEventsDataService = Depends(get_data_service)):
    """Server-Sent Events stream that pushes latest 24h metrics every ~30s."""
    async def event_generator():
        last_sent = None
        while True:
            try:
                stats = service.get_dashboard_stats(24)
                if stats:
                    payload = stats.json()
                    if payload != last_sent:
                        yield f"data: {payload}\n\n"
                        last_sent = payload
                    else:
                        # keep-alive comment to prevent proxies from closing
                        yield ": keep-alive\n\n"
                else:
                    yield ": waiting\n\n"
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            await asyncio.sleep(15)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)

@app.get("/event-types", response_model=List[str])
async def get_event_types(service: GitHubEventsDataService = Depends(get_data_service)):
    """Get list of available event types"""
    try:
        event_types = service.get_event_types()
        return event_types
        
    except Exception as e:
        logger.error(f"Error getting event types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get event types: {e}")

@app.get("/event-categories", response_model=List[str])
async def get_event_categories(service: GitHubEventsDataService = Depends(get_data_service)):
    """Get list of available event categories"""
    try:
        categories = service.get_event_categories()
        return categories
        
    except Exception as e:
        logger.error(f"Error getting event categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get event categories: {e}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "GitHub Events API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "events": "/events",
            "statistics": "/stats",
            "event_types": "/event-types",
            "event_categories": "/event-categories",
            "documentation": "/docs"
        }
    }

def main():
    """Main entry point"""
    logger.info("Starting GitHub Events API server")
    
    uvicorn.run(
        "app:app",
        host=APIConfig.HOST,
        port=APIConfig.PORT,
        reload=APIConfig.DEBUG,
        log_level="info"
    )

if __name__ == "__main__":
    main()
