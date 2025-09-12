import os
try:
    from common.config import settings
except Exception:
    # Fallback: minimal in-module settings if common package not available
    class _Fallback:
        class api:
            host = os.getenv('API_HOST', '0.0.0.0')
            port = int(os.getenv('API_PORT', '8003'))
            debug = os.getenv('API_DEBUG', 'false').lower() == 'true'
        class iceberg:
            catalog_name = os.getenv('ICEBERG_CATALOG_NAME', 'github_events')
            warehouse_path = os.getenv('ICEBERG_WAREHOUSE_PATH', '/opt/iceberg/warehouse')
            table_name = os.getenv('ICEBERG_TABLE_NAME') or f"{os.getenv('ICEBERG_CATALOG_NAME', 'github_events')}.github_events.events"
        class spark:
            master = os.getenv('SPARK_MASTER', 'local[*]')
        class s3:
            endpoint = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
            access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
            secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin123')
    settings = _Fallback()


class APIConfig:
    """Configuration for the REST API service (adapter to common settings)."""

    # API Configuration
    HOST = settings.api.host
    PORT = settings.api.port
    DEBUG = settings.api.debug

    # Iceberg Configuration
    ICEBERG_CATALOG_NAME = settings.iceberg.catalog_name
    ICEBERG_WAREHOUSE_PATH = settings.iceberg.warehouse_path
    ICEBERG_TABLE_NAME = settings.iceberg.table_name

    # Spark Configuration
    SPARK_MASTER = settings.spark.master

    # MinIO/S3 Configuration
    S3_ENDPOINT = settings.s3.endpoint
    S3_ACCESS_KEY = settings.s3.access_key
    S3_SECRET_KEY = settings.s3.secret_key

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
