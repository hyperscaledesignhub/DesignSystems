#!/usr/bin/env python3
"""
Cumulative counter tracking for the demo UI
Prevents counters from resetting when tweets cycle out
"""

import json
import time
from datetime import datetime

class CumulativeCounters:
    def __init__(self):
        self.total_counters = {
            'node1': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0},
            'node2': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}, 
            'node3': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}
        }
        self.last_reset_time = None
        self.reset_count = 0
        self.processed_tweets = set()  # Track which tweets we've counted
        
    def add_counters(self, node_num, counters):
        """Add counters to the cumulative total for a specific node"""
        node_key = f'node{node_num}'
        if node_key in self.total_counters:
            self.total_counters[node_key]['likes'] += counters.get('likes', 0)
            self.total_counters[node_key]['retweets'] += counters.get('retweets', 0)
            self.total_counters[node_key]['comments'] += counters.get('comments', 0)
            self.total_counters[node_key]['views'] += counters.get('views', 0)
    
    def get_counters(self, node_num):
        """Get cumulative counters for a specific node"""
        node_key = f'node{node_num}'
        return self.total_counters.get(node_key, {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0})
    
    def get_all_counters(self):
        """Get all cumulative counters"""
        return self.total_counters
    
    def mark_tweet_processed(self, tweet_id):
        """Mark a tweet as processed so we don't count it twice"""
        self.processed_tweets.add(tweet_id)
    
    def is_tweet_processed(self, tweet_id):
        """Check if we've already counted this tweet"""
        return tweet_id in self.processed_tweets
    
    def reset_counters(self, reason="Manual reset"):
        """Reset all counters and track when it happened"""
        self.total_counters = {
            'node1': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0},
            'node2': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}, 
            'node3': {'likes': 0, 'retweets': 0, 'comments': 0, 'views': 0}
        }
        self.last_reset_time = datetime.now()
        self.reset_count += 1
        self.processed_tweets.clear()
        return {
            'reset_time': self.last_reset_time.strftime('%H:%M:%S'),
            'reset_count': self.reset_count,
            'reason': reason
        }
    
    def get_reset_info(self):
        """Get information about the last reset"""
        if self.last_reset_time:
            return {
                'last_reset': self.last_reset_time.strftime('%H:%M:%S'),
                'reset_count': self.reset_count,
                'time_since_reset': int((datetime.now() - self.last_reset_time).total_seconds())
            }
        return None
    
    def get_total_count(self):
        """Get the total of all counters across all nodes"""
        total = 0
        for node in self.total_counters.values():
            total += sum(node.values())
        return total

# Global instance
_cumulative_counters = None

def get_cumulative_counters():
    """Get or create the global cumulative counters instance"""
    global _cumulative_counters
    if _cumulative_counters is None:
        _cumulative_counters = CumulativeCounters()
    return _cumulative_counters