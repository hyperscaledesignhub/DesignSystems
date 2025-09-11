import asyncio
import json
from datetime import datetime
from typing import List
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
import sys
import os
from fastapi import FastAPI
import uvicorn
from concurrent.futures import ThreadPoolExecutor

sys.path.append('/app')
from shared.config import DataConsumerConfig
from shared.utils import setup_logging, HealthChecker, validate_metric_data
from shared.models import MetricPoint, MetricsBatch

app = FastAPI(title="Data Consumer", version="1.0.0")
logger = setup_logging("data-consumer", DataConsumerConfig.LOG_LEVEL)
health_checker = HealthChecker()

class DataConsumer:
    def __init__(self):
        self.config = DataConsumerConfig()
        self.kafka_consumer = None
        self.influxdb_client = None
        self.write_api = None
        self.running = False
        self.metrics_processed = 0
        self.metrics_failed = 0
        self.batch_buffer = []
        
    async def initialize(self):
        """Initialize connections to Kafka and InfluxDB."""
        try:
            # Initialize Kafka consumer
            self.kafka_consumer = KafkaConsumer(
                self.config.KAFKA_TOPIC_METRICS,
                bootstrap_servers=[self.config.KAFKA_BOOTSTRAP_SERVERS],
                group_id=self.config.CONSUMER_GROUP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=True,
                auto_commit_interval_ms=1000
            )
            logger.info("Connected to Kafka consumer")
            
            # Initialize InfluxDB client
            self.influxdb_client = InfluxDBClient(
                url=self.config.INFLUXDB_URL,
                token=self.config.INFLUXDB_TOKEN,
                org=self.config.INFLUXDB_ORG
            )
            
            # Create write API with batching
            write_options = WriteOptions(
                batch_size=self.config.BATCH_SIZE,
                flush_interval=self.config.FLUSH_INTERVAL * 1000,  # Convert to ms
                jitter_interval=2000,
                retry_interval=5000
            )
            
            self.write_api = self.influxdb_client.write_api(write_options=write_options)
            logger.info("Connected to InfluxDB")
            
            # Register health checks
            health_checker.add_check("kafka", self._check_kafka_health)
            health_checker.add_check("influxdb", self._check_influxdb_health)
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    def _check_kafka_health(self):
        """Check Kafka consumer health."""
        if not self.kafka_consumer:
            raise Exception("Kafka consumer not initialized")
        
        # Check if consumer is subscribed to topics
        topics = self.kafka_consumer.subscription()
        return {"subscribed_topics": list(topics) if topics else []}
    
    def _check_influxdb_health(self):
        """Check InfluxDB connection health."""
        if not self.influxdb_client:
            raise Exception("InfluxDB client not initialized")
        
        # Test connection with a simple query
        health = self.influxdb_client.health()
        return {"status": health.status, "message": health.message}
    
    def convert_to_influxdb_point(self, metric: MetricPoint) -> Point:
        """Convert MetricPoint to InfluxDB Point."""
        point = Point(metric.name) \
            .field("value", metric.value) \
            .time(metric.timestamp)
        
        # Add labels as tags
        for key, value in metric.labels.items():
            point = point.tag(key, value)
        
        return point
    
    def process_metrics_batch(self, batch_data: dict) -> List[Point]:
        """Process a batch of metrics and convert to InfluxDB points."""
        points = []
        
        try:
            # Parse the batch
            batch = MetricsBatch(
                metrics=[MetricPoint.from_dict(m) for m in batch_data["metrics"]],
                source_host=batch_data["source_host"],
                collection_time=datetime.fromisoformat(batch_data["collection_time"])
            )
            
            # Convert each metric to InfluxDB point
            for metric in batch.metrics:
                if validate_metric_data(metric.to_dict()):
                    point = self.convert_to_influxdb_point(metric)
                    points.append(point)
                else:
                    logger.warning(f"Invalid metric data: {metric}")
                    self.metrics_failed += 1
            
        except Exception as e:
            logger.error(f"Failed to process batch: {e}")
            self.metrics_failed += len(batch_data.get("metrics", []))
        
        return points
    
    def write_points_to_influxdb(self, points: List[Point]):
        """Write points to InfluxDB."""
        try:
            if points:
                self.write_api.write(
                    bucket=self.config.INFLUXDB_BUCKET,
                    record=points
                )
                self.metrics_processed += len(points)
                logger.info(f"Written {len(points)} points to InfluxDB")
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
            self.metrics_failed += len(points)
            raise
    
    async def start_consuming(self):
        """Start consuming messages from Kafka."""
        self.running = True
        logger.info("Starting Kafka message consumption")
        
        # Use ThreadPoolExecutor for blocking Kafka operations
        with ThreadPoolExecutor(max_workers=2) as executor:
            while self.running:
                try:
                    # Poll for messages (blocking operation in thread)
                    message_batch = await asyncio.get_event_loop().run_in_executor(
                        executor, self._poll_messages
                    )
                    
                    if message_batch:
                        # Process messages
                        all_points = []
                        for message in message_batch:
                            points = self.process_metrics_batch(message.value)
                            all_points.extend(points)
                        
                        # Write to InfluxDB if we have points
                        if all_points:
                            await asyncio.get_event_loop().run_in_executor(
                                executor, self.write_points_to_influxdb, all_points
                            )
                    
                    # Small delay to prevent tight loop
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Error in consumption loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
    
    def _poll_messages(self, timeout_ms=1000):
        """Poll messages from Kafka (blocking operation)."""
        try:
            message_batch = self.kafka_consumer.poll(timeout_ms=timeout_ms)
            messages = []
            for topic_partition, msgs in message_batch.items():
                messages.extend(msgs)
            return messages
        except Exception as e:
            logger.error(f"Failed to poll messages: {e}")
            return []
    
    def stop(self):
        """Stop the consumer."""
        self.running = False
        if self.kafka_consumer:
            self.kafka_consumer.close()
        if self.write_api:
            self.write_api.close()
        if self.influxdb_client:
            self.influxdb_client.close()

# Global consumer instance
consumer = DataConsumer()

@app.on_event("startup")
async def startup_event():
    """Initialize the consumer on startup."""
    await consumer.initialize()
    # Start consumption loop in background
    asyncio.create_task(consumer.start_consuming())

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    consumer.stop()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await health_checker.run_checks()
        status_code = 200 if health_status["healthy"] else 503
        return {"status_code": status_code, **health_status}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"healthy": False, "error": str(e)}

@app.get("/stats")
async def get_stats():
    """Get consumer statistics."""
    return {
        "metrics_processed": consumer.metrics_processed,
        "metrics_failed": consumer.metrics_failed,
        "running": consumer.running,
        "success_rate": (
            consumer.metrics_processed / (consumer.metrics_processed + consumer.metrics_failed)
            if (consumer.metrics_processed + consumer.metrics_failed) > 0 else 0
        )
    }

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "data-consumer",
        "version": "1.0.0",
        "status": "running" if consumer.running else "stopped",
        "consumer_group": consumer.config.CONSUMER_GROUP
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=DataConsumerConfig.DATA_CONSUMER_PORT,
        log_level=DataConsumerConfig.LOG_LEVEL.lower()
    )