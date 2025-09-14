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
    ICEBERG_WAREHOUSE_PATH = os.getenv('ICEBERG_WAREHOUSE_PATH', '/opt/iceberg/warehouse')
    ICEBERG_TABLE_NAME = os.getenv('ICEBERG_TABLE_NAME') or f"{ICEBERG_CATALOG_NAME}.github_events.events"

    # Spark Configuration
    SPARK_MASTER = os.getenv('SPARK_MASTER', 'local[*]')

    # Local filesystem mode: no S3 credentials required

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
            'spark.jars.packages': 'org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2',
            'spark.jars.ivy': '/home/appuser/.ivy2',
            'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            # Default catalog to our Iceberg catalog for unqualified table access
            'spark.sql.defaultCatalog': cls.ICEBERG_CATALOG_NAME,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}': 'org.apache.iceberg.spark.SparkCatalog',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.type': 'hadoop',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.warehouse': cls.ICEBERG_WAREHOUSE_PATH,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.io-impl': 'org.apache.iceberg.hadoop.HadoopFileIO',
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            'spark.sql.adaptive.enabled': 'true'
        }
