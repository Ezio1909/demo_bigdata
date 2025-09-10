import json
import logging
from typing import List, Dict
from kafka import KafkaProducer
from kafka.errors import KafkaError
from config import Config

logger = logging.getLogger(__name__)

class GitHubEventsKafkaProducer:
    """Kafka producer for GitHub events"""
    
    def __init__(self):
        self.producer = None
        self.topic = Config.KAFKA_TOPIC
        self._initialize_producer()
    
    def _initialize_producer(self):
        """Initialize Kafka producer with proper configuration"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS.split(','),
                value_serializer=lambda x: json.dumps(x, default=str).encode('utf-8'),
                key_serializer=lambda x: x.encode('utf-8') if x else None,
                # Reliability settings
                acks='all',  # Wait for all replicas to acknowledge
                retries=3,
                retry_backoff_ms=1000,
                # Performance settings
                batch_size=16384,
                linger_ms=100,
                compression_type='gzip',
                # Error handling
                request_timeout_ms=30000
            )
            logger.info(f"Kafka producer initialized successfully. Topic: {self.topic}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def send_events(self, events: List[Dict]) -> int:
        """
        Send GitHub events to Kafka topic
        Returns the number of successfully sent events
        """
        if not events:
            return 0
        
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return 0
        
        sent_count = 0
        failed_count = 0
        
        for event in events:
            try:
                # Use event ID as the key for partitioning
                event_id = event.get('id', '')
                
                # Send to Kafka
                future = self.producer.send(
                    self.topic,
                    key=event_id,
                    value=event
                )
                
                # Add callback for success/failure tracking
                future.add_callback(self._on_send_success)
                future.add_errback(self._on_send_error)
                
                sent_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send event {event.get('id', 'unknown')}: {e}")
                failed_count += 1
        
        # Ensure all messages are sent
        try:
            self.producer.flush(timeout=30)
            logger.info(f"Successfully queued {sent_count} events to Kafka topic '{self.topic}'")
            
            if failed_count > 0:
                logger.warning(f"Failed to send {failed_count} events")
                
        except Exception as e:
            logger.error(f"Failed to flush Kafka producer: {e}")
        
        return sent_count
    
    def _on_send_success(self, record_metadata):
        """Callback for successful message delivery"""
        logger.debug(f"Message sent successfully to {record_metadata.topic} "
                    f"partition {record_metadata.partition} offset {record_metadata.offset}")
    
    def _on_send_error(self, exception):
        """Callback for failed message delivery"""
        logger.error(f"Failed to send message to Kafka: {exception}")
    
    def close(self):
        """Close the Kafka producer"""
        if self.producer:
            try:
                self.producer.flush(timeout=30)
                self.producer.close(timeout=30)
                logger.info("Kafka producer closed successfully")
            except Exception as e:
                logger.error(f"Error closing Kafka producer: {e}")
    
    def get_metrics(self) -> Dict:
        """Get producer metrics"""
        if not self.producer:
            return {}
        
        try:
            metrics = self.producer.metrics()
            return {
                'connection_count': metrics.get('kafka-metrics-count', {}).get('connection-count', 0),
                'record_send_rate': metrics.get('producer-metrics', {}).get('record-send-rate', 0),
                'record_error_rate': metrics.get('producer-metrics', {}).get('record-error-rate', 0)
            }
        except Exception as e:
            logger.error(f"Failed to get producer metrics: {e}")
            return {}
