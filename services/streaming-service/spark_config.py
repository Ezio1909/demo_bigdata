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
    
    # Processing Configuration
    CHECKPOINT_LOCATION = os.getenv('CHECKPOINT_LOCATION', '/opt/iceberg/checkpoints')
    TRIGGER_INTERVAL = os.getenv('TRIGGER_INTERVAL', '2 seconds')
    
    # Data retention (1 hour in milliseconds)
    DATA_RETENTION_MS = 3 * 60 * 60 * 1000
    
    @classmethod
    def get_spark_jars(cls):
        """Get required JAR files for Spark"""
        return [
            'org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.4.2',
            'org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.1'
        ]
    
    @classmethod
    def get_spark_conf(cls):
        """Get Spark configuration settings"""
        return {
            'spark.app.name': cls.APP_NAME,
            'spark.master': cls.SPARK_MASTER,
            'spark.jars.packages': ','.join(cls.get_spark_jars()),
            'spark.jars.ivy': '/opt/ivy',
            'spark.sql.extensions': 'org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions',
            'spark.sql.defaultCatalog': cls.ICEBERG_CATALOG_NAME,
            'spark.sql.catalog.spark_catalog': 'org.apache.iceberg.spark.SparkSessionCatalog',
            'spark.sql.catalog.spark_catalog.type': 'hive',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}': 'org.apache.iceberg.spark.SparkCatalog',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.type': 'hadoop',
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.warehouse': cls.ICEBERG_WAREHOUSE_PATH,
            f'spark.sql.catalog.{cls.ICEBERG_CATALOG_NAME}.io-impl': 'org.apache.iceberg.hadoop.HadoopFileIO',
            'spark.serializer': 'org.apache.spark.serializer.KryoSerializer',
            'spark.sql.adaptive.enabled': 'true',
            'spark.sql.adaptive.coalescePartitions.enabled': 'true'
        }
