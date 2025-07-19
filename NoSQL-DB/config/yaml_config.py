#!/usr/bin/env python3
"""
Simple YAML configuration loader for the distributed database
"""

import os
import yaml
from typing import Optional, List, Dict

class YamlConfig:
    """YAML-based configuration loader"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from YAML file"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file {self.config_file} not found")
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                if not config:
                    raise ValueError(f"Configuration file {self.config_file} is empty or invalid")
                return config
        except Exception as e:
            raise Exception(f"Could not load {self.config_file}: {e}")
    

    
    def get_persistent_port(self) -> int:
        """Get persistent port from configuration"""
        return self.config.get('database', {}).get('persistent_port', 55201)
    
    def get_persistent_port_for_node(self, node_id: str) -> Optional[int]:
        """Get persistent port for a specific node ID from YAML configuration"""
        # First try to find the node in seed_nodes
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('persistent_port')
        
        # If not found in seed_nodes, return the global persistent port
        return self.get_persistent_port()
    
    def get_db_port(self) -> int:
        """Get database port"""
        return self.config.get('database', {}).get('db_port', 0)
    
    def get_seed_nodes(self) -> List[Dict]:
        """Get seed nodes configuration"""
        return self.config.get('cluster', {}).get('seed_nodes', [])
    
    def get_seed_node_addresses(self) -> List[str]:
        """Get seed node addresses in format host:http_port"""
        seed_nodes = self.get_seed_nodes()
        return [f"{node['host']}:{node['http_port']}" for node in seed_nodes]
    
    def get_seed_node_by_id(self, node_id: str) -> Optional[Dict]:
        """Get seed node configuration by ID"""
        seed_nodes = self.get_seed_nodes()
        for node in seed_nodes:
            if node.get('id') == node_id:
                return node
        return None
    
    def get_current_node_config(self, node_id: str) -> Optional[Dict]:
        """Get current node configuration by ID (from seed nodes or create default)"""
        # First try to find in seed nodes
        seed_node = self.get_seed_node_by_id(node_id)
        if seed_node:
            return seed_node
        
        # If not found in seed nodes, create default config
        default_config = {
            'id': node_id,
            'host': self.get_node_config().get('host', '127.0.0.1'),
            'http_port': self.get_node_config().get('http_port', 9999),
            'db_port': self.get_db_port(),
            'persistent_port': self.get_persistent_port()
        }
        return default_config
    
    def get_node_config(self) -> dict:
        """Get node configuration"""
        return self.config.get('node', {})
    
    def get_cluster_config(self) -> dict:
        """Get cluster configuration"""
        return self.config.get('cluster', {})
    
    def get_consistency_config(self) -> dict:
        """Get consistency configuration"""
        return self.config.get('consistency', {})
    
    def get_timing_config(self) -> dict:
        """Get timing configuration"""
        return self.config.get('timing', {})
    
    def get_storage_config(self) -> dict:
        """Get storage configuration"""
        return self.config.get('storage', {})
    
    def get_logging_config(self) -> dict:
        """Get logging configuration"""
        return self.config.get('logging', {})
    
    def get_monitoring_config(self) -> dict:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})

    def get_failure_detection_port_for_node(self, node_id: str) -> Optional[int]:
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('failure_detection_port')
        return None

    def get_gossip_port_for_node(self, node_id: str) -> Optional[int]:
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('gossip_port')
        return None

    def get_anti_entropy_port_for_node(self, node_id: str) -> Optional[int]:
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('anti_entropy_port')
        return None

    def get_monitoring_port_for_node(self, node_id: str) -> Optional[int]:
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('monitoring_port')
        return None

    def get_http_port_for_node(self, node_id: str) -> Optional[int]:
        node_config = self.get_seed_node_by_id(node_id)
        if node_config:
            return node_config.get('http_port')
        return None

    def get_node_id_by_gossip_port(self, gossip_port: int) -> Optional[str]:
        seed_nodes = self.get_seed_nodes()
        for node in seed_nodes:
            if node.get('gossip_port') == gossip_port:
                return node.get('id')
        return None

# Global config instance - support environment variable for config file
import os
config_file = os.getenv('CONFIG_FILE', 'config.yaml')
yaml_config = YamlConfig(config_file) 