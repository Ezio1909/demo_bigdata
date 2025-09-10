from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, 
    BooleanType, TimestampType, ArrayType, MapType
)

def get_github_event_schema():
    """
    Define the schema for GitHub events based on GitHub API v3 event structure
    """
    
    # Actor schema (user who performed the action)
    actor_schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("login", StringType(), True),
        StructField("display_login", StringType(), True),
        StructField("gravatar_id", StringType(), True),
        StructField("url", StringType(), True),
        StructField("avatar_url", StringType(), True)
    ])
    
    # Repository schema
    repo_schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("name", StringType(), True),
        StructField("url", StringType(), True)
    ])
    
    # Organization schema (optional)
    org_schema = StructType([
        StructField("id", IntegerType(), True),
        StructField("login", StringType(), True),
        StructField("gravatar_id", StringType(), True),
        StructField("url", StringType(), True),
        StructField("avatar_url", StringType(), True)
    ])
    
    # Main event schema
    github_event_schema = StructType([
        StructField("id", StringType(), False),  # Event ID - required
        StructField("type", StringType(), False),  # Event type - required
        StructField("actor", actor_schema, True),
        StructField("repo", repo_schema, True),
        StructField("org", org_schema, True),
        StructField("payload", MapType(StringType(), StringType()), True),  # Flexible payload
        StructField("public", BooleanType(), True),
        StructField("created_at", StringType(), True),  # ISO timestamp string
        StructField("processed_at", StringType(), True)  # Our processing timestamp
    ])
    
    return github_event_schema

def get_flattened_event_schema():
    """
    Define a flattened schema for easier querying and analytics
    """
    
    flattened_schema = StructType([
        # Event identifiers
        StructField("event_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("created_at", TimestampType(), True),
        StructField("processed_at", TimestampType(), True),
        
        # Actor information
        StructField("actor_id", IntegerType(), True),
        StructField("actor_login", StringType(), True),
        StructField("actor_avatar_url", StringType(), True),
        
        # Repository information
        StructField("repo_id", IntegerType(), True),
        StructField("repo_name", StringType(), True),
        StructField("repo_url", StringType(), True),
        
        # Organization information (optional)
        StructField("org_id", IntegerType(), True),
        StructField("org_login", StringType(), True),
        
        # Event metadata
        StructField("is_public", BooleanType(), True),
        
        # Common payload fields (extracted from JSON)
        StructField("action", StringType(), True),  # For events with actions
        StructField("ref", StringType(), True),     # For push events
        StructField("ref_type", StringType(), True), # For create/delete events
        StructField("master_branch", StringType(), True), # For create events
        StructField("description", StringType(), True),   # For create events
        StructField("pusher_type", StringType(), True),   # For push events
        
        # Additional payload as JSON string for complex cases
        StructField("payload_json", StringType(), True),
        
        # Processing metadata
        StructField("processing_date", StringType(), True),  # Date partition
        StructField("processing_hour", IntegerType(), True)   # Hour partition
    ])
    
    return flattened_schema

# Event type mappings for better categorization
EVENT_TYPE_CATEGORIES = {
    'PushEvent': 'code',
    'PullRequestEvent': 'code',
    'IssuesEvent': 'issues',
    'IssueCommentEvent': 'issues',
    'WatchEvent': 'social',
    'ForkEvent': 'social',
    'CreateEvent': 'repository',
    'DeleteEvent': 'repository',
    'PublicEvent': 'repository',
    'ReleaseEvent': 'releases',
    'MemberEvent': 'collaboration',
    'TeamEvent': 'collaboration',
    'CommitCommentEvent': 'code',
    'PullRequestReviewEvent': 'code',
    'PullRequestReviewCommentEvent': 'code'
}
