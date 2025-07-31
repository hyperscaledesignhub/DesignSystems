#!/usr/bin/env python3
"""
Realistic Traffic Generator for Distributed Database Demos
Creates authentic user behavior patterns and continuous activity
"""

import asyncio
import aiohttp
import json
import time
import random
import threading
from datetime import datetime, timedelta
import names
import queue
import logging
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealisticTrafficGenerator:
    def __init__(self, cluster_nodes: List[str]):
        self.cluster_nodes = cluster_nodes
        self.active_sessions = {}
        self.traffic_patterns = {}
        self.running = False
        self.stats = {
            'total_operations': 0,
            'operations_per_second': 0,
            'active_users': 0,
            'errors': 0
        }
        
    async def start_traffic_generation(self):
        """Start realistic traffic generation for all demos"""
        self.running = True
        
        # Start different traffic patterns concurrently
        tasks = [
            self.generate_twitter_traffic(),
            self.generate_collab_editor_traffic(),
            self.generate_inventory_traffic(),
            self.generate_background_activity(),
            self.monitor_performance()
        ]
        
        await asyncio.gather(*tasks)
    
    async def generate_twitter_traffic(self):
        """Generate realistic Twitter-like social media traffic"""
        tweet_templates = [
            "Just launched our new product! 🚀 #{hashtag}",
            "Amazing sunset today! 🌅 #{location}",
            "Working on something exciting... 💻 #{tech}",
            "Coffee break thoughts ☕ #{random}",
            "Weekend vibes! 🎉 #{weekend}",
            "Learning something new every day 📚 #{education}",
            "Great meeting with the team today! 👥 #{work}",
            "Can't wait for the holidays! 🎄 #{holiday}"
        ]
        
        hashtags = ["tech", "startup", "life", "coding", "AI", "travel", "food", "nature"]
        locations = ["NYC", "LA", "Tokyo", "London", "Paris", "SF", "Austin", "Miami"]
        
        while self.running:
            try:
                # Create realistic tweets with varying popularity
                for _ in range(random.randint(2, 8)):
                    tweet_content = random.choice(tweet_templates).format(
                        hashtag=random.choice(hashtags),
                        location=random.choice(locations),
                        tech=random.choice(["Python", "JavaScript", "AI", "ML", "Blockchain"]),
                        random=random.choice(["motivation", "inspiration", "thoughts"]),
                        weekend=random.choice(["Saturday", "Sunday", "fun", "relax"]),
                        education=random.choice(["programming", "design", "business"]),
                        work=random.choice(["productive", "collaboration", "innovation"]),
                        holiday=random.choice(["vacation", "family", "celebration"])
                    )
                    
                    await self.create_realistic_tweet(tweet_content)
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                
                # Generate engagement on existing tweets
                await self.generate_tweet_engagement()
                
                await asyncio.sleep(random.uniform(3, 8))
                
            except Exception as e:
                logger.error(f"Error in Twitter traffic generation: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)
    
    async def create_realistic_tweet(self, content: str):
        """Create a tweet with realistic metadata"""
        author_names = ["@elonmusk", "@sundarpichai", "@satyanadella", "@tim_cook", "@jeffbezos", 
                       "@sundararaman", "@karpathy", "@ylecun", "@goodfellow_ian", "@lexfridman"]
        
        tweet_data = {
            "author": random.choice(author_names),
            "content": content,
            "timestamp": time.time(),
            "location": random.choice(["San Francisco", "New York", "Seattle", "Austin", "London"]),
            "verified": random.choice([True, False, False])  # Most users not verified
        }
        
        try:
            node = random.choice(self.cluster_nodes)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{node}/api/twitter/create",
                    json=tweet_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            # Store tweet for later engagement
                            tweet_id = result.get('tweet_id')
                            self.traffic_patterns[tweet_id] = {
                                'created_at': time.time(),
                                'engagement_rate': random.uniform(0.1, 5.0),  # 0.1% to 5% engagement
                                'viral_potential': random.uniform(0, 100)
                            }
                            self.stats['total_operations'] += 1
                            logger.info(f"Created tweet: {tweet_id}")
                            
        except Exception as e:
            logger.error(f"Error creating tweet: {e}")
            self.stats['errors'] += 1
    
    async def generate_tweet_engagement(self):
        """Generate realistic engagement patterns on tweets"""
        engagement_types = ['likes', 'retweets', 'comments', 'views']
        
        # Simulate different user behavior patterns
        user_behaviors = [
            {'type': 'casual', 'engagement_rate': 0.5, 'burst_probability': 0.1},
            {'type': 'power_user', 'engagement_rate': 2.0, 'burst_probability': 0.3},
            {'type': 'bot', 'engagement_rate': 10.0, 'burst_probability': 0.8},
            {'type': 'influencer', 'engagement_rate': 0.8, 'burst_probability': 0.4}
        ]
        
        for tweet_id, pattern in list(self.traffic_patterns.items()):
            age_hours = (time.time() - pattern['created_at']) / 3600
            
            # Tweets get less engagement as they age
            age_factor = max(0.1, 1.0 - (age_hours / 24))
            
            # Viral tweets get exponential engagement
            viral_factor = 1.0
            if pattern['viral_potential'] > 80:
                viral_factor = random.uniform(5, 20)
            elif pattern['viral_potential'] > 60:
                viral_factor = random.uniform(2, 5)
            
            total_engagement = int(pattern['engagement_rate'] * age_factor * viral_factor)
            
            if total_engagement > 0:
                for _ in range(min(total_engagement, 50)):  # Limit to prevent overwhelming
                    behavior = random.choice(user_behaviors)
                    action = random.choice(engagement_types)
                    
                    # Different probabilities for different actions
                    action_weights = {'views': 10, 'likes': 3, 'retweets': 1, 'comments': 1}
                    if random.random() < action_weights.get(action, 1) / 15:
                        await self.engage_with_tweet(tweet_id, action, behavior['type'])
                        await asyncio.sleep(random.uniform(0.1, 1.0))
    
    async def engage_with_tweet(self, tweet_id: str, action: str, user_type: str):
        """Generate realistic engagement with a tweet"""
        try:
            node = random.choice(self.cluster_nodes)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{node}/api/twitter/engage",
                    json={
                        "tweet_id": tweet_id,
                        "action": action,
                        "user_type": user_type,
                        "timestamp": time.time()
                    },
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        self.stats['total_operations'] += 1
                        logger.debug(f"Engagement: {action} on {tweet_id} by {user_type}")
                        
        except Exception as e:
            logger.error(f"Error engaging with tweet {tweet_id}: {e}")
            self.stats['errors'] += 1
    
    async def generate_collab_editor_traffic(self):
        """Generate realistic collaborative editing traffic"""
        document_templates = [
            "Product Requirements Document",
            "Marketing Strategy 2024",
            "Engineering Roadmap",
            "Budget Planning Q1",
            "Team Meeting Notes",
            "Project Proposal",
            "Technical Specification",
            "User Research Findings"
        ]
        
        users = [
            {"name": "Alice", "role": "Product Manager", "edit_frequency": 2.0},
            {"name": "Bob", "role": "Engineer", "edit_frequency": 1.5},
            {"name": "Charlie", "role": "Designer", "edit_frequency": 1.0},
            {"name": "Diana", "role": "Marketing", "edit_frequency": 0.8},
            {"name": "Eve", "role": "Data Scientist", "edit_frequency": 1.2}
        ]
        
        while self.running:
            try:
                # Create new documents periodically
                if random.random() < 0.3:  # 30% chance to create new doc
                    doc_title = random.choice(document_templates)
                    await self.create_realistic_document(doc_title)
                
                # Generate collaborative editing activity
                await self.simulate_collaborative_editing(users)
                
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Error in collaborative editor traffic: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)
    
    async def create_realistic_document(self, title: str):
        """Create a document with realistic initial content"""
        try:
            node = random.choice(self.cluster_nodes)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{node}/api/collab/create",
                    json={"title": title},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            doc_id = result.get('doc_id')
                            logger.info(f"Created document: {doc_id}")
                            
                            # Add initial content to paragraphs
                            await self.add_initial_content(doc_id)
                            
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            self.stats['errors'] += 1
    
    async def add_initial_content(self, doc_id: str):
        """Add realistic initial content to document paragraphs"""
        initial_content = {
            "para_1": "Executive Summary: This document outlines the key objectives and strategic approach for the upcoming initiative.",
            "para_2": "Background: Based on market research and user feedback, we have identified significant opportunities for improvement.",
            "para_3": "Proposed Solution: We recommend implementing a comprehensive approach that addresses core user needs.",
            "para_4": "Timeline: The project is expected to span 3-6 months with key milestones at regular intervals.",
            "para_5": "Next Steps: Immediate actions include stakeholder alignment and resource allocation."
        }
        
        for para_id, content in initial_content.items():
            try:
                node = random.choice(self.cluster_nodes)
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"http://{node}/api/collab/edit",
                        json={
                            "doc_id": doc_id,
                            "para_id": para_id,
                            "content": content,
                            "author": "System"
                        },
                        timeout=aiohttp.ClientTimeout(total=3)
                    ) as response:
                        if response.status == 200:
                            self.stats['total_operations'] += 1
                            
                await asyncio.sleep(random.uniform(0.2, 0.8))
                
            except Exception as e:
                logger.error(f"Error adding initial content: {e}")
                self.stats['errors'] += 1
    
    async def simulate_collaborative_editing(self, users: List[Dict]):
        """Simulate realistic collaborative editing patterns"""
        # Pick random users for this editing session
        active_users = random.sample(users, random.randint(1, 3))
        
        for user in active_users:
            if random.random() < user['edit_frequency'] / 10:  # Probability of editing
                await self.simulate_user_edit(user)
                await asyncio.sleep(random.uniform(1, 5))
    
    async def simulate_user_edit(self, user: Dict):
        """Simulate a realistic edit by a specific user"""
        # For demo purposes, we'll use a known document ID pattern
        # In real implementation, we'd track created documents
        doc_id = f"doc_{int(time.time() // 3600)}"  # Hourly document buckets
        
        paragraphs = ["para_1", "para_2", "para_3", "para_4", "para_5"]
        para_id = random.choice(paragraphs)
        
        # Generate realistic content based on user role
        content_by_role = {
            "Product Manager": [
                "Updated requirements based on stakeholder feedback.",
                "Revised timeline to accommodate new priorities.",
                "Added success metrics and KPIs for measurement.",
                "Clarified scope and deliverables for the team."
            ],
            "Engineer": [
                "Technical implementation details added.",
                "Identified potential technical risks and mitigation strategies.",
                "Estimated development effort and resource requirements.",
                "Proposed architecture and technology stack considerations."
            ],
            "Designer": [
                "User experience considerations and design principles.",
                "Accessibility requirements and guidelines.",
                "Visual design direction and brand alignment.",
                "User research insights and design recommendations."
            ],
            "Marketing": [
                "Market positioning and competitive analysis.",
                "Go-to-market strategy and launch timeline.",
                "Target audience identification and messaging.",
                "Marketing channels and campaign considerations."
            ],
            "Data Scientist": [
                "Data requirements and analytics framework.",
                "Metrics collection and measurement strategy.",
                "A/B testing framework and success criteria.",
                "Data privacy and compliance considerations."
            ]
        }
        
        content = random.choice(content_by_role.get(user['role'], ["Generic content update."]))
        
        try:
            node = random.choice(self.cluster_nodes)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://{node}/api/collab/edit",
                    json={
                        "doc_id": doc_id,
                        "para_id": para_id,
                        "content": content,
                        "author": user['name']
                    },
                    timeout=aiohttp.ClientTimeout(total=3)
                ) as response:
                    if response.status == 200:
                        self.stats['total_operations'] += 1
                        logger.info(f"{user['name']} edited {para_id}")
                        
        except Exception as e:
            logger.error(f"Error simulating user edit: {e}")
            self.stats['errors'] += 1
    
    async def generate_inventory_traffic(self):
        """Generate realistic inventory management traffic"""
        products = [
            {"id": "iphone-14-pro", "name": "iPhone 14 Pro", "base_stock": 500},
            {"id": "macbook-pro", "name": "MacBook Pro M2", "base_stock": 200},
            {"id": "airpods-pro", "name": "AirPods Pro", "base_stock": 1000},
            {"id": "ipad-air", "name": "iPad Air", "base_stock": 300},
            {"id": "apple-watch", "name": "Apple Watch", "base_stock": 400}
        ]
        
        while self.running:
            try:
                # Simulate different types of inventory operations
                operation_types = [
                    ('order', 0.6),      # 60% orders
                    ('shipment', 0.2),   # 20% shipments
                    ('transfer', 0.15),  # 15% transfers
                    ('adjustment', 0.05) # 5% adjustments
                ]
                
                # Time-based patterns (more orders during business hours)
                current_hour = datetime.now().hour
                if 9 <= current_hour <= 17:  # Business hours
                    operation_multiplier = 2.0
                elif 20 <= current_hour <= 23:  # Evening shopping
                    operation_multiplier = 1.5
                else:  # Night/early morning
                    operation_multiplier = 0.3
                
                operations_this_cycle = int(random.uniform(3, 10) * operation_multiplier)
                
                for _ in range(operations_this_cycle):
                    operation = random.choices(
                        [op[0] for op in operation_types],
                        weights=[op[1] for op in operation_types]
                    )[0]
                    
                    product = random.choice(products)
                    await self.simulate_inventory_operation(operation, product)
                    await asyncio.sleep(random.uniform(0.5, 2.0))
                
                await asyncio.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Error in inventory traffic generation: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)
    
    async def simulate_inventory_operation(self, operation: str, product: Dict):
        """Simulate realistic inventory operations"""
        try:
            # This would integrate with your inventory demo API
            # For now, we'll simulate the operations
            operation_details = {
                'order': {'change': -random.randint(1, 10), 'reason': f'Customer order #{random.randint(1000, 9999)}'},
                'shipment': {'change': random.randint(20, 100), 'reason': f'Supplier shipment #{random.randint(100, 999)}'},
                'transfer': {'change': random.randint(-30, 30), 'reason': 'Inter-warehouse transfer'},
                'adjustment': {'change': random.randint(-5, 5), 'reason': 'Inventory reconciliation'}
            }
            
            details = operation_details[operation]
            self.stats['total_operations'] += 1
            
            logger.info(f"Inventory {operation}: {product['name']} {details['change']:+d} units - {details['reason']}")
            
        except Exception as e:
            logger.error(f"Error simulating inventory operation: {e}")
            self.stats['errors'] += 1
    
    async def generate_background_activity(self):
        """Generate background system activity for realism"""
        while self.running:
            try:
                # Simulate system maintenance, health checks, etc.
                activities = [
                    "Health check completed",
                    "Backup process initiated", 
                    "Cache refresh completed",
                    "Log rotation performed",
                    "Metrics collection updated",
                    "Anti-entropy sync triggered"
                ]
                
                activity = random.choice(activities)
                logger.debug(f"Background activity: {activity}")
                
                # Update active user count simulation
                self.stats['active_users'] = random.randint(50, 500)
                
                await asyncio.sleep(random.uniform(10, 30))
                
            except Exception as e:
                logger.error(f"Error in background activity: {e}")
                await asyncio.sleep(10)
    
    async def monitor_performance(self):
        """Monitor and update performance statistics"""
        last_operation_count = 0
        
        while self.running:
            try:
                # Calculate operations per second
                current_operations = self.stats['total_operations']
                ops_diff = current_operations - last_operation_count
                self.stats['operations_per_second'] = ops_diff / 10  # 10-second intervals
                last_operation_count = current_operations
                
                # Log performance stats
                logger.info(f"Performance: {self.stats['operations_per_second']:.1f} ops/sec, "
                          f"{self.stats['active_users']} active users, "
                          f"{self.stats['errors']} errors")
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error monitoring performance: {e}")
                await asyncio.sleep(10)
    
    def stop_traffic_generation(self):
        """Stop all traffic generation"""
        self.running = False
        logger.info("Traffic generation stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current traffic statistics"""
        return self.stats.copy()

# Singleton instance for global access
traffic_generator = None

def get_traffic_generator(cluster_nodes: List[str]) -> RealisticTrafficGenerator:
    """Get or create the traffic generator instance"""
    global traffic_generator
    if traffic_generator is None:
        traffic_generator = RealisticTrafficGenerator(cluster_nodes)
    return traffic_generator

async def start_realistic_traffic(cluster_nodes: List[str]):
    """Start realistic traffic generation"""
    generator = get_traffic_generator(cluster_nodes)
    await generator.start_traffic_generation()

if __name__ == "__main__":
    # Test the traffic generator
    cluster_nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
    asyncio.run(start_realistic_traffic(cluster_nodes))