#!/usr/bin/env python3
"""
REAL Traffic Generator for Distributed Database
Generates ACTUAL traffic against your live cluster - no fake data!
"""

import asyncio
import aiohttp
import json
import time
import random
import threading
from datetime import datetime
import names
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDatabaseTrafficGenerator:
    def __init__(self, cluster_nodes: List[str]):
        self.cluster_nodes = cluster_nodes
        self.running = False
        self.active_tweets = []
        self.active_documents = []
        
    def start_continuous_traffic(self):
        """Start REAL continuous traffic generation"""
        self.running = True
        
        # Start background threads for different types of traffic
        threads = [
            threading.Thread(target=self._run_twitter_traffic, daemon=True),
            threading.Thread(target=self._run_collab_traffic, daemon=True),
            threading.Thread(target=self._run_inventory_traffic, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
            
        logger.info("REAL traffic generation started against distributed database cluster")
        return threads
    
    def _run_twitter_traffic(self):
        """Generate REAL Twitter traffic on persistent tweet only"""
        persistent_tweet_id = "tweet_persistent_demo"
        
        while self.running:
            try:
                # Only generate engagement on the persistent tweet - never recreate it
                if random.random() < 0.2:  # 20% chance to generate engagement (reduced for stability)
                    action = random.choices(
                        ['likes', 'retweets', 'comments', 'views'],
                        weights=[30, 15, 10, 45]  # Views are most common
                    )[0]
                    self._engage_with_real_tweet(persistent_tweet_id, action)
                
                time.sleep(random.uniform(3.0, 5.0))  # Longer delay to avoid overwhelming cluster
                
            except Exception as e:
                logger.error(f"Error in Twitter traffic: {e}")
                time.sleep(1)
    
    def _ensure_persistent_tweet_exists(self):
        """Ensure persistent tweet exists, create only if missing - NEVER overwrite existing data"""
        persistent_tweet_id = "tweet_persistent_demo"
        
        # Use a class variable to ensure we only check once per traffic generator instance
        if hasattr(self, '_tweet_creation_attempted'):
            return persistent_tweet_id
            
        self._tweet_creation_attempted = True
        
        try:
            node = random.choice(self.cluster_nodes)
            import requests
            
            # Check if tweet exists with proper quorum read
            response = requests.get(f"http://{node}/kv/{persistent_tweet_id}", timeout=3)
            
            if response.status_code == 200:
                response_data = response.json()
                if "error" not in response_data and "value" in response_data:
                    # Tweet exists and is readable - NEVER recreate it
                    logger.info(f"Persistent tweet already exists with data: {persistent_tweet_id}")
                    return persistent_tweet_id
            
            # Only create if it genuinely doesn't exist or is not readable
            tweet_data = {
                "id": persistent_tweet_id,
                "author": "@distributed_demo",
                "content": "🚀 Persistent tweet for cumulative counter demonstration across distributed nodes",
                "timestamp": time.time(),
                "counters": {
                    "likes": 0,
                    "retweets": 0, 
                    "comments": 0,
                    "views": 0
                }
            }
            
            create_response = requests.put(
                f"http://{node}/kv/{persistent_tweet_id}",
                json={"value": json.dumps(tweet_data)},
                timeout=5
            )
            
            if create_response.status_code == 200:
                logger.info(f"Created new persistent tweet: {persistent_tweet_id}")
            else:
                logger.error(f"Failed to create persistent tweet: {create_response.text}")
                
        except Exception as e:
            logger.error(f"Error ensuring persistent tweet exists: {e}")
    
    def _create_real_tweet(self) -> str:
        """Create a REAL tweet in the distributed database"""
        # This method is deprecated - we now use a single persistent tweet
        # Return the persistent tweet ID without recreating it
        return "tweet_persistent_demo"
    
    def _engage_with_real_tweet(self, tweet_id: str, action: str):
        """Generate REAL engagement with a tweet in the database with retry logic and failure tracking"""
        max_retries = 3
        retry_delay = 0.5  # seconds
        
        for attempt in range(max_retries):
            try:
                # Use random node for load balancing
                node = random.choice(self.cluster_nodes)
                
                import requests
                
                # REAL database read
                response = requests.get(f"http://{node}/kv/{tweet_id}", timeout=3)
                
                tweet_data = None
                
                if response.status_code == 200:
                    response_data = response.json()
                    
                    # CHECK FOR QUORUM FAILURE AND DATA INCONSISTENCY
                    if "error" in response_data:
                        if "Quorum not reached" in response_data["error"]:
                            logger.warning(f"Attempt {attempt + 1}: Quorum not reached for read {tweet_id}, retrying...")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                                continue
                            else:
                                logger.error(f"CLUSTER DEGRADED: Failed to read {tweet_id} after {max_retries} attempts: {response_data['error']}")
                                self._mark_cluster_degraded("Read quorum failures after retries")
                                return
                        elif "Data inconsistency detected" in response_data["error"]:
                            # Data inconsistency detected - wait and retry, don't resolve
                            logger.warning(f"Attempt {attempt + 1}: Data inconsistency detected for {tweet_id}, retrying after delay...")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                                continue
                            else:
                                logger.error(f"Data inconsistency persisted for {tweet_id} after {max_retries} attempts")
                                return
                        else:
                            logger.error(f"Read error for {tweet_id}: {response_data['error']}")
                            return
                    
                    # Successful quorum read
                    value_str = response_data.get("value", "{}")
                    tweet_data = json.loads(value_str)
                else:
                    # HTTP error - don't assume tweet doesn't exist, retry instead
                    logger.warning(f"HTTP error reading {tweet_id} (status {response.status_code}), retrying...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"Failed to read {tweet_id} after {max_retries} attempts")
                        return
                
                # REAL counter increment - ensure counters exist
                if "counters" not in tweet_data:
                    tweet_data["counters"] = {}
                
                current_value = tweet_data["counters"].get(action, 0)
                tweet_data["counters"][action] = current_value + 1
                
                # REAL database write
                write_response = requests.put(
                    f"http://{node}/kv/{tweet_id}",
                    json={"value": json.dumps(tweet_data)},
                    timeout=3
                )
                
                if write_response.status_code == 200:
                    write_data = write_response.json()
                    
                    # CHECK WRITE QUORUM FAILURE - handle both error message formats
                    if "error" in write_data:
                        error_msg = write_data["error"]
                        if "Quorum not reached" in error_msg or "quorum not reached" in error_msg:
                            logger.warning(f"Attempt {attempt + 1}: Write quorum failed for {tweet_id} - {error_msg}, retrying...")
                            if attempt < max_retries - 1:
                                time.sleep(retry_delay * (attempt + 1))
                                continue
                            else:
                                logger.error(f"CLUSTER DEGRADED: Failed to write {tweet_id} after {max_retries} attempts: {error_msg}")
                                self._mark_cluster_degraded("Write quorum failures after retries")
                                return
                        else:
                            logger.error(f"Write error for {tweet_id}: {error_msg}")
                            return
                    
                    # Successful write
                    logger.debug(f"REAL engagement: {action} on {tweet_id} via {node} (attempt {attempt + 1})")
                    return  # Success, exit retry loop
                else:
                    logger.error(f"Write failed with status {write_response.status_code}: {write_response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                        
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}: Error with real engagement: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    continue
        
        logger.error(f"CLUSTER DEGRADED: Failed to engage with {tweet_id} after {max_retries} attempts")
        self._mark_cluster_degraded("Multiple operation failures")
    
    def _mark_cluster_degraded(self, reason: str):
        """Mark cluster as degraded and notify UI"""
        import time
        self.cluster_status = {
            'status': 'degraded',
            'reason': reason,
            'timestamp': time.time(),
            'healthy_nodes': 0,
            'total_nodes': len(self.cluster_nodes)
        }
        logger.error(f"🚨 CLUSTER MARKED AS DEGRADED: {reason}")
    
    def get_cluster_status(self):
        """Get current cluster status for UI"""
        return getattr(self, 'cluster_status', {
            'status': 'healthy',
            'healthy_nodes': len(self.cluster_nodes),
            'total_nodes': len(self.cluster_nodes)
        })
    
    def _run_collab_traffic(self):
        """Generate REAL collaborative editing traffic"""
        while self.running:
            try:
                # Create real documents in the database
                if random.random() < 0.2:  # 20% chance to create new doc
                    doc_id = self._create_real_document()
                    if doc_id:
                        self.active_documents.append(doc_id)
                        if len(self.active_documents) > 10:
                            self.active_documents.pop(0)
                
                # Generate REAL edits on existing documents
                if self.active_documents:
                    doc_id = random.choice(self.active_documents)
                    self._edit_real_document(doc_id)
                
                time.sleep(random.uniform(5, 15))
                
            except Exception as e:
                logger.error(f"Error in collaborative traffic: {e}")
                time.sleep(5)
    
    def _create_real_document(self) -> str:
        """Create a REAL document in the distributed database"""
        try:
            node = random.choice(self.cluster_nodes)
            
            titles = [
                "Engineering Roadmap Q1 2024",
                "Product Requirements Document", 
                "System Architecture Review",
                "Performance Optimization Plan",
                "Database Migration Strategy"
            ]
            
            doc_data = {
                "title": random.choice(titles),
                "paragraphs": {},
                "version": 1,
                "created_at": time.time()
            }
            
            doc_id = f"doc_{int(time.time() * 1000)}"
            
            # REAL database write with causal consistency for document creation
            import requests
            response = requests.put(
                f"http://{node}/causal/kv/{doc_id}",
                json={"value": json.dumps(doc_data)},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"REAL document created: {doc_id} on node {node}")
                return doc_id
            else:
                logger.error(f"Failed to create document: {response.text}")
                
        except Exception as e:
            logger.error(f"Error creating real document: {e}")
            
        return None
    
    def _edit_real_document(self, doc_id: str):
        """Edit a REAL document in the distributed database"""
        try:
            node = random.choice(self.cluster_nodes)
            
            import requests
            
            # REAL database read with causal consistency for edit ordering
            response = requests.get(f"http://{node}/causal/kv/{doc_id}", timeout=3)
            if response.status_code == 200:
                response_data = response.json()
                value_str = response_data.get("value", "{}")
                doc_data = json.loads(value_str)
                
                # Add real content
                para_id = f"para_{random.randint(1, 5)}"
                authors = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
                
                content_updates = [
                    "Updated the technical specifications based on latest requirements.",
                    "Added performance benchmarks and optimization strategies.",
                    "Revised timeline to accommodate stakeholder feedback.",
                    "Included risk assessment and mitigation plans.",
                    "Enhanced the implementation details with code examples."
                ]
                
                if "paragraphs" not in doc_data:
                    doc_data["paragraphs"] = {}
                
                doc_data["paragraphs"][para_id] = {
                    "content": random.choice(content_updates),
                    "author": random.choice(authors),
                    "timestamp": time.time()
                }
                doc_data["version"] = doc_data.get("version", 0) + 1
                
                # REAL database write with causal consistency for proper edit ordering
                response = requests.put(
                    f"http://{node}/causal/kv/{doc_id}",
                    json={"value": json.dumps(doc_data)},
                    timeout=3
                )
                
                if response.status_code == 200:
                    logger.info(f"REAL document edit: {doc_id} {para_id} via {node}")
                else:
                    logger.error(f"Failed to edit document: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error editing real document: {e}")
    
    def _run_inventory_traffic(self):
        """Generate REAL inventory traffic"""
        while self.running:
            try:
                products = [
                    "iphone-14-pro", "macbook-pro", "airpods-pro", 
                    "ipad-air", "apple-watch"
                ]
                
                for product in products:
                    if random.random() < 0.4:  # 40% chance per product
                        self._update_real_inventory(product)
                        time.sleep(random.uniform(0.5, 2.0))
                
                time.sleep(random.uniform(8, 20))
                
            except Exception as e:
                logger.error(f"Error in inventory traffic: {e}")
                time.sleep(5)
    
    def _update_real_inventory(self, product_id: str):
        """Update REAL inventory in the distributed database"""
        try:
            node = random.choice(self.cluster_nodes)
            
            import requests
            
            # REAL database read
            response = requests.get(f"http://{node}/kv/inventory_{product_id}", timeout=3)
            
            if response.status_code == 200:
                response_data = response.json()
                value_str = response_data.get("value", "{}")
                inventory_data = json.loads(value_str)
            else:
                # Initialize if not exists
                inventory_data = {
                    "product_id": product_id,
                    "warehouses": {
                        "ny": random.randint(100, 500),
                        "la": random.randint(100, 500), 
                        "chicago": random.randint(100, 500)
                    },
                    "last_updated": time.time()
                }
            
            # REAL inventory change
            warehouse = random.choice(["ny", "la", "chicago"])
            change = random.randint(-10, 20)  # Orders reduce, shipments increase
            
            if "warehouses" not in inventory_data:
                inventory_data["warehouses"] = {}
            if warehouse not in inventory_data["warehouses"]:
                inventory_data["warehouses"][warehouse] = random.randint(100, 500)
            
            # Ensure stock doesn't go negative
            new_stock = max(0, inventory_data["warehouses"][warehouse] + change)
            inventory_data["warehouses"][warehouse] = new_stock
            inventory_data["last_updated"] = time.time()
            
            # REAL database write with replication
            response = requests.put(
                f"http://{node}/kv/inventory_{product_id}",
                json={"value": json.dumps(inventory_data)},
                timeout=3
            )
            
            if response.status_code == 200:
                operation = "order" if change < 0 else "shipment"
                logger.info(f"REAL inventory {operation}: {product_id} {warehouse} {change:+d} via {node}")
            else:
                logger.error(f"Failed to update inventory: {response.text}")
                
        except Exception as e:
            logger.error(f"Error updating real inventory: {e}")
    
    def stop_traffic(self):
        """Stop traffic generation"""
        self.running = False
        logger.info("REAL traffic generation stopped")
    
    def get_active_tweets(self) -> List[str]:
        """Get list of active tweet IDs"""
        return self.active_tweets.copy()
    
    def get_active_documents(self) -> List[str]:
        """Get list of active document IDs"""  
        return self.active_documents.copy()

# Global traffic generator instance
real_traffic_generator = None

def start_real_traffic(cluster_nodes: List[str]) -> RealDatabaseTrafficGenerator:
    """Start REAL traffic generation against the cluster"""
    global real_traffic_generator
    
    if real_traffic_generator is None:
        real_traffic_generator = RealDatabaseTrafficGenerator(cluster_nodes)
        real_traffic_generator.start_continuous_traffic()
        logger.info(f"REAL traffic generator started against cluster: {cluster_nodes}")
    
    return real_traffic_generator

def stop_real_traffic():
    """Stop REAL traffic generation"""
    global real_traffic_generator
    if real_traffic_generator:
        real_traffic_generator.stop_traffic()
        real_traffic_generator = None

def get_real_traffic_generator() -> RealDatabaseTrafficGenerator:
    """Get the active traffic generator"""
    return real_traffic_generator

if __name__ == "__main__":
    # Test against actual cluster
    cluster_nodes = ["localhost:9999", "localhost:10000", "localhost:10001"]
    generator = start_real_traffic(cluster_nodes)
    
    try:
        # Run for a while then stop
        time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        stop_real_traffic()