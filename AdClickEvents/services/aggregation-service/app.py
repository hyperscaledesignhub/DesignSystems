#!/usr/bin/env python3
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import time
import threading
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AggregationService:
    def __init__(self):
        kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9092')
        
        # Kafka consumer for raw events
        try:
            self.consumer = KafkaConsumer(
                'ad-clicks-raw',
                bootstrap_servers=kafka_servers.split(','),
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='aggregation-service',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            logger.info("Connected to Kafka consumer")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka consumer: {e}")
            self.consumer = None
        
        # Kafka producer for aggregated events
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_servers.split(','),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            logger.info("Connected to Kafka producer")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka producer: {e}")
            self.producer = None
        
        # Aggregation windows (1-minute tumbling windows)
        self.window_size = 60  # 1 minute in seconds
        self.current_window = {}
        self.window_start_time = None
        
        # Top N configuration
        self.top_n = int(os.getenv('TOP_N', '10'))
        
        # Thread lock for aggregation data
        self.lock = threading.Lock()
        
        # Start aggregation timer
        self.start_aggregation_timer()
    
    def start_aggregation_timer(self):
        """Start timer for periodic aggregation"""
        def aggregation_worker():
            while True:
                time.sleep(self.window_size)
                self.process_window()
        
        timer_thread = threading.Thread(target=aggregation_worker, daemon=True)
        timer_thread.start()
        logger.info("Started aggregation timer")
    
    def get_window_key(self, timestamp_str):
        """Get window key for timestamp"""
        try:
            # Parse timestamp
            if timestamp_str.endswith('Z'):
                timestamp = datetime.fromisoformat(timestamp_str[:-1])
            else:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', ''))
            
            # Calculate window start (floor to minute)
            window_start = timestamp.replace(second=0, microsecond=0)
            return window_start.isoformat()
            
        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
            # Fallback to current time
            window_start = datetime.now().replace(second=0, microsecond=0)
            return window_start.isoformat()
    
    def process_event(self, event):
        """Process a single ad click event"""
        try:
            ad_id = event.get('ad_id')
            country = event.get('country', 'Unknown')
            timestamp = event.get('click_timestamp')
            
            if not ad_id or not timestamp:
                logger.warning(f"Invalid event: {event}")
                return
            
            window_key = self.get_window_key(timestamp)
            
            with self.lock:
                # Initialize window if needed
                if window_key not in self.current_window:
                    self.current_window[window_key] = {
                        'ads': defaultdict(int),
                        'countries': defaultdict(int),
                        'total_clicks': 0,
                        'events': []
                    }
                
                window_data = self.current_window[window_key]
                
                # Aggregate data
                window_data['ads'][ad_id] += 1
                window_data['countries'][country] += 1
                window_data['total_clicks'] += 1
                
                # Store event for debugging
                window_data['events'].append({
                    'ad_id': ad_id,
                    'country': country,
                    'timestamp': timestamp
                })
                
                logger.debug(f"Aggregated event for window {window_key}: ad={ad_id}, country={country}")
                
        except Exception as e:
            logger.error(f"Error processing event: {e}")
    
    def process_window(self):
        """Process completed windows and send aggregations"""
        current_time = datetime.now()
        completed_windows = []
        
        with self.lock:
            # Find windows that are at least 1 minute old
            for window_key, window_data in self.current_window.items():
                try:
                    window_time = datetime.fromisoformat(window_key)
                    if current_time - window_time >= timedelta(minutes=1):
                        completed_windows.append((window_key, window_data))
                except Exception as e:
                    logger.error(f"Error parsing window key {window_key}: {e}")
            
            # Remove completed windows
            for window_key, _ in completed_windows:
                del self.current_window[window_key]
        
        # Process completed windows
        for window_key, window_data in completed_windows:
            self.send_aggregations(window_key, window_data)
    
    def send_aggregations(self, window_key, window_data):
        """Send aggregation results to Kafka"""
        if not self.producer:
            logger.error("Cannot send aggregations - producer not available")
            return
        
        try:
            # Create aggregation message
            aggregation = {
                'window_start': window_key,
                'window_end': (datetime.fromisoformat(window_key) + timedelta(minutes=1)).isoformat(),
                'total_clicks': window_data['total_clicks'],
                'unique_ads': len(window_data['ads']),
                'countries': dict(window_data['countries']),
                'processing_timestamp': datetime.now().isoformat()
            }
            
            # Send individual ad aggregations
            for ad_id, clicks in window_data['ads'].items():
                ad_aggregation = {
                    **aggregation,
                    'ad_id': ad_id,
                    'clicks': clicks,
                    'type': 'ad_aggregation'
                }
                
                self.producer.send('ad-clicks-aggregated', value=ad_aggregation)
            
            # Send top ads for this window
            top_ads = sorted(window_data['ads'].items(), key=lambda x: x[1], reverse=True)[:self.top_n]
            
            top_ads_aggregation = {
                **aggregation,
                'top_ads': [{'ad_id': ad_id, 'clicks': clicks} for ad_id, clicks in top_ads],
                'type': 'top_ads_aggregation'
            }
            
            self.producer.send('ad-clicks-aggregated', value=top_ads_aggregation)
            
            logger.info(f"Sent aggregations for window {window_key}: "
                       f"{window_data['total_clicks']} total clicks, "
                       f"{len(window_data['ads'])} unique ads")
            
        except Exception as e:
            logger.error(f"Error sending aggregations: {e}")
    
    def start_consuming(self):
        """Start consuming events from Kafka"""
        if not self.consumer:
            logger.error("Cannot start consuming - consumer not available")
            return
        
        logger.info("Starting to consume ad click events...")
        
        try:
            for message in self.consumer:
                event = message.value
                self.process_event(event)
                
                # Process windows periodically during high-volume periods
                if datetime.now().second % 30 == 0:  # Every 30 seconds
                    self.process_window()
                
        except KeyboardInterrupt:
            logger.info("Stopping aggregation service...")
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            if self.producer:
                self.producer.close()

if __name__ == '__main__':
    service = AggregationService()
    service.start_consuming()