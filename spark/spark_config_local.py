import os
from dotenv import load_dotenv

load_dotenv()

class SparkConfig:
    """Configuration for Spark Iceberg consumer - LOCAL FILESYSTEM VERSION"""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'github-events')
    KAFKA_STARTING_OFFSETS = os.getenv('KAFKA_STARTING_OFFSETS', 'latest')
    
    # Spark Configuration
    APP_NAME = 'GitHubEventsIcebergConsumer'
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'local[*]')
    
    # Iceberg Configuration - LOCAL FILESYSTEM
    ICEBERG_CATALOG_NAME = 'github_events'
    USE_LOCAL_FILESYSTEM = os.getenv('USE_LOCAL_FILESYSTEM', 'true').lower() == 'true'
    
    if USE_LOCAL_FILESYSTEM:
        # Local filesystem paths
        ICEBERG_WAREHOUSE_PATH = os.getenv('ICEBERG_WAREHOUSE_PATH', 'file:///opt/iceberg/warehouse')
        CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', 'file:///opt/iceberg/checkpoints')
    else:
        # S3/MinIO paths (fallback)
        ICEBERG_WAREHOUSE_PATH = os.getenv('ICEBERG_WAREHOUSE_PATH', '/opt/iceberg/warehouse')
        CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/opt/iceberg/checkpoints')
    
    ICEBERG_TABLE_NAME = f'{ICEBERG_CATALOG_NAME}.github_events.events'
    
    # Processing Configuration
    TRIGGER_INTERVAL = os.getenv('TRIGGER_INTERVAL', '30 seconds')
    
    # Data retention (1 hour in milliseconds)
    DATA_RETENTION_MS = 60 * 60 * 1000
    
    @classmethod
    def get_spark_jars(cls):
        """Get required JAR files for Spark"""
        jars = [
            'org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2',
            'org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1'
        ]
        
        # Only add AWS JARs if using S3/MinIO
        if not cls.USE_LOCAL_FILESYSTEM:
            jars.extend([
                'software.amazon.awssdk:bundle:2.20.18',
                'software.amazon.awssdk:url-connection-client:2.20.18'
            ])
        
        return jars
    
    @classmethod
    def get_spark_conf(cls):
        """Get Spark configuration settings"""
        base_conf = {
            'spark.app.name': cls.APP_NAME,
            'spark.master': cls.SPARK_MASTER,
            'spark.jars.packages': ','.join(cls.get_spark_jars()),
            'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            'spark.sql.catalog.spark_catalog': 'org.apache.iceberg.spark.SparkSessionCatalog',
            'spark.sql.catalog.spark_catalog.type': 'hive',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}': 'org.apache.iceberg.spark.SparkCatalog',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.type': 'hadoop',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.warehouse': cls.ICEBERG_WAREHOUSE_PATH,
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            'spark.sql.adaptive.enabled': 'true',
            'spark.sql.adaptive.coalescePartitions.enabled': 'true'
        }
        
        # Add S3/MinIO configuration only if not using local filesystem
        if not cls.USE_LOCAL_FILESYSTEM:
            s3_conf = {
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.io-impl': 'org.apache.iceberg.aws.s3.S3FileIO',
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.endpoint': os.getenv('S3_ENDPOINT', 'http://localhost:9000'),
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.access-key-id': os.getenv('S3_ACCESS_KEY', 'minioadmin'),
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.secret-access-key': os.getenv('S3_SECRET_KEY', 'minioadmin123'),
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.path-style-access': 'true'
            }
            base_conf.update(s3_conf)
        else:
            # Local filesystem configuration
            local_conf = {
                f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.io-impl': 'org.apache.iceberg.hadoop.HadoopFileIO'
            }
            base_conf.update(local_conf)
        
        return base_conf
