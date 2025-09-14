#!/usr/bin/env python3
"""
Spark Streaming Service API
Provides REST API for controlling the Spark streaming job (Kafka → Iceberg)
"""

import logging
import sys
import threading
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Import Spark components
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, count, countDistinct, desc, date_trunc,
    collect_list
)
from spark_config import SparkConfig
from event_processor import GitHubEventProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StreamingStatus(BaseModel):
    status: str
    is_running: bool
    start_time: Optional[datetime] = None
    total_events_processed: int = 0
    total_batches_processed: int = 0
    errors: int = 0
    last_batch_time: Optional[datetime] = None
    checkpoint_location: str

class StreamingConfig(BaseModel):
    trigger_interval: str = "30 seconds"
    max_events_per_batch: int = 1000

app = FastAPI(
    title="Spark Streaming Service API",
    description="REST API for controlling Spark streaming job",
    version="1.0.0"
)

# Enable CORS for the dashboard on a different origin (e.g., http://localhost:8080)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)

# Global streaming state
streaming_status = StreamingStatus(
    status="stopped",
    is_running=False,
    checkpoint_location=SparkConfig.CHECKPOINT_LOCATION
)

# Spark components
spark: Optional[SparkSession] = None
processor: Optional[GitHubEventProcessor] = None
streaming_query = None
streaming_thread: Optional[threading.Thread] = None

# ------------------------------
# Dashboard models (for frontend)
# ------------------------------

class GitHubEvent(BaseModel):
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
    events: List[GitHubEvent]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class EventTypeStats(BaseModel):
    event_type: str
    count: int
    percentage: float

class EventCategoryStats(BaseModel):
    event_category: str
    count: int
    percentage: float

class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    count: int

class RepositoryStats(BaseModel):
    repo_name: str
    repo_id: int
    event_count: int
    unique_actors: int
    event_types: List[str]

class ActorStats(BaseModel):
    actor_login: str
    actor_id: int
    event_count: int
    repo_count: int
    event_types: List[str]

class DashboardStats(BaseModel):
    total_events: int
    unique_repositories: int
    unique_actors: int
    event_types_count: int
    last_updated: datetime
    time_range_hours: int
    event_type_stats: List[EventTypeStats]
    event_category_stats: List[EventCategoryStats]
    hourly_events: List[TimeSeriesPoint]
    top_repositories: List[RepositoryStats]
    top_actors: List[ActorStats]

class QueryParameters(BaseModel):
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    actor_login: Optional[str] = None
    repo_name: Optional[str] = None
    org_login: Optional[str] = None
    is_public: Optional[bool] = None
    hours_back: Optional[int] = Field(default=1, ge=1, le=24)
    page: Optional[int] = Field(default=1, ge=1)
    page_size: Optional[int] = Field(default=100, ge=1, le=1000)

def initialize_spark():
    """Initialize Spark session"""
    global spark, processor
    
    try:
        builder = SparkSession.builder
        
        # Apply all configuration settings
        for key, value in SparkConfig.get_spark_conf().items():
            builder = builder.config(key, value)
        
        spark = builder.getOrCreate()
        spark.sparkContext.setLogLevel("WARN")
        
        logger.info("Spark session initialized successfully")
        
        # Initialize event processor
        processor = GitHubEventProcessor(spark)
        
        # Create Iceberg catalog and database if they don't exist
        setup_iceberg_catalog()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Spark session: {e}")
        return False

def setup_iceberg_catalog():
    """Set up Iceberg catalog and database"""
    try:
        # Create database if it doesn't exist
        database_name = SparkConfig.ICEBERG_CATALOG_NAME + ".github_events"
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        logger.info(f"Database {database_name} ready")
        
        # Create table if it doesn't exist
        table_name = SparkConfig.ICEBERG_TABLE_NAME
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            event_id STRING,
            event_type STRING,
            event_category STRING,
            created_at TIMESTAMP,
            processed_at TIMESTAMP,
            actor_id INT,
            actor_login STRING,
            actor_avatar_url STRING,
            repo_id INT,
            repo_name STRING,
            repo_url STRING,
            org_id INT,
            org_login STRING,
            is_public BOOLEAN,
            action STRING,
            ref STRING,
            ref_type STRING,
            master_branch STRING,
            description STRING,
            pusher_type STRING,
            payload_json STRING,
            processing_date STRING,
            processing_hour INT,
            has_actor BOOLEAN,
            has_repo BOOLEAN,
            has_org BOOLEAN
        ) USING iceberg
        PARTITIONED BY (processing_date, processing_hour)
        TBLPROPERTIES (
            'write.target-file-size-bytes'='134217728',
            'write.delete.mode'='merge-on-read'
        )
        """
        
        spark.sql(create_table_sql)
        logger.info(f"Iceberg table {table_name} ready")
        
    except Exception as e:
        logger.error(f"Failed to setup Iceberg catalog: {e}")
        raise


# ------------------------------
# Helper functions for dashboard
# ------------------------------

def _load_events_df(hours_back: int) -> DataFrame:
    if not spark:
        raise Exception("Spark not initialized")
    cutoff = datetime.now().timestamp() - (hours_back * 3600)
    # Use fully-qualified table name
    table = SparkConfig.ICEBERG_TABLE_NAME
    df = spark.read.format("iceberg").load(table)
    # Filter by created_at >= cutoff
    return df.filter(col("created_at") >= datetime.fromtimestamp(cutoff))

def _apply_filters(df: DataFrame, params: QueryParameters) -> DataFrame:
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

def _df_to_events(df: DataFrame) -> List[GitHubEvent]:
    events = []
    for row in df.collect():
        events.append(GitHubEvent(**row.asDict()))
    return events

def streaming_worker():
    """Background worker that runs Spark streaming"""
    global streaming_query, streaming_status
    
    try:
        streaming_status.status = "running"
        streaming_status.start_time = datetime.now()
        
        logger.info("Spark streaming worker started")
        
        # Read from Kafka
        kafka_df = spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", SparkConfig.KAFKA_BOOTSTRAP_SERVERS) \
            .option("subscribe", SparkConfig.KAFKA_TOPIC) \
            .option("startingOffsets", SparkConfig.KAFKA_STARTING_OFFSETS) \
            .option("failOnDataLoss", "false") \
            .load()
        
        logger.info(f"Started reading from Kafka topic: {SparkConfig.KAFKA_TOPIC}")
        
        # Process the stream
        processed_df = processor.process_kafka_stream(kafka_df)
        processed_df = processor.add_data_quality_checks(processed_df)
        processed_df = processor.prepare_for_iceberg(processed_df)
        
        # Write to Iceberg table
        streaming_query = processed_df.writeStream \
            .format("iceberg") \
            .outputMode("append") \
            .option("path", SparkConfig.ICEBERG_TABLE_NAME) \
            .option("checkpointLocation", SparkConfig.CHECKPOINT_LOCATION) \
            .trigger(processingTime=SparkConfig.TRIGGER_INTERVAL) \
            .start()
        
        logger.info(f"Started streaming to Iceberg table: {SparkConfig.ICEBERG_TABLE_NAME}")
        
        # Monitor streaming
        while streaming_query.isActive:
            streaming_query.awaitTermination(timeout=30)
            
            # Update status
            progress = streaming_query.lastProgress
            if progress:
                streaming_status.total_batches_processed += 1
                streaming_status.last_batch_time = datetime.now()
                
                input_rows = progress.get('inputRowsPerSecond', 0)
                processed_rows = progress.get('processedRowsPerSecond', 0)
                
                if input_rows > 0:
                    streaming_status.total_events_processed += int(input_rows)
                
                logger.debug(f"Streaming progress: input={input_rows}, processed={processed_rows}")
        
    except Exception as e:
        logger.error(f"Error in streaming worker: {e}")
        streaming_status.status = "error"
        streaming_status.errors += 1
    finally:
        streaming_status.status = "stopped"
        streaming_status.is_running = False
        logger.info("Spark streaming worker stopped")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "streaming_status": streaming_status.status,
        "spark_initialized": spark is not None
    }

@app.get("/status", response_model=StreamingStatus)
async def get_status():
    """Get current streaming status"""
    return streaming_status

@app.post("/start")
async def start_streaming():
    """Start the Spark streaming job"""
    global streaming_thread
    
    if streaming_status.is_running:
        raise HTTPException(status_code=400, detail="Streaming is already running")
    
    if not initialize_spark():
        raise HTTPException(status_code=500, detail="Failed to initialize Spark")
    
    # Start streaming thread
    streaming_thread = threading.Thread(target=streaming_worker, daemon=True)
    streaming_thread.start()
    
    streaming_status.is_running = True
    
    logger.info("Spark streaming started via API")
    
    return {
        "message": "Spark streaming started successfully",
        "status": streaming_status.status
    }

@app.post("/stop")
async def stop_streaming():
    """Stop the Spark streaming job"""
    global streaming_query
    
    if not streaming_status.is_running:
        raise HTTPException(status_code=400, detail="Streaming is not running")
    
    # Stop streaming query
    if streaming_query and streaming_query.isActive:
        streaming_query.stop()
        streaming_query.awaitTermination(timeout=30)
    
    streaming_status.is_running = False
    streaming_status.status = "stopped"
    
    logger.info("Spark streaming stopped via API")
    
    return {
        "message": "Spark streaming stopped successfully",
        "status": streaming_status.status
    }

@app.post("/config")
async def update_config(config: StreamingConfig):
    """Update streaming configuration"""
    try:
        # Update configuration
        SparkConfig.TRIGGER_INTERVAL = config.trigger_interval
        
        logger.info("Streaming configuration updated")
        
        return {
            "message": "Configuration updated successfully",
            "config": {
                "trigger_interval": SparkConfig.TRIGGER_INTERVAL,
                "checkpoint_location": SparkConfig.CHECKPOINT_LOCATION
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")

@app.get("/stats")
async def get_stats():
    """Get detailed streaming statistics"""
    uptime = None
    if streaming_status.start_time:
        uptime = (datetime.now() - streaming_status.start_time).total_seconds()
    
    return {
        "status": streaming_status.status,
        "is_running": streaming_status.is_running,
        "uptime_seconds": uptime,
        "total_events_processed": streaming_status.total_events_processed,
        "total_batches_processed": streaming_status.total_batches_processed,
        "errors": streaming_status.errors,
        "last_batch_time": streaming_status.last_batch_time,
        "checkpoint_location": streaming_status.checkpoint_location,
        "trigger_interval": SparkConfig.TRIGGER_INTERVAL,
        "kafka_topic": SparkConfig.KAFKA_TOPIC,
        "iceberg_table": SparkConfig.ICEBERG_TABLE_NAME
    }

@app.get("/table/info")
async def get_table_info():
    """Get information about the Iceberg table"""
    if not spark:
        raise HTTPException(status_code=500, detail="Spark not initialized")
    
    try:
        # Get table information
        table_name = SparkConfig.ICEBERG_TABLE_NAME
        table_info = spark.sql(f"DESCRIBE TABLE {table_name}").collect()
        
        # Get record count
        count_result = spark.sql(f"SELECT COUNT(*) as total_records FROM {table_name}").collect()
        total_records = count_result[0]['total_records'] if count_result else 0
        
        return {
            "table_name": table_name,
            "total_records": total_records,
            "schema": [{"column": row['col_name'], "type": row['data_type']} for row in table_info]
        }
        
    except Exception as e:
        logger.error(f"Failed to get table info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table info: {e}")


# ------------------------------
# Minimal dashboard endpoints
# ------------------------------

@app.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(hours_back: int = Query(1, ge=1, le=24)):
    try:
        df = _load_events_df(hours_back)
        # Basic stats
        agg = df.agg(
            count("*").alias("total_events"),
            countDistinct("repo_id").alias("unique_repositories"),
            countDistinct("actor_id").alias("unique_actors"),
            countDistinct("event_type").alias("event_types_count")
        ).collect()[0]

        # Event type stats
        type_df = df.groupBy("event_type").agg(count("*").alias("count")).orderBy(desc("count"))
        total_events = agg["total_events"] or 0
        type_stats = []
        for row in type_df.collect():
            pct = 0.0 if total_events == 0 else round((row["count"] / total_events) * 100, 2)
            type_stats.append(EventTypeStats(event_type=row["event_type"], count=row["count"], percentage=pct))

        # Event category stats
        cat_df = df.groupBy("event_category").agg(count("*").alias("count")).orderBy(desc("count"))
        cat_stats = []
        for row in cat_df.collect():
            pct = 0.0 if total_events == 0 else round((row["count"] / total_events) * 100, 2)
            cat_stats.append(EventCategoryStats(event_category=row["event_category"], count=row["count"], percentage=pct))

        # Hourly series
        hourly = df.groupBy(date_trunc("hour", col("created_at")).alias("hour")).agg(count("*").alias("count")).orderBy("hour")
        series = [TimeSeriesPoint(timestamp=row["hour"], count=row["count"]) for row in hourly.collect()]

        # Top repos
        repos_df = df.filter(col("repo_name").isNotNull()).groupBy("repo_name", "repo_id").agg(
            count("*").alias("event_count"),
            countDistinct("actor_id").alias("unique_actors"),
            collect_list("event_type").alias("event_types_list")
        ).orderBy(desc("event_count")).limit(10)
        repos = [
            RepositoryStats(
                repo_name=row["repo_name"],
                repo_id=row["repo_id"],
                event_count=row["event_count"],
                unique_actors=row["unique_actors"],
                event_types=list(set(row["event_types_list"]))
            ) for row in repos_df.collect()
        ]

        # Top actors
        actors_df = df.filter(col("actor_login").isNotNull()).groupBy("actor_login", "actor_id").agg(
            count("*").alias("event_count"),
            countDistinct("repo_id").alias("repo_count"),
            collect_list("event_type").alias("event_types_list")
        ).orderBy(desc("event_count")).limit(10)
        actors = [
            ActorStats(
                actor_login=row["actor_login"],
                actor_id=row["actor_id"],
                event_count=row["event_count"],
                repo_count=row["repo_count"],
                event_types=list(set(row["event_types_list"]))
            ) for row in actors_df.collect()
        ]

        return DashboardStats(
            total_events=total_events,
            unique_repositories=agg["unique_repositories"] or 0,
            unique_actors=agg["unique_actors"] or 0,
            event_types_count=agg["event_types_count"] or 0,
            last_updated=datetime.now(),
            time_range_hours=hours_back,
            event_type_stats=type_stats,
            event_category_stats=cat_stats,
            hourly_events=series,
            top_repositories=repos,
            top_actors=actors
        )
    except Exception as e:
        logger.error(f"dashboard_stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/events", response_model=EventsResponse)
async def dashboard_events(
    event_type: Optional[str] = None,
    event_category: Optional[str] = None,
    actor_login: Optional[str] = None,
    repo_name: Optional[str] = None,
    org_login: Optional[str] = None,
    is_public: Optional[bool] = None,
    hours_back: int = Query(1, ge=1, le=24),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
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
        df = _apply_filters(_load_events_df(params.hours_back), params)
        total = df.count()
        # Pagination
        offset = (params.page - 1) * params.page_size
        # Spark doesn't have offset; approximate via window: simplest is order then limit after collecting small pages.
        rows = df.orderBy(desc("created_at")).limit(offset + params.page_size).collect()[offset:offset + params.page_size]
        events = [GitHubEvent(**r.asDict()) for r in rows]
        return EventsResponse(
            events=events,
            total_count=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )
    except Exception as e:
        logger.error(f"dashboard_events error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root aliases for filters placed before main so they register at startup
@app.get("/event-types", response_model=List[str])
async def event_types(hours_back: int = Query(24, ge=1, le=24)):
    return await dashboard_event_types(hours_back)

@app.get("/event-categories", response_model=List[str])
async def event_categories(hours_back: int = Query(24, ge=1, le=24)):
    return await dashboard_event_categories(hours_back)

@app.get("/dashboard/event-types", response_model=List[str])
async def dashboard_event_types(hours_back: int = Query(24, ge=1, le=24)):
    try:
        df = _load_events_df(hours_back)
        rows = df.select("event_type").distinct().collect()
        return [r["event_type"] for r in rows if r["event_type"]]
    except Exception as e:
        logger.error(f"dashboard_event_types error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/event-categories", response_model=List[str])
async def dashboard_event_categories(hours_back: int = Query(24, ge=1, le=24)):
    try:
        df = _load_events_df(hours_back)
        rows = df.select("event_category").distinct().collect()
        return [r["event_category"] for r in rows if r["event_category"]]
    except Exception as e:
        logger.error(f"dashboard_event_categories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root aliases for filters
@app.get("/event-types", response_model=List[str])
async def event_types(hours_back: int = Query(24, ge=1, le=24)):
    return await dashboard_event_types(hours_back)

@app.get("/event-categories", response_model=List[str])
async def event_categories(hours_back: int = Query(24, ge=1, le=24)):
    return await dashboard_event_categories(hours_back)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Spark Streaming Service API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "start": "/start",
            "stop": "/stop",
            "config": "/config",
            "stats": "/stats",
            "table_info": "/table/info",
            "documentation": "/docs"
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize Spark on startup"""
    logger.info("Starting Spark Streaming Service API")
    initialize_spark()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Streaming API")
    
    # Stop streaming if running
    if streaming_status.is_running and streaming_query:
        streaming_query.stop()
    
    # Stop Spark session
    if spark:
        spark.stop()

def main():
    """Main entry point"""
    logger.info("Starting Spark Streaming Service API")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )

if __name__ == "__main__":
    main()
