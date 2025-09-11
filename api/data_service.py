import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import threading
import time
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, count, countDistinct, desc, asc, collect_list,
    date_trunc, hour, max as spark_max, min as spark_min,
    sum as spark_sum, avg, stddev, percentile_approx
)
from config import APIConfig
from models import (
    GitHubEvent, DashboardStats, EventTypeStats, EventCategoryStats,
    TimeSeriesPoint, RepositoryStats, ActorStats, QueryParameters
)

logger = logging.getLogger(__name__)

class GitHubEventsDataService:
    """Service for querying GitHub events data from Iceberg"""
    
    def __init__(self):
        self.spark: Optional[SparkSession] = None
        self.table_name = APIConfig.ICEBERG_TABLE_NAME
        # In-memory cache for precomputed metrics and recent events (24h only for dashboard push)
        self.metrics_cache: Dict[int, Optional[DashboardStats]] = {24: None}
        self.metrics_updated_at: Dict[int, Optional[datetime]] = {24: None}
        self.recent_events_cache: Dict[int, List[GitHubEvent]] = {24: []}
        self._cache_lock = threading.Lock()
        self._cache_thread: Optional[threading.Thread] = None
        
    def initialize(self) -> bool:
        """Initialize Spark session"""
        try:
            builder = SparkSession.builder
            
            for key, value in APIConfig.get_spark_conf().items():
                builder = builder.config(key, value)
            
            self.spark = builder.getOrCreate()
            self.spark.sparkContext.setLogLevel("WARN")
            
            logger.info("Data service initialized successfully")
            # Start background cache updater
            self._start_cache_updater()
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize data service: {e}")
            return False

    def _start_cache_updater(self, refresh_seconds: int = 1):
        if self._cache_thread and self._cache_thread.is_alive():
            return
        def _worker():
            logger.info("Metrics cache updater started (24h window)")
            while True:
                try:
                    hours = 24
                    stats = self._compute_dashboard_stats(hours)
                    events = self._compute_recent_events(hours, 200)
                    with self._cache_lock:
                        self.metrics_cache[hours] = stats
                        self.metrics_updated_at[hours] = datetime.now()
                        self.recent_events_cache[hours] = events
                except Exception as e:
                    logger.error(f"Cache updater error: {e}")
                time.sleep(refresh_seconds)
        self._cache_thread = threading.Thread(target=_worker, daemon=True)
        self._cache_thread.start()
    
    def get_events(self, params: QueryParameters) -> Tuple[List[GitHubEvent], int]:
        """Get events with filtering and pagination"""
        try:
            # Serve from in-memory cache to avoid live Spark calls during requests
            hours = params.hours_back or 1
            with self._cache_lock:
                cached = list(self.recent_events_cache.get(hours, []))
            # Apply filters in Python
            def match(e: GitHubEvent) -> bool:
                return (
                    (not params.event_type or e.event_type == params.event_type) and
                    (not params.event_category or e.event_category == params.event_category) and
                    (not params.actor_login or e.actor_login == params.actor_login) and
                    (not params.repo_name or e.repo_name == params.repo_name) and
                    (not params.org_login or e.org_login == params.org_login) and
                    (params.is_public is None or e.is_public == params.is_public)
                )
            filtered = [e for e in cached if match(e)]
            total = len(filtered)
            start = (params.page - 1) * params.page_size
            end = start + params.page_size
            return filtered[start:end], total
            
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return [], 0
    
    def get_dashboard_stats(self, hours_back: int = 1) -> Optional[DashboardStats]:
        """Get comprehensive dashboard statistics"""
        try:
            # Force 24h window for dashboard
            hours_back = 24
            with self._cache_lock:
                cached = self.metrics_cache.get(hours_back)
            if cached:
                return cached
            return self._compute_dashboard_stats(hours_back)
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return None

    # Internal compute helpers used by background thread
    def _compute_dashboard_stats(self, hours_back: int) -> Optional[DashboardStats]:
        if not self.spark:
            raise Exception("Spark session not initialized")
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        # Ensure we read the latest Iceberg snapshot and not a cached plan
        try:
            self.spark.catalog.refreshTable(self.table_name)
        except Exception:
            pass
        df = self.spark.table(self.table_name)
        df = df.filter(col("created_at") >= cutoff_time)
        basic_stats = df.agg(
            count("*").alias("total_events"),
            countDistinct("repo_id").alias("unique_repositories"),
            countDistinct("actor_id").alias("unique_actors"),
            countDistinct("event_type").alias("event_types_count")
        ).collect()[0]
        event_type_stats = self._get_event_type_stats(df)
        event_category_stats = self._get_event_category_stats(df)
        hourly_events = self._get_hourly_time_series(df)
        top_repositories = self._get_top_repositories(df, limit=10)
        top_actors = self._get_top_actors(df, limit=10)
        return DashboardStats(
            total_events=basic_stats["total_events"],
            unique_repositories=basic_stats["unique_repositories"],
            unique_actors=basic_stats["unique_actors"],
            event_types_count=basic_stats["event_types_count"],
            last_updated=datetime.now(),
            time_range_hours=hours_back,
            event_type_stats=event_type_stats,
            event_category_stats=event_category_stats,
            hourly_events=hourly_events,
            top_repositories=top_repositories,
            top_actors=top_actors
        )

    def _compute_recent_events(self, hours_back: int, max_items: int = 200) -> List[GitHubEvent]:
        if not self.spark:
            return []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        try:
            self.spark.catalog.refreshTable(self.table_name)
        except Exception:
            pass
        df = self.spark.table(self.table_name)
        df = df.filter(col("created_at") >= cutoff_time)
        df = df.orderBy(desc("created_at")).limit(max_items)
        return self._dataframe_to_events(df)
    
    def get_event_types(self) -> List[str]:
        """Get list of available event types"""
        try:
            if not self.spark:
                return []
            
            df = self.spark.table(self.table_name)
            types = df.select("event_type").distinct().collect()
            return [row["event_type"] for row in types if row["event_type"]]
            
        except Exception as e:
            logger.error(f"Error getting event types: {e}")
            return []
    
    def get_event_categories(self) -> List[str]:
        """Get list of available event categories"""
        try:
            if not self.spark:
                return []
            
            df = self.spark.table(self.table_name)
            categories = df.select("event_category").distinct().collect()
            return [row["event_category"] for row in categories if row["event_category"]]
            
        except Exception as e:
            logger.error(f"Error getting event categories: {e}")
            return []
    
    def health_check(self) -> Dict[str, str]:
        """Check health of data service"""
        try:
            components = {}
            
            # Check Spark session
            if self.spark:
                components["spark"] = "healthy"
            else:
                components["spark"] = "unhealthy"
            
            # Check table accessibility
            try:
                if self.spark:
                    df = self.spark.table(self.table_name)
                    count = df.count()
                    components["iceberg_table"] = f"healthy ({count} records)"
                else:
                    components["iceberg_table"] = "unhealthy - no spark session"
            except Exception as e:
                components["iceberg_table"] = f"unhealthy - {str(e)}"
            
            return components
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return {"error": str(e)}
    
    def _apply_filters(self, df: DataFrame, params: QueryParameters) -> DataFrame:
        """Apply query filters to DataFrame"""
        if params.event_type:
            df = df.filter(col("event_type") == params.event_type)
        
        if params.event_category:
            df = df.filter(col("event_category") == params.event_category)
        
        if params.actor_login:
            df = df.filter(col("actor_login") == params.actor_login)
        
        if params.repo_name:
            df = df.filter(col("repo_name") == params.repo_name)
        
        if params.org_login:
            df = df.filter(col("org_login") == params.org_login)
        
        if params.is_public is not None:
            df = df.filter(col("is_public") == params.is_public)
        
        return df
    
    def _dataframe_to_events(self, df: DataFrame) -> List[GitHubEvent]:
        """Convert DataFrame to list of GitHubEvent objects"""
        try:
            rows = df.collect()
            events = []
            
            for row in rows:
                event = GitHubEvent(
                    event_id=row.event_id,
                    event_type=row.event_type,
                    event_category=row.event_category,
                    created_at=row.created_at,
                    processed_at=row.processed_at,
                    actor_id=row.actor_id,
                    actor_login=row.actor_login,
                    actor_avatar_url=row.actor_avatar_url,
                    repo_id=row.repo_id,
                    repo_name=row.repo_name,
                    repo_url=row.repo_url,
                    org_id=row.org_id,
                    org_login=row.org_login,
                    is_public=row.is_public,
                    action=row.action,
                    ref=row.ref,
                    ref_type=row.ref_type,
                    master_branch=row.master_branch,
                    description=row.description,
                    pusher_type=row.pusher_type,
                    payload_json=row.payload_json,
                    processing_date=row.processing_date,
                    processing_hour=row.processing_hour,
                    has_actor=row.has_actor,
                    has_repo=row.has_repo,
                    has_org=row.has_org
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error converting DataFrame to events: {e}")
            return []
    
    def _get_event_type_stats(self, df: DataFrame) -> List[EventTypeStats]:
        """Get event type statistics"""
        try:
            total_events = df.count()
            if total_events == 0:
                return []
            
            stats_df = df.groupBy("event_type").agg(
                count("*").alias("count")
            ).orderBy(desc("count"))
            
            stats = []
            for row in stats_df.collect():
                stats.append(EventTypeStats(
                    event_type=row.event_type,
                    count=row["count"],
                    percentage=round((row["count"] / total_events) * 100, 2)
                ))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting event type stats: {e}")
            return []
    
    def _get_event_category_stats(self, df: DataFrame) -> List[EventCategoryStats]:
        """Get event category statistics"""
        try:
            total_events = df.count()
            if total_events == 0:
                return []
            
            stats_df = df.groupBy("event_category").agg(
                count("*").alias("count")
            ).orderBy(desc("count"))
            
            stats = []
            for row in stats_df.collect():
                stats.append(EventCategoryStats(
                    event_category=row.event_category,
                    count=row["count"],
                    percentage=round((row["count"] / total_events) * 100, 2)
                ))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting event category stats: {e}")
            return []
    
    def _get_hourly_time_series(self, df: DataFrame) -> List[TimeSeriesPoint]:
        """Get hourly time series data"""
        try:
            hourly_df = df.groupBy(
                date_trunc("hour", col("created_at")).alias("hour")
            ).agg(
                count("*").alias("count")
            ).orderBy("hour")
            
            points = []
            for row in hourly_df.collect():
                points.append(TimeSeriesPoint(
                    timestamp=row.hour,
                    count=int(row["count"]) if isinstance(row["count"], (int,)) else row["count"]
                ))
            
            return points
            
        except Exception as e:
            logger.error(f"Error getting hourly time series: {e}")
            return []
    
    def _get_top_repositories(self, df: DataFrame, limit: int = 10) -> List[RepositoryStats]:
        """Get top repositories by activity"""
        try:
            repo_df = df.filter(col("repo_name").isNotNull()).groupBy("repo_name", "repo_id").agg(
                count("*").alias("event_count"),
                countDistinct("actor_id").alias("unique_actors"),
                collect_list("event_type").alias("event_types_list")
            ).orderBy(desc("event_count")).limit(limit)
            
            repos = []
            for row in repo_df.collect():
                repos.append(RepositoryStats(
                    repo_name=row.repo_name,
                    repo_id=row.repo_id,
                    event_count=row.event_count,
                    unique_actors=row.unique_actors,
                    event_types=list(set(row.event_types_list))  # Remove duplicates
                ))
            
            return repos
            
        except Exception as e:
            logger.error(f"Error getting top repositories: {e}")
            return []
    
    def _get_top_actors(self, df: DataFrame, limit: int = 10) -> List[ActorStats]:
        """Get top actors by activity"""
        try:
            actor_df = df.filter(col("actor_login").isNotNull()).groupBy("actor_login", "actor_id").agg(
                count("*").alias("event_count"),
                countDistinct("repo_id").alias("repo_count"),
                collect_list("event_type").alias("event_types_list")
            ).orderBy(desc("event_count")).limit(limit)
            
            actors = []
            for row in actor_df.collect():
                actors.append(ActorStats(
                    actor_login=row.actor_login,
                    actor_id=row.actor_id,
                    event_count=row.event_count,
                    repo_count=row.repo_count,
                    event_types=list(set(row.event_types_list))  # Remove duplicates
                ))
            
            return actors
            
        except Exception as e:
            logger.error(f"Error getting top actors: {e}")
            return []
    
    def close(self):
        """Close Spark session"""
        if self.spark:
            self.spark.stop()
            logger.info("Data service closed")
