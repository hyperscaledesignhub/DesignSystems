#!/usr/bin/env python3
import os
import json
import time
import logging
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from kafka import KafkaProducer
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdClickLogHandler(FileSystemEventHandler):
    def __init__(self, producer):
        self.producer = producer
        self.processed_lines = {}  # Track processed lines per file
        
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith('.log'):
            self.process_log_file(event.src_path)
    
    def process_log_file(self, file_path):
        """Process new lines in log file"""
        try:
            with open(file_path, 'r') as file:
                # Get current line count
                lines = file.readlines()
                current_line_count = len(lines)
                
                # Get last processed line count for this file
                last_processed = self.processed_lines.get(file_path, 0)
                
                # Process only new lines
                if current_line_count > last_processed:
                    new_lines = lines[last_processed:]
                    
                    for line in new_lines:
                        self.parse_and_send_event(line.strip())
                    
                    # Update processed line count
                    self.processed_lines[file_path] = current_line_count
                    logger.info(f"Processed {len(new_lines)} new lines from {file_path}")
                    
        except Exception as e:
            logger.error(f"Error processing log file {file_path}: {e}")
    
    def parse_and_send_event(self, line):
        """Parse log line and send to Kafka"""
        if not line:
            return
        
        try:
            # Expected format: ad_id,timestamp,user_id,ip_address,country
            parts = line.split(',')
            
            if len(parts) >= 5:
                event = {
                    'ad_id': parts[0].strip(),
                    'click_timestamp': parts[1].strip(),
                    'user_id': parts[2].strip(),
                    'ip_address': parts[3].strip(),
                    'country': parts[4].strip(),
                    'parsed_timestamp': datetime.now().isoformat(),
                    'source_file': 'log_watcher'
                }
                
                # Send to Kafka
                self.producer.send('ad-clicks-raw', value=event)
                logger.debug(f"Sent event: {event}")
            else:
                logger.warning(f"Invalid log format: {line}")
                
        except Exception as e:
            logger.error(f"Error parsing line '{line}': {e}")

class LogWatcher:
    def __init__(self):
        # Kafka configuration
        kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9092')
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_servers.split(','),
                value_serializer=lambda x: json.dumps(x).encode('utf-8'),
                batch_size=16384,
                linger_ms=10
            )
            logger.info(f"Connected to Kafka: {kafka_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self.producer = None
        
        # Watch directory
        self.watch_dir = os.getenv('LOG_DIR', '/var/log/adclick')
        if not os.path.exists(self.watch_dir):
            os.makedirs(self.watch_dir)
            logger.info(f"Created watch directory: {self.watch_dir}")
        
        # File watcher
        self.observer = Observer()
        self.handler = AdClickLogHandler(self.producer)
    
    def start_watching(self):
        """Start watching log files"""
        if not self.producer:
            logger.error("Cannot start watching - Kafka producer not available")
            return
        
        logger.info(f"Starting to watch directory: {self.watch_dir}")
        
        # Process existing files first
        self.process_existing_files()
        
        # Start watching for new changes
        self.observer.schedule(self.handler, self.watch_dir, recursive=True)
        self.observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping log watcher...")
            self.observer.stop()
            if self.producer:
                self.producer.close()
        
        self.observer.join()
    
    def process_existing_files(self):
        """Process existing log files"""
        try:
            for filename in os.listdir(self.watch_dir):
                if filename.endswith('.log'):
                    file_path = os.path.join(self.watch_dir, filename)
                    logger.info(f"Processing existing file: {file_path}")
                    self.handler.process_log_file(file_path)
        except Exception as e:
            logger.error(f"Error processing existing files: {e}")

if __name__ == '__main__':
    watcher = LogWatcher()
    watcher.start_watching()