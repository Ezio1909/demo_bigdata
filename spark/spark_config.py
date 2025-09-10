import os
from dotenv import load_dotenv

load_dotenv()

class SparkConfig:
    """Configuration for Spark Iceberg consumer"""
    
    # Kafka Configuration
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'github-events')
    KAFKA_STARTING_OFFSETS = os.getenv('KAFKA_STARTING_OFFSETS', 'latest')
    
    # Spark Configuration
    APP_NAME = 'GitHubEventsIcebergConsumer'
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'local[*]')
    
    # Iceberg Configuration
    ICEBERG_CATALOG_NAME = 'github_events'
    ICEBERG_WAREHOUSE_PATH = os.getenv('ICEBERG_WAREHOUSE_PATH', '/opt/iceberg/warehouse')
    ICEBERG_TABLE_NAME = f'{ICEBERG_CATALOG_NAME}.github_events.events'
    
    # MinIO/S3 Configuration
    S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'minioadmin123')
    S3_BUCKET = os.getenv('S3_BUCKET', 'iceberg')
    
    # Processing Configuration
    CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/opt/iceberg/checkpoints')
    TRIGGER_INTERVAL = os.getenv('TRIGGER_INTERVAL', '30 seconds')
    
    # Data retention (1 hour in milliseconds)
    DATA_RETENTION_MS = 60 * 60 * 1000
    
    @classmethod
    def get_spark_jars(cls):
        """Get required JAR files for Spark"""
        return [
            'org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2',
            'org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1',
            'software.amazon.awssdk:bundle:2.20.18',
            'software.amazon.awssdk:url-connection-client:2.20.18'
        ]
    
    @classmethod
    def get_spark_conf(cls):
        """Get Spark configuration settings"""
        return {
            'spark.app.name': cls.APP_NAME,
            'spark.master': cls.SPARK_MASTER,
            'spark.jars.packages': ','.join(cls.get_spark_jars()),
            'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            'spark.sql.catalog.spark_catalog': 'org.apache.iceberg.spark.SparkSessionCatalog',
            'spark.sql.catalog.spark_catalog.type': 'hive',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}': 'org.apache.iceberg.spark.SparkCatalog',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.type': 'hadoop',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.warehouse': cls.ICEBERG_WAREHOUSE_PATH,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.io-impl': 'org.apache.iceberg.aws.s3.S3FileIO',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.endpoint': cls.S3_ENDPOINT,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.access-key-id': cls.S3_ACCESS_KEY,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.secret-access-key': cls.S3_SECRET_KEY,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.s3.path-style-access': 'true',
            # Ensure Hadoop S3A can access MinIO for any s3a:// operations
            'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
            'spark.hadoop.fs.s3a.endpoint': cls.S3_ENDPOINT,
            'spark.hadoop.fs.s3a.access.key': cls.S3_ACCESS_KEY,
            'spark.hadoop.fs.s3a.secret.key': cls.S3_SECRET_KEY,
            'spark.hadoop.fs.s3a.path.style.access': 'true',
            'spark.hadoop.fs.s3a.connection.ssl.enabled': 'false',
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            'spark.sql.adaptive.enabled': 'true',
            'spark.sql.adaptive.coalescePartitions.enabled': 'true'
        }
