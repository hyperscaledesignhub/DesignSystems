#!/usr/bin/env python3
"""
Professional Test Utilities for Distributed Database Tests

This module provides utilities for professional testing practices:
- Temporary directory management
- Test data isolation
- Proper cleanup mechanisms
- Test environment setup/teardown
"""

import os
import sys
import tempfile
import shutil
import time
import requests
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import logging

# Add distributed path to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'distributed'))

class TestEnvironment:
    """Professional test environment manager"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.temp_dirs = []
        self.created_files = []
        self.test_data_dir = None
        self.original_cwd = os.getcwd()
        
    def __enter__(self):
        """Setup test environment"""
        # Create test-specific temporary directory
        self.test_data_dir = tempfile.mkdtemp(prefix=f"test_{self.test_name}_")
        self.temp_dirs.append(self.test_data_dir)
        
        # Create subdirectories for different test data types
        self.persistence_dir = os.path.join(self.test_data_dir, "persistence")
        self.logs_dir = os.path.join(self.test_data_dir, "logs")
        self.cache_dir = os.path.join(self.test_data_dir, "cache")
        
        os.makedirs(self.persistence_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Set environment variables for tests
        os.environ['TEST_DATA_DIR'] = self.test_data_dir
        os.environ['TEST_LOGS_DIR'] = self.logs_dir
        os.environ['TEST_PERSISTENCE_DIR'] = self.persistence_dir
        
        print(f"🧪 Test environment created: {self.test_data_dir}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment"""
        self.cleanup()
        
    def cleanup(self):
        """Clean up all test artifacts"""
        print(f"🧹 Cleaning up test environment...")
        
        # Remove all temporary directories
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"   ✅ Removed: {temp_dir}")
                except Exception as e:
                    print(f"   ⚠️ Failed to remove {temp_dir}: {e}")
        
        # Remove created files
        for file_path in self.created_files:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                except Exception as e:
                    print(f"   ⚠️ Failed to remove {file_path}: {e}")
        
        # Clear environment variables
        for var in ['TEST_DATA_DIR', 'TEST_LOGS_DIR', 'TEST_PERSISTENCE_DIR']:
            if var in os.environ:
                del os.environ[var]
        
        self.temp_dirs.clear()
        self.created_files.clear()
        
    def create_temp_dir(self, name: str) -> str:
        """Create a temporary directory for specific test data"""
        temp_dir = os.path.join(self.test_data_dir, name)
        os.makedirs(temp_dir, exist_ok=True)
        self.temp_dirs.append(temp_dir)
        return temp_dir
        
    def create_temp_file(self, name: str, content: str = "") -> str:
        """Create a temporary file with content"""
        file_path = os.path.join(self.test_data_dir, name)
        with open(file_path, 'w') as f:
            f.write(content)
        self.created_files.append(file_path)
        return file_path

@contextmanager
def temporary_test_environment(test_name: str):
    """Context manager for temporary test environment"""
    env = TestEnvironment(test_name)
    try:
        yield env
    finally:
        env.cleanup()

class ClusterTestHelper:
    """Helper for cluster-based tests"""
    
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.test_data_dirs = {}
        
    def setup_node_data_dirs(self, test_env: TestEnvironment) -> Dict[str, str]:
        """Setup temporary data directories for each node"""
        node_dirs = {}
        for i, node in enumerate(self.nodes):
            node_id = f"db-node-{i+1}"
            node_dir = test_env.create_temp_dir(f"node_{i+1}")
            node_dirs[node] = node_dir
            self.test_data_dirs[node] = node_dir
        return node_dirs
        
    def wait_for_node_ready(self, node_address: str, timeout: int = 30) -> bool:
        """Wait for a node to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"http://{node_address}/health", timeout=1)
                if response.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False
        
    def verify_cluster_health(self, timeout: int = 30) -> bool:
        """Verify all nodes in cluster are healthy"""
        print(f"🔍 Verifying cluster health for {len(self.nodes)} nodes...")
        
        for node in self.nodes:
            if not self.wait_for_node_ready(node, timeout):
                print(f"❌ Node {node} is not healthy")
                return False
            print(f"✅ Node {node} is healthy")
        
        return True
        
    def cleanup_node_data(self):
        """Clean up node data directories"""
        for node_dir in self.test_data_dirs.values():
            if os.path.exists(node_dir):
                shutil.rmtree(node_dir, ignore_errors=True)

def create_test_config(test_env: TestEnvironment, nodes: List[str]) -> str:
    """Create a temporary test configuration file"""
    config_content = f"""
cluster:
  seed_nodes:
"""
    
    for i, node in enumerate(nodes):
        host, port = node.split(':')
        config_content += f"""
    - id: db-node-{i+1}
      host: {host}
      http_port: {port}
      db_port: {port}
      persistent_port: {int(port) + 1000}
      failure_detection_port: {int(port) + 2000}
      anti_entropy_port: {int(port) + 3000}
      monitoring_port: {int(port) + 4000}
"""
    
    config_file = test_env.create_temp_file("test_config.yaml", config_content)
    return config_file

def setup_test_logging(test_env: TestEnvironment, node_id: str = None) -> logging.Logger:
    """Setup test-specific logging"""
    from logging_utils import setup_logging
    
    # Override logs directory for tests
    os.environ['LOGS_DIR'] = test_env.logs_dir
    
    if node_id:
        logger = setup_logging(node_id=node_id)
    else:
        logger = setup_logging()
    
    return logger

def cleanup_test_artifacts():
    """Clean up any remaining test artifacts in the project root"""
    # Remove any test-related directories that might have been created
    test_dirs_to_clean = [
        "test_data",
        "test_logs", 
        "test_persistence",
        "temp_test",
        "demo_data",
        "automated_anti_entropy_demo_data"
    ]
    
    for dir_name in test_dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name, ignore_errors=True)
                print(f"🧹 Cleaned up: {dir_name}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {dir_name}: {e}")
    
    # Remove test log files from demo directory
    demo_dir = os.path.dirname(__file__)
    for file in os.listdir(demo_dir):
        if file.endswith('.log') and 'demo' in file:
            try:
                os.remove(os.path.join(demo_dir, file))
                print(f"🧹 Cleaned up: {file}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {file}: {e}")

# Global cleanup function to be called at the end of test suites
def global_test_cleanup():
    """Global cleanup function for all tests"""
    print("🧹 Performing global test cleanup...")
    cleanup_test_artifacts()
    
    # Also clean up any data directories that might have been created
    if os.path.exists("data"):
        try:
            shutil.rmtree("data", ignore_errors=True)
            print("🧹 Cleaned up: data/")
        except Exception as e:
            print(f"⚠️ Failed to clean up data/: {e}") 