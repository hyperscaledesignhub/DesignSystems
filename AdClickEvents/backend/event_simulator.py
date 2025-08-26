#!/usr/bin/env python3
import os
import json
import time
import random
import logging
from datetime import datetime
from kafka import KafkaProducer
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EventSimulator:
    def __init__(self):
        kafka_servers = os.getenv('KAFKA_SERVERS', 'localhost:9903,localhost:9904,localhost:9905')
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=kafka_servers.split(','),
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            self.producer = None
        
        self.scenarios = {
            'ecommerce': {
                'ads': ['fashion_ad_001', 'electronics_ad_002', 'home_ad_003', 'books_ad_004'],
                'countries': ['USA', 'Canada', 'UK', 'Germany', 'France'],
                'user_patterns': {
                    'peak_hours': [9, 12, 18, 21],  # Hours with high activity
                    'weekend_boost': 1.3,
                    'mobile_ratio': 0.7
                }
            },
            'gaming': {
                'ads': ['game_ad_001', 'puzzle_ad_002', 'strategy_ad_003', 'arcade_ad_004'],
                'countries': ['USA', 'Japan', 'South Korea', 'China', 'India'],
                'user_patterns': {
                    'peak_hours': [19, 20, 21, 22, 23],
                    'weekend_boost': 1.8,
                    'mobile_ratio': 0.9
                }
            },
            'finance': {
                'ads': ['credit_ad_001', 'loan_ad_002', 'insurance_ad_003', 'investment_ad_004'],
                'countries': ['USA', 'UK', 'Canada', 'Australia', 'Singapore'],
                'user_patterns': {
                    'peak_hours': [9, 10, 11, 14, 15],
                    'weekend_boost': 0.4,
                    'mobile_ratio': 0.4
                }
            },
            'social': {
                'ads': ['social_ad_001', 'influencer_ad_002', 'brand_ad_003', 'event_ad_004'],
                'countries': ['USA', 'Brazil', 'India', 'UK', 'Mexico'],
                'user_patterns': {
                    'peak_hours': [12, 18, 19, 20, 21],
                    'weekend_boost': 1.5,
                    'mobile_ratio': 0.85
                }
            }
        }
        
        self.is_running = False
        self.current_scenario = 'ecommerce'
        self.events_per_second = 10
        self.fraud_rate = 0.05
        
        # User simulation data
        self.user_pool = self.generate_user_pool()
        self.ip_ranges = self.generate_ip_ranges()
    
    def generate_user_pool(self):
        """Generate realistic user pool"""
        users = []
        for i in range(10000):
            users.append({
                'user_id': f"user_{i:06d}",
                'behavior_score': random.uniform(0.1, 1.0),  # 0 = bot-like, 1 = human-like
                'click_frequency': random.choice(['low', 'medium', 'high']),
                'device_type': random.choice(['mobile', 'desktop', 'tablet']),
                'user_agent': self.generate_user_agent()
            })
        return users
    
    def generate_user_agent(self):
        """Generate realistic user agents"""
        agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
            "Mozilla/5.0 (Android 11; Mobile; rv:68.0) Gecko/68.0",
            "Mozilla/5.0 (iPad; CPU OS 14_7_1 like Mac OS X)"
        ]
        return random.choice(agents)
    
    def generate_ip_ranges(self):
        """Generate IP ranges for different countries"""
        return {
            'USA': ['192.168.1.{}', '10.0.1.{}', '172.16.1.{}'],
            'UK': ['192.168.2.{}', '10.0.2.{}'],
            'Canada': ['192.168.3.{}', '10.0.3.{}'],
            'Germany': ['192.168.4.{}', '10.0.4.{}'],
            'France': ['192.168.5.{}'],
            'Japan': ['192.168.6.{}'],
            'South Korea': ['192.168.7.{}'],
            'China': ['192.168.8.{}'],
            'India': ['192.168.9.{}'],
            'Brazil': ['192.168.10.{}'],
            'Australia': ['192.168.11.{}'],
            'Singapore': ['192.168.12.{}'],
            'Mexico': ['192.168.13.{}']
        }
    
    def generate_realistic_event(self):
        """Generate a realistic ad click event"""
        scenario = self.scenarios[self.current_scenario]
        current_hour = datetime.now().hour
        
        # Adjust click probability based on time
        time_multiplier = 1.0
        if current_hour in scenario['user_patterns']['peak_hours']:
            time_multiplier = 1.8
        elif 2 <= current_hour <= 6:  # Low activity hours
            time_multiplier = 0.3
        
        # Select user and determine if this is fraud
        user = random.choice(self.user_pool)
        is_fraud = random.random() < self.fraud_rate
        
        # Generate IP based on country
        country = random.choice(scenario['countries'])
        ip_template = random.choice(self.ip_ranges[country])
        ip_address = ip_template.format(random.randint(1, 254))
        
        # Fraud patterns
        if is_fraud:
            # Fraudulent events have patterns
            if random.random() < 0.3:  # IP clustering
                ip_address = "192.168.99.{}".format(random.randint(1, 10))
            if random.random() < 0.4:  # Bot user agent
                user['user_agent'] = "Bot/1.0"
            if random.random() < 0.2:  # Rapid clicks
                user['behavior_score'] = 0.1
        
        event = {
            'ad_id': random.choice(scenario['ads']),
            'click_timestamp': datetime.now().isoformat(),
            'user_id': user['user_id'],
            'ip_address': ip_address,
            'country': country,
            'user_agent': user['user_agent'],
            'device_type': user['device_type'],
            'behavior_score': user['behavior_score'],
            'session_id': f"session_{random.randint(100000, 999999)}",
            'referrer': random.choice(['google.com', 'facebook.com', 'direct', 'twitter.com']),
            'is_fraud': is_fraud,  # This would not be in real data
            'campaign_id': f"campaign_{random.randint(1, 4)}",
            'bid_amount': round(random.uniform(0.10, 2.00), 2),
            'conversion_value': round(random.uniform(5.00, 100.00), 2) if random.random() < 0.15 else 0
        }
        
        return event
    
    def start_simulation(self, scenario='ecommerce', events_per_second=10):
        """Start the event simulation"""
        self.current_scenario = scenario
        self.events_per_second = events_per_second
        self.is_running = True
        
        logger.info(f"Starting simulation: {scenario} scenario, {events_per_second} events/sec")
        
        simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        simulation_thread.start()
    
    def stop_simulation(self):
        """Stop the event simulation"""
        self.is_running = False
        logger.info("Stopping simulation")
    
    def _simulation_loop(self):
        """Main simulation loop"""
        events_sent = 0
        
        while self.is_running:
            try:
                # Generate and send events
                for _ in range(self.events_per_second):
                    if not self.is_running:
                        break
                    
                    event = self.generate_realistic_event()
                    
                    if self.producer:
                        # Send to Kafka
                        self.producer.send('ad-clicks-raw', event)
                        events_sent += 1
                    
                    # Log progress
                    if events_sent % 100 == 0:
                        logger.info(f"Sent {events_sent} events")
                
                time.sleep(1)  # Sleep for 1 second
                
            except Exception as e:
                logger.error(f"Error in simulation loop: {e}")
                time.sleep(5)  # Wait before retrying
        
        logger.info(f"Simulation stopped. Total events sent: {events_sent}")
    
    def generate_burst_traffic(self, duration_seconds=60, burst_multiplier=5):
        """Generate burst traffic for demo purposes"""
        original_rate = self.events_per_second
        self.events_per_second = original_rate * burst_multiplier
        
        logger.info(f"Starting burst traffic for {duration_seconds} seconds")
        time.sleep(duration_seconds)
        
        self.events_per_second = original_rate
        logger.info("Burst traffic ended")
    
    def simulate_fraud_attack(self, duration_seconds=30):
        """Simulate a fraud attack scenario"""
        original_fraud_rate = self.fraud_rate
        self.fraud_rate = 0.8  # 80% fraud rate
        
        logger.info(f"Starting fraud attack simulation for {duration_seconds} seconds")
        time.sleep(duration_seconds)
        
        self.fraud_rate = original_fraud_rate
        logger.info("Fraud attack simulation ended")

if __name__ == '__main__':
    simulator = EventSimulator()
    
    # Start simulation with default parameters
    simulator.start_simulation('ecommerce', 20)
    
    try:
        # Keep running
        while True:
            time.sleep(10)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        simulator.stop_simulation()
        if simulator.producer:
            simulator.producer.close()