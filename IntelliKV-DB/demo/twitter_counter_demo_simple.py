#!/usr/bin/env python3
"""
Simplified Twitter Counter Demo - Tests basic functionality
"""

import os
import sys
import time
import json
import requests

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo.demo_utils import DemoLogger, ensure_cluster_running

def test_twitter_demo():
    logger = DemoLogger("twitter_simple_test")
    
    # Get cluster nodes
    cluster_env = os.environ.get('CLUSTER_NODES')
    if cluster_env:
        nodes = [node.strip() for node in cluster_env.split(',')]
    else:
        nodes = ensure_cluster_running(logger)
        
    if not nodes:
        logger.error("No cluster available")
        return False
        
    logger.header("🐦 Simple Twitter Counter Test 🐦")
    
    # Test 1: Create tweet
    logger.step("Creating tweet")
    tweet_id = "simple_tweet_test"
    tweet_data = {
        "content": "Testing distributed counters! 🚀",
        "counters": {"likes": 0, "retweets": 0, "views": 1}
    }
    
    response = requests.put(
        f"http://{nodes[0]}/kv/{tweet_id}",
        json={"value": json.dumps(tweet_data)}
    )
    
    if response.status_code == 200:
        logger.success("Tweet created successfully")
    else:
        logger.error(f"Failed to create tweet: {response.text}")
        return False
        
    # Test 2: Increment likes
    logger.step("Adding 10 likes")
    for i in range(10):
        # Get current data
        resp = requests.get(f"http://{nodes[0]}/kv/{tweet_id}")
        if resp.status_code == 200:
            current_data = json.loads(resp.json()["value"])
            current_data["counters"]["likes"] += 1
            
            # Write back
            put_resp = requests.put(
                f"http://{nodes[0]}/kv/{tweet_id}",
                json={"value": json.dumps(current_data)}
            )
            
            if put_resp.status_code == 200:
                logger.info(f"  Like {i+1} added successfully")
            else:
                logger.error(f"Failed to add like {i+1}")
                
        time.sleep(0.1)
        
    # Test 3: Check replication
    logger.step("Checking replication across nodes")
    for i, node in enumerate(nodes):
        try:
            resp = requests.get(f"http://{node}/kv/{tweet_id}")
            if resp.status_code == 200:
                data = json.loads(resp.json()["value"])
                likes = data["counters"]["likes"]
                logger.success(f"Node-{i+1}: {likes} likes ✅")
            else:
                logger.warning(f"Node-{i+1}: No data found")
        except Exception as e:
            logger.error(f"Node-{i+1}: Error - {e}")
            
    # Test 4: Final verification
    logger.step("Final verification")
    resp = requests.get(f"http://{nodes[0]}/kv/{tweet_id}")
    final_data = json.loads(resp.json()["value"])
    final_likes = final_data["counters"]["likes"]
    
    if final_likes == 10:
        logger.success(f"✅ Test passed! Final likes: {final_likes}")
        return True
    else:
        logger.error(f"❌ Test failed! Expected 10 likes, got {final_likes}")
        return False

if __name__ == "__main__":
    success = test_twitter_demo()
    if success:
        print("\n🎉 Twitter counter demo works correctly!")
    else:
        print("\n❌ Twitter counter demo needs fixing")