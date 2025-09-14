import os
from dotenv import load_dotenv

load_dotenv()


class APIConfig:
    """Configuration for the REST API service."""

    # API Configuration
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', '8003'))
    DEBUG = os.getenv('API_DEBUG', 'false').lower() == 'true'

    # Iceberg Configuration
    ICEBERG_CATALOG_NAME = os.getenv('ICEBERG_CATALOG_NAME', 'github_events')
    ICEBERG_WAREHOUSE_PATH = os.getenv('ICEBERG_WAREHOUSE_PATH', 's3a://iceberg/warehouse')
    ICEBERG_TABLE_NAME = os.getenv('ICEBERG_TABLE_NAME') or f"{ICEBERG_CATALOG_NAME}.github_events.events"

    # Spark Configuration
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'local[*]')

    # MinIO/S3 Configuration
    S3_ENDPOINT = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    S3_SECRET_KEY = os.getenv('S3_SECRET_KEY', 'minioadmin123')

    # Query Configuration
    MAX_RESULTS_LIMIT = int(os.getenv('MAX_RESULTS_LIMIT', '1000'))
    DEFAULT_RESULTS_LIMIT = int(os.getenv('DEFAULT_RESULTS_LIMIT', '100'))
    CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '30'))

    @classmethod
    def get_spark_conf(cls):
        """Get Spark configuration for API service"""
        return {
            'spark.app.name': 'GitHubEventsAPI',
            'spark.master': cls.SPARK_MASTER,
            'spark.jars.packages': 'org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2,software.amazon.awssdk:bundle:2.20.18,org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.12.262',
            'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            # Default catalog to our Iceberg catalog for unqualified table access
            'spark.sql.defaultCatalog': cls.ICEBERG_CATALOG_NAME,
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
            'spark.sql.adaptive.enabled': 'true'
        }
