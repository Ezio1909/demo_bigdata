from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GitHubEvent(BaseModel):
    """GitHub event model"""
    event_id: str
    event_type: str
    event_category: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    actor_id: Optional[int] = None
    actor_login: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    repo_id: Optional[int] = None
    repo_name: Optional[str] = None
    repo_url: Optional[str] = None
    org_id: Optional[int] = None
    org_login: Optional[str] = None
    is_public: Optional[bool] = None
    action: Optional[str] = None
    ref: Optional[str] = None
    ref_type: Optional[str] = None
    master_branch: Optional[str] = None
    description: Optional[str] = None
    pusher_type: Optional[str] = None
    payload_json: Optional[str] = None
    processing_date: Optional[str] = None
    processing_hour: Optional[int] = None
    has_actor: Optional[bool] = None
    has_repo: Optional[bool] = None
    has_org: Optional[bool] = None

class EventsResponse(BaseModel):
    """Response model for events endpoint"""
    events: List[GitHubEvent]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class EventTypeStats(BaseModel):
    """Statistics by event type"""
    event_type: str
    count: int
    percentage: float

class EventCategoryStats(BaseModel):
    """Statistics by event category"""
    event_category: str
    count: int
    percentage: float

class TimeSeriesPoint(BaseModel):
    """Time series data point"""
    timestamp: datetime
    count: int

class RepositoryStats(BaseModel):
    """Repository statistics"""
    repo_name: str
    repo_id: int
    event_count: int
    unique_actors: int
    event_types: List[str]

class ActorStats(BaseModel):
    """Actor statistics"""
    actor_login: str
    actor_id: int
    event_count: int
    repo_count: int
    event_types: List[str]

class DashboardStats(BaseModel):
    """Dashboard statistics model"""
    total_events: int
    unique_repositories: int
    unique_actors: int
    event_types_count: int
    last_updated: datetime
    time_range_hours: int
    
    # Event type distribution
    event_type_stats: List[EventTypeStats]
    
    # Event category distribution
    event_category_stats: List[EventCategoryStats]
    
    # Time series data (events per hour)
    hourly_events: List[TimeSeriesPoint]
    
    # Top repositories by activity
    top_repositories: List[RepositoryStats]
    
    # Top actors by activity
    top_actors: List[ActorStats]

class QueryParameters(BaseModel):
    """Query parameters for filtering events"""
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    actor_login: Optional[str] = None
    repo_name: Optional[str] = None
    org_login: Optional[str] = None
    is_public: Optional[bool] = None
    hours_back: Optional[int] = Field(default=1, ge=1, le=24)
    page: Optional[int] = Field(default=1, ge=1)
    page_size: Optional[int] = Field(default=100, ge=1, le=1000)

class HealthCheck(BaseModel):
    """Health check response"""
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    components: Dict[str, str]

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime
