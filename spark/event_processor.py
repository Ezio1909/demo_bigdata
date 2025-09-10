import json
from datetime import datetime
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, from_json, to_timestamp, current_timestamp,
    date_format, hour, get_json_object, when, lit
)
from pyspark.sql.types import StringType
from schema import get_github_event_schema, get_flattened_event_schema, EVENT_TYPE_CATEGORIES

class GitHubEventProcessor:
    """Processes GitHub events from Kafka and prepares them for Iceberg storage"""
    
    def __init__(self, spark_session):
        self.spark = spark_session
        self.github_event_schema = get_github_event_schema()
        self.flattened_schema = get_flattened_event_schema()
    
    def process_kafka_stream(self, kafka_df: DataFrame) -> DataFrame:
        """
        Process raw Kafka stream data and convert to structured GitHub events
        """
        # Parse JSON from Kafka value
        parsed_df = kafka_df.select(
            col("key").cast(StringType()).alias("kafka_key"),
            col("value").cast(StringType()).alias("raw_json"),
            col("timestamp").alias("kafka_timestamp"),
            col("partition").alias("kafka_partition"),
            col("offset").alias("kafka_offset")
        )
        
        # Parse the GitHub event JSON
        events_df = parsed_df.select(
            "*",
            from_json(col("raw_json"), self.github_event_schema).alias("event")
        ).filter(col("event").isNotNull())
        
        # Flatten the event structure for easier querying
        flattened_df = self._flatten_github_event(events_df)
        
        return flattened_df
    
    def _flatten_github_event(self, events_df: DataFrame) -> DataFrame:
        """
        Flatten GitHub event structure into a more queryable format
        """
        
        flattened_df = events_df.select(
            # Event identifiers
            col("event.id").alias("event_id"),
            col("event.type").alias("event_type"),
            to_timestamp(col("event.created_at")).alias("created_at"),
            to_timestamp(col("event.processed_at")).alias("processed_at"),
            
            # Actor information
            col("event.actor.id").alias("actor_id"),
            col("event.actor.login").alias("actor_login"),
            col("event.actor.avatar_url").alias("actor_avatar_url"),
            
            # Repository information
            col("event.repo.id").alias("repo_id"),
            col("event.repo.name").alias("repo_name"),
            col("event.repo.url").alias("repo_url"),
            
            # Organization information (optional)
            col("event.org.id").alias("org_id"),
            col("event.org.login").alias("org_login"),
            
            # Event metadata
            col("event.public").alias("is_public"),
            
            # Extract common payload fields
            get_json_object(col("raw_json"), "$.payload.action").alias("action"),
            get_json_object(col("raw_json"), "$.payload.ref").alias("ref"),
            get_json_object(col("raw_json"), "$.payload.ref_type").alias("ref_type"),
            get_json_object(col("raw_json"), "$.payload.master_branch").alias("master_branch"),
            get_json_object(col("raw_json"), "$.payload.description").alias("description"),
            get_json_object(col("raw_json"), "$.payload.pusher_type").alias("pusher_type"),
            
            # Keep full payload as JSON for complex analysis
            get_json_object(col("raw_json"), "$.payload").alias("payload_json"),
            
            # Processing metadata for partitioning
            date_format(current_timestamp(), "yyyy-MM-dd").alias("processing_date"),
            hour(current_timestamp()).alias("processing_hour"),
            
            # Kafka metadata
            col("kafka_timestamp"),
            col("kafka_partition"),
            col("kafka_offset")
        )
        
        # Add event category based on type
        flattened_df = flattened_df.withColumn(
            "event_category",
            self._categorize_event_type(col("event_type"))
        )
        
        return flattened_df
    
    def _categorize_event_type(self, event_type_col):
        """
        Categorize event types into broader categories
        """
        category_expr = lit("other")  # default category
        
        for event_type, category in EVENT_TYPE_CATEGORIES.items():
            category_expr = when(event_type_col == event_type, lit(category)).otherwise(category_expr)
        
        return category_expr
    
    def add_data_quality_checks(self, df: DataFrame) -> DataFrame:
        """
        Add data quality checks and filters
        """
        # Filter out events without required fields
        quality_df = df.filter(
            col("event_id").isNotNull() &
            col("event_type").isNotNull() &
            col("created_at").isNotNull()
        )
        
        # Add data quality flags
        quality_df = quality_df.withColumn(
            "has_actor", col("actor_id").isNotNull()
        ).withColumn(
            "has_repo", col("repo_id").isNotNull()
        ).withColumn(
            "has_org", col("org_id").isNotNull()
        )
        
        return quality_df
    
    def prepare_for_iceberg(self, df: DataFrame) -> DataFrame:
        """
        Final preparation for writing to Iceberg table
        """
        # Ensure proper data types and handle nulls
        prepared_df = df.select(
            col("event_id"),
            col("event_type"),
            col("event_category"),
            col("created_at"),
            col("processed_at"),
            col("actor_id"),
            col("actor_login"),
            col("actor_avatar_url"),
            col("repo_id"),
            col("repo_name"),
            col("repo_url"),
            col("org_id"),
            col("org_login"),
            col("is_public"),
            col("action"),
            col("ref"),
            col("ref_type"),
            col("master_branch"),
            col("description"),
            col("pusher_type"),
            col("payload_json"),
            col("processing_date"),
            col("processing_hour"),
            col("has_actor"),
            col("has_repo"),
            col("has_org")
        )
        
        return prepared_df
