#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseWriter:
    def __init__(self):
        # Kafka configuration
        kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9092')
        
        try:
            self.consumer = KafkaConsumer(
                'ad-clicks-aggregated',
                bootstrap_servers=kafka_servers.split(','),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='database-writer',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info("Connected to Kafka consumer")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self.consumer = None
        
        # InfluxDB configuration
        influx_host = os.getenv('INFLUXDB_HOST', 'localhost')
        influx_port = os.getenv('INFLUXDB_PORT', '8086')
        self.influx_url = f"http://{influx_host}:{influx_port}"
        self.influx_token = os.getenv('INFLUXDB_TOKEN', 'demo-token')
        self.influx_org = os.getenv('INFLUXDB_ORG', 'demo-org')
        self.influx_bucket = os.getenv('INFLUXDB_BUCKET', 'adclick-demo')
        
        try:
            self.influx_client = InfluxDBClient(
                url=self.influx_url,
                token=self.influx_token,
                org=self.influx_org
            )
            
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info(f"Connected to InfluxDB: {self.influx_url}")
            
            # Test connection
            health = self.influx_client.health()
            logger.info(f"InfluxDB health: {health.status}")
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            self.influx_client = None
            self.write_api = None
        
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.batch_buffer = []
    
    def write_ad_aggregation(self, data):
        """Write individual ad aggregation to InfluxDB"""
        try:
            point = Point("ad_clicks") \
                .tag("ad_id", data['ad_id']) \
                .field("count", data['clicks']) \
                .field("total_clicks", data['total_clicks']) \
                .field("unique_ads", data['unique_ads']) \
                .time(data['window_start'], WritePrecision.S)
            
            # Add country information if available
            for country, count in data.get('countries', {}).items():
                point.field(f"country_{country}", count)
            
            self.batch_buffer.append(point)
            logger.debug(f"Added ad aggregation to batch: {data['ad_id']} = {data['clicks']} clicks")
            
        except Exception as e:
            logger.error(f"Error creating ad aggregation point: {e}")
    
    def write_top_ads_aggregation(self, data):
        """Write top ads aggregation to InfluxDB"""
        try:
            # Store the top ads list as JSON
            top_ads_json = json.dumps(data['top_ads'])
            
            point = Point("top_ads") \
                .field("ads_list", top_ads_json) \
                .field("total_clicks", data['total_clicks']) \
                .field("window_duration", 60) \
                .time(data['window_start'], WritePrecision.S)
            
            self.batch_buffer.append(point)
            logger.debug(f"Added top ads aggregation to batch: {len(data['top_ads'])} ads")
            
        except Exception as e:
            logger.error(f"Error creating top ads point: {e}")
    
    def write_country_aggregation(self, data):
        """Write country-level aggregations"""
        try:
            for country, count in data.get('countries', {}).items():
                point = Point("country_clicks") \
                    .tag("country", country) \
                    .field("count", count) \
                    .field("percentage", (count / data['total_clicks']) * 100 if data['total_clicks'] > 0 else 0) \
                    .time(data['window_start'], WritePrecision.S)
                
                self.batch_buffer.append(point)
            
            logger.debug(f"Added country aggregations to batch: {len(data.get('countries', {}))} countries")
            
        except Exception as e:
            logger.error(f"Error creating country aggregation points: {e}")
    
    def flush_batch(self):
        """Write batch to InfluxDB"""
        if not self.write_api or not self.batch_buffer:
            return
        
        try:
            self.write_api.write(
                bucket=self.influx_bucket,
                org=self.influx_org,
                record=self.batch_buffer
            )
            
            logger.info(f"Wrote batch of {len(self.batch_buffer)} points to InfluxDB")
            self.batch_buffer.clear()
            
        except Exception as e:
            logger.error(f"Error writing batch to InfluxDB: {e}")
            # Clear buffer on error to prevent memory buildup
            self.batch_buffer.clear()
    
    def process_aggregation(self, data):
        """Process aggregation message"""
        try:
            aggregation_type = data.get('type', 'unknown')
            
            if aggregation_type == 'ad_aggregation':
                self.write_ad_aggregation(data)
                self.write_country_aggregation(data)
                
            elif aggregation_type == 'top_ads_aggregation':
                self.write_top_ads_aggregation(data)
            
            else:
                logger.warning(f"Unknown aggregation type: {aggregation_type}")
            
            # Flush batch if it's full
            if len(self.batch_buffer) >= self.batch_size:
                self.flush_batch()
                
        except Exception as e:
            logger.error(f"Error processing aggregation: {e}")
    
    def start_consuming(self):
        """Start consuming aggregated events"""
        if not self.consumer:
            logger.error("Cannot start consuming - consumer not available")
            return
        
        if not self.write_api:
            logger.error("Cannot start consuming - InfluxDB not available")
            return
        
        logger.info("Starting to consume aggregated events...")
        
        try:
            for message in self.consumer:
                aggregation = message.value
                self.process_aggregation(aggregation)
                
        except KeyboardInterrupt:
            logger.info("Stopping database writer...")
            # Flush remaining data
            self.flush_batch()
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            if self.influx_client:
                self.influx_client.close()

if __name__ == '__main__':
    writer = DatabaseWriter()
    writer.start_consuming()