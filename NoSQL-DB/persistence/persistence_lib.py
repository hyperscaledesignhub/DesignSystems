#!/usr/bin/env python3
"""
Persistence Library for Distributed Key-Value Store
Core persistence functionality extracted from tdd_step8_persistence_independent.py
"""

import os
import sys
import time
import json
import logging
import threading
import tempfile
import shutil
import glob
from typing import Dict, Optional, List, Set
from dataclasses import dataclass
from flask import Flask, jsonify, request
import requests

# Add persistence imports
from persistence.cache_flush_kvstore import put as cache_put_value, get as cache_get_value, flush_cache_to_sstable

logger = logging.getLogger(__name__)

@dataclass
class SimpleVersionedValue:
    value: str
    timestamp: float
    node_id: str
    version: int
    persisted: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "timestamp": self.timestamp,
            "node_id": self.node_id,
            "version": self.version,
            "persisted": self.persisted
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SimpleVersionedValue':
        return cls(
            value=data["value"],
            timestamp=data["timestamp"],
            node_id=data["node_id"],
            version=data["version"],
            persisted=data.get("persisted", False)
        )

class SimplePersistenceManager:
    def __init__(self, node_id: str, data_dir: str = None):
        self.node_id = node_id
        self.data_dir = data_dir or f"data/{node_id}"
        self.namespace = self.data_dir  # Use data_dir as namespace for cache/commitlog/SSTable
        os.makedirs(self.data_dir, exist_ok=True)
        self.wal_file = os.path.join(self.data_dir, "kvstore.log")
        self.cache_max_size = 1000
        self.recovered_entries = 0
        logger.info(f"SimplePersistenceManager initialized for {node_id} at {self.data_dir}")
    
    def write_to_wal(self, key: str, versioned_value: SimpleVersionedValue) -> bool:
        """Write to WAL using cache_flush_kvstore"""
        try:
            # Store as JSON string for value
            value_json = json.dumps(versioned_value.to_dict())
            return cache_put_value(key, value_json, max_size=self.cache_max_size, namespace=self.namespace)
        except Exception as e:
            logger.error(f"WAL write failed for {key}: {e}")
            return False
    
    def put_persistent(self, key: str, versioned_value: SimpleVersionedValue) -> bool:
        """Persistent put using cache_flush_kvstore"""
        try:
            # Use cache_put_value for put logic (handles commit log, cache, SSTable flush)
            value_json = json.dumps(versioned_value.to_dict())
            return cache_put_value(key, value_json, max_size=self.cache_max_size, namespace=self.namespace)
        except Exception as e:
            logger.error(f"Persistent put failed for {key}: {e}")
            return False
    
    def get_persistent(self, key: str) -> Optional[SimpleVersionedValue]:
        """Get from persistent storage"""
        try:
            value_json = cache_get_value(key, namespace=self.namespace)
            if value_json:
                versioned_data = json.loads(value_json)
                return SimpleVersionedValue.from_dict(versioned_data)
            return None
        except Exception as e:
            logger.error(f"Persistent get failed for {key}: {e}")
            return None
    
    def _flush_cache_to_sstable(self) -> bool:
        """Flush cache to SSTable"""
        try:
            return flush_cache_to_sstable(namespace=self.namespace)
        except Exception as e:
            logger.error(f"Cache flush failed: {e}")
            return False
    
    def recover_from_disk(self) -> Dict[str, SimpleVersionedValue]:
        """Recover data from commit log and SSTables"""
        try:
            recovered = {}
            
            # Recover from SSTables first (older data)
            sstable_data = self._recover_from_sstables()
            recovered.update(sstable_data)
            
            # Recover from commit log (newer data takes precedence)
            commit_log_data = self._recover_from_commit_log()
            for key, value in commit_log_data.items():
                if key not in recovered or value.timestamp > recovered[key].timestamp:
                    recovered[key] = value
            
            self.recovered_entries = len(recovered)
            logger.info(f"Recovered {len(recovered)} entries from disk")
            return recovered
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return {}
    
    def _recover_from_sstables(self) -> Dict[str, SimpleVersionedValue]:
        """Recover data from SSTable files"""
        recovered = {}
        try:
            sstable_pattern = os.path.join(self.data_dir, "sstable_*.data")
            sstable_files = glob.glob(sstable_pattern)
            if not sstable_files:
                return {}
            sstable_files.sort()
            
            for sstable_file in sstable_files:
                try:
                    with open(sstable_file, "r") as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                key = entry["key"]
                                # Parse the JSON value to get SimpleVersionedValue
                                value_json = entry["value"]
                                versioned_data = json.loads(value_json)
                                versioned_value = SimpleVersionedValue.from_dict(versioned_data)
                                
                                if key not in recovered or versioned_value.timestamp > recovered[key].timestamp:
                                    recovered[key] = versioned_value
                            except Exception as e:
                                logger.warning(f"Error parsing SSTable entry: {e}")
                except Exception as e:
                    logger.warning(f"Error reading SSTable {sstable_file}: {e}")
            
            logger.info(f"Recovered {len(recovered)} entries from SSTables")
            return recovered
        except Exception as e:
            logger.error(f"SSTable recovery failed: {e}")
            return {}
    
    def _recover_from_commit_log(self) -> Dict[str, SimpleVersionedValue]:
        """Recover data from commit log"""
        recovered = {}
        try:
            # Use the same path as cache_put_value: {namespace}/kvstore.log
            commit_log_file = os.path.join(self.data_dir, "kvstore.log")
            if not os.path.exists(commit_log_file):
                return {}
            
            with open(commit_log_file, "r") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        key = entry["key"]
                        # Parse the JSON value to get SimpleVersionedValue
                        value_json = entry["value"]
                        versioned_data = json.loads(value_json)
                        versioned_value = SimpleVersionedValue.from_dict(versioned_data)
                        
                        if key not in recovered or versioned_value.timestamp > recovered[key].timestamp:
                            recovered[key] = versioned_value
                    except Exception as e:
                        logger.warning(f"Error parsing commit log entry: {e}")
            
            logger.info(f"Recovered {len(recovered)} entries from commit log")
            return recovered
        except Exception as e:
            logger.error(f"Commit log recovery failed: {e}")
            return {}
    
    def get_stats(self) -> Dict:
        """Get persistence statistics"""
        try:
            # Use cache_get_value and os/glob for stats
            cache_keys_list = []
            try:
                from cache import cache_keys
                cache_keys_list = cache_keys(self.namespace)
            except Exception:
                pass
            sstable_pattern = os.path.join(self.data_dir, "sstable_*.data")
            sstable_files = glob.glob(sstable_pattern)
            sstable_count = len(sstable_files)
            wal_size = 0
            if os.path.exists(self.wal_file):
                wal_size = os.path.getsize(self.wal_file)
            return {
                "cache_entries": len(cache_keys_list),
                "sstable_files": sstable_count,
                "wal_size_bytes": wal_size,
                "recovered_entries": self.recovered_entries,
                "data_directory": self.data_dir
            }
        except Exception as e:
            logger.error(f"Error getting persistence stats: {e}")
            return {"error": str(e)}

# Persistence utility functions
def create_versioned_value(value: str, node_id: str, version: int = 1) -> SimpleVersionedValue:
    """Create a versioned value with current timestamp"""
    return SimpleVersionedValue(
        value=value,
        timestamp=time.time(),
        node_id=node_id,
        version=version
    )

def put_with_persistence(persistence_manager: SimplePersistenceManager, key: str, value: str, node_id: str) -> bool:
    """Put a key-value pair with persistence"""
    versioned_value = create_versioned_value(value, node_id)
    return persistence_manager.put_persistent(key, versioned_value)

def get_with_persistence(persistence_manager: SimplePersistenceManager, key: str) -> Optional[str]:
    """Get a value with persistence fallback"""
    versioned_value = persistence_manager.get_persistent(key)
    if versioned_value:
        return versioned_value.value
    return None

def recover_node_data(persistence_manager: SimplePersistenceManager) -> Dict[str, str]:
    """Recover all data for a node"""
    recovered_data = persistence_manager.recover_from_disk()
    return {key: versioned_value.value for key, versioned_value in recovered_data.items()} 