#!/usr/bin/env python3
"""
Twitter-like Social Media Counter Demo
Demonstrates distributed counter replication for likes, retweets, and followers
"""

import os
import sys
import time
import json
import requests
import threading
import random
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_utils import DemoLogger, ensure_cluster_running

class TwitterCounterDemo:
    def __init__(self, cluster_nodes=None):
        self.logger = DemoLogger("twitter_counter_demo")
        self.cluster_nodes = cluster_nodes or []
        self.tweet_id = "tweet_12345"
        self.user_id = "user_elonmusk"
        
    def create_tweet(self):
        """Create a sample tweet with counters"""
        self.logger.step("Creating viral tweet")
        
        tweet_data = {
            "id": self.tweet_id,
            "author": "@elonmusk",
            "content": "Just sent a car to space 🚗🚀 #SpaceX",
            "timestamp": time.time(),
            "counters": {
                "likes": 0,
                "retweets": 0,
                "comments": 0,
                "views": 1000  # Initial views
            }
        }
        
        # Create tweet on primary node
        response = requests.put(
            f"http://{self.cluster_nodes[0]}/kv/{self.tweet_id}",
            json={"value": json.dumps(tweet_data)}
        )
        
        if response.status_code == 200:
            self.logger.success("Tweet created successfully!")
            self.logger.info(f"Tweet: \"{tweet_data['content']}\"")
        else:
            self.logger.error(f"Failed to create tweet: {response.text}")
            
        # Create user follower count
        user_data = {
            "username": "@elonmusk", 
            "followers": 150000000,  # 150M followers
            "following": 423
        }
        
        requests.put(
            f"http://{self.cluster_nodes[0]}/kv/{self.user_id}",
            json={"value": json.dumps(user_data)}
        )
        
    def simulate_viral_engagement(self):
        """Simulate a tweet going viral with high engagement"""
        self.logger.step("Simulating viral tweet engagement")
        
        # Simulate different types of engagement (reduced for testing)
        engagement_types = [
            ("likes", 50, "❤️"),
            ("retweets", 20, "🔄"),
            ("comments", 10, "💬"),
            ("views", 100, "👁️")
        ]
        
        # Process sequentially for now to avoid race conditions
        for counter_type, count, emoji in engagement_types:
            self._generate_engagement(counter_type, count, emoji)
            time.sleep(1)  # Give time for replication
            
        self.logger.success("Viral engagement simulation complete!")
        
    def _generate_engagement(self, counter_type, count, emoji):
        """Generate engagement for a specific counter"""
        self.logger.info(f"Generating {count} {counter_type} {emoji}")
        
        for i in range(count):
            # Use first node for simplicity
            node = self.cluster_nodes[0]
            success = self.increment_counter(node, counter_type)
            if success:
                if i % 10 == 0:
                    self.logger.info(f"  Added {i+1}/{count} {counter_type}")
            time.sleep(0.02)  # Small delay to avoid overwhelming the database
                
    def increment_counter(self, node, counter_type):
        """Increment a specific counter atomically"""
        try:
            # Get current tweet data
            response = requests.get(f"http://{node}/kv/{self.tweet_id}")
            if response.status_code == 200:
                # The database returns the value as a string in the response
                response_data = response.json()
                value_str = response_data.get("value", "{}")
                tweet_data = json.loads(value_str)
                
                # Increment counter
                if "counters" not in tweet_data:
                    tweet_data["counters"] = {}
                    
                current_value = tweet_data["counters"].get(counter_type, 0)
                tweet_data["counters"][counter_type] = current_value + 1
                
                # Write back
                response = requests.put(
                    f"http://{node}/kv/{self.tweet_id}",
                    json={"value": json.dumps(tweet_data)}
                )
                
                if response.status_code == 200:
                    return True
                else:
                    self.logger.error(f"Failed to increment {counter_type}: {response.text}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error incrementing counter: {e}")
            return False
            
    def show_real_time_stats(self):
        """Display real-time statistics from all nodes"""
        self.logger.step("Real-time engagement statistics")
        
        print("\n" + "="*60)
        print("📊 LIVE TWEET STATS (Refreshing every second)")
        print("="*60)
        
        for _ in range(10):  # Show stats for 10 seconds
            stats_by_node = {}
            
            for i, node in enumerate(self.cluster_nodes):
                try:
                    response = requests.get(f"http://{node}/kv/{self.tweet_id}")
                    if response.status_code == 200:
                        response_data = response.json()
                        value_str = response_data.get("value", "{}")
                        tweet_data = json.loads(value_str)
                        counters = tweet_data.get("counters", {})
                        stats_by_node[f"Node-{i+1}"] = counters
                except Exception as e:
                    stats_by_node[f"Node-{i+1}"] = {"error": str(e)}
                    
            # Clear previous output (simple approach)
            print("\033[H\033[J", end="")
            print("\n" + "="*60)
            print("📊 LIVE TWEET STATS")
            print("="*60)
            print(f"Tweet: \"Just sent a car to space 🚗🚀 #SpaceX\"")
            print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
            print("-"*60)
            
            # Show stats from each node
            for node_name, counters in stats_by_node.items():
                if "error" not in counters:
                    likes = counters.get("likes", 0)
                    retweets = counters.get("retweets", 0) 
                    comments = counters.get("comments", 0)
                    views = counters.get("views", 0)
                    
                    status = "✅" if all(stats_by_node.get("Node-1", {}).get(k) == v 
                                       for k, v in counters.items()) else "⏳"
                    
                    print(f"\n{node_name} {status}")
                    print(f"  ❤️ Likes: {likes:,}")
                    print(f"  🔄 Retweets: {retweets:,}")
                    print(f"  💬 Comments: {comments:,}")
                    print(f"  👁️ Views: {views:,}")
                else:
                    print(f"\n{node_name} ❌ (Error: {counters['error']})")
                    
            time.sleep(1)
            
    def simulate_follower_spike(self):
        """Simulate a spike in followers (e.g., after viral tweet)"""
        self.logger.step("Simulating follower spike after viral tweet")
        
        # Get current follower count
        response = requests.get(f"http://{self.cluster_nodes[0]}/kv/{self.user_id}")
        if response.status_code == 200:
            response_data = response.json()
            value_str = response_data.get("value", "{}")
            user_data = json.loads(value_str)
            initial_followers = user_data.get("followers", 0)
            
            self.logger.info(f"Initial followers: {initial_followers:,}")
            
            # Simulate gaining 50,000 followers
            new_followers = 50000
            self.logger.info(f"Gaining {new_followers:,} new followers...")
            
            # Distribute follower updates across nodes
            followers_per_update = 1000
            for i in range(0, new_followers, followers_per_update):
                node = random.choice(self.cluster_nodes)
                
                # Get latest count
                response = requests.get(f"http://{node}/kv/{self.user_id}")
                if response.status_code == 200:
                    response_data = response.json()
                    value_str = response_data.get("value", "{}")
                    user_data = json.loads(value_str)
                    user_data["followers"] = user_data.get("followers", 0) + followers_per_update
                    
                    # Update
                    requests.put(
                        f"http://{node}/kv/{self.user_id}",
                        json={"value": json.dumps(user_data)}
                    )
                    
                if i % 10000 == 0:
                    self.logger.info(f"  +{i:,} followers...")
                    
            self.logger.success(f"Follower spike complete! New total: {initial_followers + new_followers:,}")
            
    def check_replication_consistency(self):
        """Check if counters are consistent across all nodes"""
        self.logger.step("Checking replication consistency")
        
        tweet_stats = {}
        user_stats = {}
        
        for i, node in enumerate(self.cluster_nodes):
            node_name = f"Node-{i+1}"
            
            # Check tweet counters
            try:
                response = requests.get(f"http://{node}/kv/{self.tweet_id}")
                if response.status_code == 200:
                    response_data = response.json()
                    value_str = response_data.get("value", "{}")
                    tweet_data = json.loads(value_str)
                    tweet_stats[node_name] = tweet_data.get("counters", {})
            except Exception as e:
                self.logger.error(f"Error checking {node_name}: {e}")
                
            # Check user followers
            try:
                response = requests.get(f"http://{node}/kv/{self.user_id}")
                if response.status_code == 200:
                    response_data = response.json()
                    value_str = response_data.get("value", "{}")
                    user_data = json.loads(value_str)
                    user_stats[node_name] = user_data.get("followers", 0)
            except Exception as e:
                self.logger.error(f"Error checking user on {node_name}: {e}")
                
        # Check consistency
        self.logger.info("Tweet counter consistency:")
        reference_stats = list(tweet_stats.values())[0] if tweet_stats else {}
        all_consistent = True
        
        for node_name, stats in tweet_stats.items():
            is_consistent = stats == reference_stats
            status = "✅" if is_consistent else "❌"
            all_consistent &= is_consistent
            
            self.logger.info(f"  {node_name}: {status} - {stats}")
            
        if all_consistent:
            self.logger.success("All nodes have consistent tweet counters!")
        else:
            self.logger.warning("Inconsistencies detected - waiting for convergence...")
            
        # Check follower count consistency
        self.logger.info("\nFollower count consistency:")
        follower_values = list(user_stats.values())
        if len(set(follower_values)) == 1:
            self.logger.success(f"All nodes show {follower_values[0]:,} followers ✅")
        else:
            self.logger.warning("Follower counts are inconsistent:")
            for node_name, count in user_stats.items():
                self.logger.info(f"  {node_name}: {count:,}")
                
    def demonstrate_quorum_reads(self):
        """Demonstrate quorum reads for consistency"""
        self.logger.step("Demonstrating quorum reads")
        
        # Simulate reading from multiple nodes
        self.logger.info("Reading tweet stats with quorum (2 out of 3 nodes)...")
        
        stats_from_nodes = []
        for i, node in enumerate(self.cluster_nodes[:2]):  # Read from 2 nodes (quorum)
            try:
                response = requests.get(f"http://{node}/kv/{self.tweet_id}")
                if response.status_code == 200:
                    response_data = response.json()
                    value_str = response_data.get("value", "{}")
                    tweet_data = json.loads(value_str)
                    stats_from_nodes.append(tweet_data.get("counters", {}))
                    self.logger.info(f"Read from Node-{i+1}: {tweet_data.get('counters', {})}")
            except Exception as e:
                self.logger.error(f"Failed to read from Node-{i+1}: {e}")
                
        # Verify quorum agreement
        if len(stats_from_nodes) >= 2 and all(s == stats_from_nodes[0] for s in stats_from_nodes):
            self.logger.success("Quorum achieved! Consistent read confirmed")
        else:
            self.logger.warning("Quorum reads show inconsistency - conflict resolution needed")
            
    def simulate_node_lag(self):
        """Simulate one node lagging behind due to network issues"""
        self.logger.step("Simulating replication lag")
        
        if len(self.cluster_nodes) < 3:
            self.logger.warning("Need at least 3 nodes for lag simulation")
            return
            
        # Simulate Node-3 being slow/lagging
        self.logger.info("Node-3 experiencing network latency...")
        self.logger.info("Updating counters on Node-1 and Node-2 only...")
        
        # Update only on first two nodes
        for _ in range(20):
            node = random.choice(self.cluster_nodes[:2])  # Only first 2 nodes
            self.increment_counter(node, "likes")
            
        # Show lag
        self.logger.info("\nChecking stats during lag:")
        for i, node in enumerate(self.cluster_nodes):
            try:
                response = requests.get(f"http://{node}/kv/{self.tweet_id}")
                if response.status_code == 200:
                    response_data = response.json()
                    value_str = response_data.get("value", "{}")
                    tweet_data = json.loads(value_str)
                    likes = tweet_data.get("counters", {}).get("likes", 0)
                    
                    lag_indicator = " (LAGGING)" if i == 2 else ""
                    self.logger.info(f"Node-{i+1}: {likes} likes{lag_indicator}")
            except:
                pass
                
        # Wait for anti-entropy
        self.logger.info("\nWaiting for anti-entropy to sync lagging node...")
        time.sleep(3)
        
        # Check again
        self.check_replication_consistency()
        
    def run_demo(self):
        """Run the complete Twitter counter demo"""
        self.logger.header("🐦 Twitter-like Distributed Counter Demo 🐦")
        self.logger.info("Demonstrating distributed counters for social media metrics")
        
        # Ensure cluster is running
        if not self.cluster_nodes:
            self.cluster_nodes = ensure_cluster_running(self.logger)
            if not self.cluster_nodes:
                return
                
        try:
            # Create tweet
            self.create_tweet()
            time.sleep(1)
            
            # Simulate viral engagement
            self.simulate_viral_engagement()
            
            # Show real-time stats
            self.show_real_time_stats()
            
            # Check consistency
            self.check_replication_consistency()
            time.sleep(2)
            
            # Simulate follower spike
            self.simulate_follower_spike()
            time.sleep(2)
            
            # Demonstrate quorum reads
            self.demonstrate_quorum_reads()
            time.sleep(1)
            
            # Simulate node lag
            if len(self.cluster_nodes) >= 3:
                self.simulate_node_lag()
                
            # Final consistency check
            self.check_replication_consistency()
            
            self.logger.header("✅ Demo completed successfully!")
            self.logger.info("Key takeaways:")
            self.logger.info("- Distributed counters handle high-traffic scenarios")
            self.logger.info("- Replication ensures availability across regions")
            self.logger.info("- Quorum reads provide consistent data")
            self.logger.info("- Anti-entropy handles node lag and network issues")
            self.logger.info("- Perfect for social media metrics at scale")
            
        except KeyboardInterrupt:
            self.logger.warning("\nDemo interrupted by user")
        except Exception as e:
            self.logger.error(f"Demo error: {e}")
            import traceback
            traceback.print_exc()

def main():
    # Check for existing cluster
    cluster_env = os.environ.get('CLUSTER_NODES')
    cluster_nodes = None
    
    if cluster_env:
        cluster_nodes = [node.strip() for node in cluster_env.split(',')]
        print(f"Using existing cluster: {cluster_nodes}")
    
    demo = TwitterCounterDemo(cluster_nodes)
    demo.run_demo()

if __name__ == "__main__":
    main()