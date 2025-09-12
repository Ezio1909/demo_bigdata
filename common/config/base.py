import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class KafkaSettings:
    bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic: str = os.getenv('KAFKA_TOPIC', 'github-events')


@dataclass
class SparkSettings:
    app_name: str = os.getenv('SPARK_APP_NAME', 'GitHubEventsApp')
    master: str = os.getenv('SPARK_MASTER', 'local[*]')


@dataclass
class IcebergSettings:
    catalog_name: str = os.getenv('ICEBERG_CATALOG_NAME', 'github_events')
    warehouse_path: str = os.getenv('ICEBERG_WAREHOUSE_PATH', '/opt/iceberg/warehouse')
    table_name: str = os.getenv('ICEBERG_TABLE_NAME', None) or f"{os.getenv('ICEBERG_CATALOG_NAME', 'github_events')}.github_events.events"


@dataclass
class S3Settings:
    endpoint: str = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
    access_key: str = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    secret_key: str = os.getenv('S3_SECRET_KEY', 'minioadmin123')
    path_style_access: bool = True
    ssl_enabled: bool = False


@dataclass
class APISettings:
    host: str = os.getenv('API_HOST', '0.0.0.0')
    port: int = int(os.getenv('API_PORT', '8000'))
    debug: bool = os.getenv('API_DEBUG', 'false').lower() == 'true'


@dataclass
class Settings:
    kafka: KafkaSettings = KafkaSettings()
    spark: SparkSettings = SparkSettings()
    iceberg: IcebergSettings = IcebergSettings()
    s3: S3Settings = S3Settings()
    api: APISettings = APISettings()


settings = Settings()

