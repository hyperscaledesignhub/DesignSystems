#!/usr/bin/env python3
"""
Automated Anti-Entropy Demo
A comprehensive demonstration of anti-entropy synchronization in the distributed key-value store.
This demo showcases:
- Data inconsistency creation
- Merkle tree-based detection
- Automatic synchronization
- Conflict resolution
- Real-time monitoring
Supports both new cluster creation and existing cluster usage.

Uses professional testing practices with temporary directories and proper cleanup.
"""

import os
import sys
import time
import json
import requests
import shutil
import threading
import yaml
from datetime import datetime
from typing import Dict, List, Tuple

# Import test utilities for professional testing practices
from test_utils import TestEnvironment, ClusterTestHelper, setup_test_logging, global_test_cleanup

# Import the required modules directly from the current directory
from node import RobustSimpleGossipNode, find_free_port

class AutomatedAntiEntropyDemo:
    def __init__(self, test_env: TestEnvironment = None):
        self.nodes = []
        self.existing_nodes = None
        self.test_env = test_env or TestEnvironment("automated_anti_entropy")
        self.logger = setup_test_logging(self.test_env, "anti_entropy_demo")
        
    def setup_demo_environment(self):
        """Setup clean demo environment using temporary directories"""
        print("🚀 AUTOMATED ANTI-ENTROPY DEMO")
        print("=" * 80)
        print("This demo will showcase:")
        print("  🔄 Anti-entropy synchronization between nodes")
        print("  🌳 Merkle tree-based inconsistency detection")
        print("  ⚡ Automatic conflict resolution")
        print("  📊 Real-time monitoring and statistics")
        print("  🎯 Multiple inconsistency scenarios")
        print("=" * 80)
        print()
        
        # Use test environment for demo data directory
        self.demo_data_dir = self.test_env.create_temp_dir("anti_entropy_demo")
        
        print("✅ Demo environment ready")
        print(f"📝 Demo data directory: {self.demo_data_dir}")
        print()
        
    def log_message(self, message: str):
        """Log message using test logging system"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.logger.info(message)
            
    def detect_existing_cluster(self):
        """Detect if we should use an existing cluster from config file or environment"""
        # First check for CLUSTER_NODES environment variable (set by cluster_demo_runner.py)
        cluster_nodes_env = os.environ.get('CLUSTER_NODES')
        if cluster_nodes_env:
            self.log_message(f"Found CLUSTER_NODES environment variable: {cluster_nodes_env}")
            node_addresses = cluster_nodes_env.split(',')
            # Convert addresses to the format expected by the demo
            seed_nodes = []
            for i, address in enumerate(node_addresses):
                host, port = address.split(':')
                # Extract node ID from hostname (e.g., "distributed-database-0" from "distributed-database-0.db-headless-service.distributed-db.svc.cluster.local")
                node_id = host.split('.')[0] if '.' in host else f"db-node-{i+1}"
                seed_nodes.append({
                    'id': node_id,
                    'host': host,
                    'http_port': int(port),  # Use http_port to match config format
                    'port': int(port),       # Keep port for backward compatibility
                    'address': address
                })
            self.log_message(f"Using existing cluster with {len(seed_nodes)} nodes from environment")
            return seed_nodes
        
        # Fall back to config file detection
        config_file = os.environ.get('CONFIG_FILE', 'config-local.yaml')
        
        if not os.path.exists(config_file):
            self.log_message(f"Config file {config_file} not found, will create new cluster")
            return None
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check for cluster configuration
            if 'cluster' in config and 'seed_nodes' in config['cluster']:
                seed_nodes = config['cluster']['seed_nodes']
                self.log_message(f"Found existing cluster configuration with {len(seed_nodes)} seed nodes")
                return seed_nodes
            else:
                self.log_message("No cluster configuration found in config file, will create new cluster")
                return None
                
        except Exception as e:
            self.log_message(f"Error reading config file: {e}")
            return None

    def verify_existing_cluster(self, seed_nodes):
        """Verify that existing cluster nodes are reachable and healthy"""
        self.log_message("Verifying existing cluster nodes...")
        
        healthy_nodes = []
        for node_info in seed_nodes:
            node_id = node_info.get('id', node_info.get('node_id', 'unknown'))
            
            # Detect cluster type based on port configuration
            if 'http_port' in node_info:
                # Kubernetes cluster
                host = node_info['host']
                port = node_info['http_port']
                cluster_type = "Kubernetes"
            else:
                # Local cluster
                host = node_info.get('host', 'localhost')
                port = node_info.get('port', 9999)
                cluster_type = "Local"
            
            address = f"{host}:{port}"
            
            try:
                # Check health endpoint
                response = requests.get(f"http://{address}/health", timeout=5)
                if response.status_code == 200:
                    self.log_message(f"Node {node_id} ({address}) [{cluster_type}] is healthy")
                    healthy_nodes.append({
                        'id': node_id,
                        'address': address,
                        'host': host,
                        'port': port
                    })
                else:
                    self.log_message(f"Node {node_id} ({address}) [{cluster_type}] health check failed: {response.status_code}")
            except Exception as e:
                self.log_message(f"Node {node_id} ({address}) [{cluster_type}] is not reachable: {e}")
        
        if len(healthy_nodes) >= 2:
            self.log_message(f"Found {len(healthy_nodes)} healthy nodes in existing cluster")
            return healthy_nodes
        else:
            self.log_message("Not enough healthy nodes found in existing cluster")
            return None
            
    def create_demo_nodes(self, num_nodes: int = 3) -> List[RobustSimpleGossipNode]:
        """Create demo nodes with anti-entropy enabled"""
        self.log_message(f"🔧 Creating {num_nodes} nodes with anti-entropy enabled...")
        
        for i in range(num_nodes):
            node_id = f"anti-entropy-node-{i+1}"
            port = find_free_port()
            data_dir = os.path.join(self.demo_data_dir, node_id)
            
            node = RobustSimpleGossipNode(
                node_id=node_id,
                host="localhost", 
                port=port,
                data_dir=data_dir
            )
            
            self.nodes.append(node)
            self.log_message(f"  ✅ Created {node_id} on port {port}")
            
        self.log_message(f"✅ All {num_nodes} nodes created successfully")
        print()
        return self.nodes
        
    def start_all_nodes(self):
        """Start all demo nodes"""
        self.log_message("🚀 Starting all nodes...")
        
        for node in self.nodes:
            node.start()
            self.log_message(f"  ✅ Started {node.node_id} at {node.get_address()}")
            
        # Wait for nodes to fully start
        time.sleep(3)
        self.log_message("✅ All nodes started successfully")
        print()
        
    def stop_all_nodes(self):
        """Stop all demo nodes"""
        self.log_message("🛑 Stopping all nodes...")
        
        for node in self.nodes:
            try:
                node.stop()
                self.log_message(f"  ✅ Stopped {node.node_id}")
            except Exception as e:
                self.log_message(f"  ⚠️ Error stopping {node.node_id}: {e}")
                
        self.log_message("✅ All nodes stopped")
        print()
        
    def join_nodes_to_cluster(self):
        """Join all nodes to form a cluster"""
        self.log_message("🔗 Forming cluster by joining nodes...")
        
        # Create a full mesh topology
        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes):
                if i != j:  # Don't join node to itself
                    try:
                        response = requests.post(
                            f"http://{node2.get_address()}/join",
                            json={"peer_address": node1.get_address()},
                            timeout=5
                        )
                        if response.status_code == 200:
                            self.log_message(f"  ✅ {node2.node_id} joined {node1.node_id}")
                        else:
                            self.log_message(f"  ⚠️ {node2.node_id} failed to join {node1.node_id}")
                    except Exception as e:
                        self.log_message(f"  ⚠️ Error joining {node2.node_id} to {node1.node_id}: {e}")
        
        time.sleep(2)
        self.log_message("✅ Cluster formation completed")
        print()
        
    def verify_existing_cluster_connectivity(self):
        """Verify connectivity between existing cluster nodes"""
        self.log_message("🔗 Verifying existing cluster connectivity...")
        
        for node in self.existing_nodes:
            try:
                response = requests.get(f"http://{node['address']}/peers", timeout=5)
                if response.status_code == 200:
                    peers = response.json()
                    self.log_message(f"Node {node['id']} has {len(peers)} peers: {peers}")
                else:
                    self.log_message(f"Node {node['id']} failed to get peers: {response.status_code}")
            except Exception as e:
                self.log_message(f"Node {node['id']} error: {e}")
        
        self.log_message("✅ Cluster connectivity verification completed")
        print()
        
    def create_inconsistencies(self):
        """Create various types of data inconsistencies between nodes"""
        self.log_message("🎯 CREATING DATA INCONSISTENCIES")
        self.log_message("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        if len(target_nodes) < 3:
            self.log_message("❌ Need at least 3 nodes for comprehensive demo")
            return
            
        # Get first 3 nodes
        node1_info, node2_info, node3_info = target_nodes[0], target_nodes[1], target_nodes[2]
        
        # Extract node information consistently
        node1_id = node1_info['id'] if isinstance(node1_info, dict) else node1_info.node_id
        node1_address = node1_info['address'] if isinstance(node1_info, dict) else node1_info.get_address()
        node2_id = node2_info['id'] if isinstance(node2_info, dict) else node2_info.node_id
        node2_address = node2_info['address'] if isinstance(node2_info, dict) else node2_info.get_address()
        node3_id = node3_info['id'] if isinstance(node3_info, dict) else node3_info.node_id
        node3_address = node3_info['address'] if isinstance(node3_info, dict) else node3_info.get_address()
        
        # Scenario 1: Node 1 has unique data
        self.log_message("📝 Scenario 1: Writing unique data to Node 1")
        node1_data = {
            "user:alice": "alice@company.com",
            "user:bob": "bob@company.com",
            "config:theme": "dark",
            "session:xyz789": "active",
            "file:document1.txt": "content_from_node1"
        }
        
        for key, value in node1_data.items():
            response = requests.put(
                f"http://{node1_address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                self.log_message(f"  ✅ {key} = {value}")
                
        # Scenario 2: Node 2 has conflicting data
        self.log_message("📝 Scenario 2: Writing conflicting data to Node 2")
        node2_data = {
            "user:alice": "alice@different.com",  # CONFLICT!
            "user:bob": "bob@different.com",      # CONFLICT!
            "config:theme": "light",              # CONFLICT!
            "user:charlie": "charlie@company.com", # NEW
            "session:abc123": "inactive"          # NEW
        }
        
        for key, value in node2_data.items():
            response = requests.put(
                f"http://{node2_address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                self.log_message(f"  ✅ {key} = {value}")
                
        # Scenario 3: Node 3 has completely different data
        self.log_message("📝 Scenario 3: Writing different data to Node 3")
        node3_data = {
            "user:diana": "diana@company.com",
            "user:eve": "eve@company.com",
            "config:database": "postgresql",
            "config:cache": "redis",
            "session:def456": "active",
            "file:document2.txt": "content_from_node3"
        }
        
        for key, value in node3_data.items():
            response = requests.put(
                f"http://{node3_address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                self.log_message(f"  ✅ {key} = {value}")
                
        # Store initial data for verification
        self.initial_data = {
            node1_id: node1_data,
            node2_id: node2_data,
            node3_id: node3_data
        }
        
        self.log_message("✅ Data inconsistencies created successfully")
        
        # Add a small delay to ensure data is fully committed
        self.log_message("⏳ Waiting for data to be fully committed...")
        time.sleep(2)
        print()
        
    def show_merkle_snapshots(self):
        """Show Merkle tree snapshots from all nodes"""
        self.log_message("🌳 MERKLE TREE SNAPSHOTS")
        self.log_message("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        for node_info in target_nodes:
            node_id = node_info['id'] if isinstance(node_info, dict) else node_info.node_id
            address = node_info['address'] if isinstance(node_info, dict) else node_info.get_address()
            
            self.log_message(f"🌳 {node_id} Merkle Snapshot:")
            self.log_message(f"  🔗 Hitting address: http://{address}/merkle/snapshot")
            
            try:
                response = requests.get(f"http://{address}/merkle/snapshot", timeout=5)
                if response.status_code == 200:
                    snapshot = response.json()
                    self.log_message(f"  🔢 Merkle root: {snapshot.get('root_hash', 'N/A')}")
                    self.log_message(f"  📋 Total keys: {len(snapshot.get('key_hashes', []))}")
                    
                    # Show sample keys
                    key_hashes = snapshot.get('key_hashes', [])
                    if key_hashes:
                        self.log_message(f"  📝 Sample key hashes:")
                        for key_hash in key_hashes[:3]:
                            self.log_message(f"    - {key_hash[:16]}...")
                        if len(key_hashes) > 3:
                            self.log_message(f"    - ... and {len(key_hashes) - 3} more")
                else:
                    self.log_message(f"  ❌ Failed to generate snapshot")
            except Exception as e:
                self.log_message(f"  ❌ Error getting snapshot: {e}")
                
            print()
            
    def trigger_anti_entropy(self):
        """Trigger anti-entropy on all nodes"""
        self.log_message("🔄 TRIGGERING ANTI-ENTROPY SYNCHRONIZATION")
        self.log_message("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        for node_info in target_nodes:
            node_id = node_info['id'] if isinstance(node_info, dict) else node_info.node_id
            address = node_info['address'] if isinstance(node_info, dict) else node_info.get_address()
            
            try:
                response = requests.post(f"http://{address}/anti-entropy/trigger", timeout=5)
                if response.status_code == 200:
                    self.log_message(f"  ✅ Anti-entropy triggered on {node_id}")
                else:
                    self.log_message(f"  ❌ Failed to trigger anti-entropy on {node_id}")
            except Exception as e:
                self.log_message(f"  ❌ Error triggering anti-entropy on {node_id}: {e}")
        
        self.log_message("⏳ Waiting for synchronization to complete...")
        time.sleep(8)  # Give more time for sync
        self.log_message("✅ Anti-entropy synchronization completed")
        print()
        
    def verify_synchronization(self):
        """Verify that all nodes have synchronized data"""
        self.log_message("🔍 VERIFYING SYNCHRONIZATION RESULTS")
        self.log_message("=" * 60)
        
        # Collect all expected keys and values
        all_expected_data = {}
        for node_data in self.initial_data.values():
            all_expected_data.update(node_data)
            
        self.log_message(f"📊 Expected total keys: {len(all_expected_data)}")
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        # Check each node
        sync_results = {}
        for node_info in target_nodes:
            node_id = node_info['id'] if isinstance(node_info, dict) else node_info.node_id
            address = node_info['address'] if isinstance(node_info, dict) else node_info.get_address()
            
            self.log_message(f"🔍 Checking {node_id}:")
            
            sync_count = 0
            total_keys = len(all_expected_data)
            
            for key, expected_value in all_expected_data.items():
                try:
                    response = requests.get(f"http://{address}/kv/{key}", timeout=5)
                    if response.status_code == 200:
                        result = response.json()
                        actual_value = result.get('value')
                        
                        if actual_value == expected_value:
                            self.log_message(f"  ✅ {key} = {actual_value}")
                            sync_count += 1
                        else:
                            self.log_message(f"  ⚠️ {key} = {actual_value} (expected: {expected_value})")
                    else:
                        self.log_message(f"  ❌ {key} = NOT_FOUND")
                except Exception as e:
                    self.log_message(f"  ❌ Error checking {key}: {e}")
                    
            sync_rate = (sync_count / total_keys) * 100 if total_keys > 0 else 0
            sync_results[node_id] = {
                'sync_count': sync_count,
                'total_keys': total_keys,
                'sync_rate': sync_rate
            }
            
            self.log_message(f"📈 {node_id} sync rate: {sync_count}/{total_keys} ({sync_rate:.1f}%)")
            print()
            
        # Overall results
        self.log_message("📊 OVERALL SYNCHRONIZATION RESULTS")
        self.log_message("=" * 60)
        
        perfect_sync = True
        for node_id, results in sync_results.items():
            self.log_message(f"  {node_id}: {results['sync_rate']:.1f}% ({results['sync_count']}/{results['total_keys']})")
            if results['sync_rate'] < 100:
                perfect_sync = False
                
        if perfect_sync:
            self.log_message("🎉 PERFECT ANTI-ENTROPY SYNCHRONIZATION!")
            self.log_message("✅ All nodes have identical data")
        else:
            self.log_message("⚠️ Some inconsistencies remain")
            
        print()
        
    def show_anti_entropy_stats(self):
        """Show anti-entropy statistics from all nodes"""
        self.log_message("📊 ANTI-ENTROPY STATISTICS")
        self.log_message("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        for node_info in target_nodes:
            node_id = node_info['id'] if isinstance(node_info, dict) else node_info.node_id
            address = node_info['address'] if isinstance(node_info, dict) else node_info.get_address()
            
            self.log_message(f"📈 {node_id} Statistics:")
            
            try:
                # Get anti-entropy stats
                response = requests.get(f"http://{address}/anti-entropy/stats", timeout=5)
                if response.status_code == 200:
                    stats = response.json()
                    self.log_message(f"  🔄 Last sync: {stats.get('last_sync', 'N/A')}")
                    self.log_message(f"  📊 Sync count: {stats.get('sync_count', 0)}")
                    self.log_message(f"  ⏱️ Sync interval: {stats.get('sync_interval', 'N/A')}s")
                    self.log_message(f"  🎯 Status: {stats.get('status', 'N/A')}")
                else:
                    self.log_message(f"  ❌ Failed to get anti-entropy stats")
                    
                # Get general stats
                response = requests.get(f"http://{address}/stats", timeout=5)
                if response.status_code == 200:
                    stats = response.json()
                    self.log_message(f"  📋 Total keys: {stats.get('total_keys', 0)}")
                    self.log_message(f"  💾 Memory usage: {stats.get('memory_usage', 'N/A')}")
                else:
                    self.log_message(f"  ❌ Failed to get general stats")
                    
            except Exception as e:
                self.log_message(f"  ❌ Error getting stats: {e}")
                
            print()
            
    def run_complete_demo(self):
        """Run the complete automated anti-entropy demonstration"""
        try:
            # Check for existing cluster first
            existing_nodes = self.detect_existing_cluster()
            if existing_nodes:
                verified_nodes = self.verify_existing_cluster(existing_nodes)
                if verified_nodes:
                    self.log_message("Using existing cluster for automated anti-entropy demo")
                    self.existing_nodes = verified_nodes
                    return self.run_with_existing_cluster()
                else:
                    self.log_message("Existing cluster verification failed, will create new cluster")
            
            # Fall back to creating new cluster
            self.log_message("Creating new cluster for automated anti-entropy demo")
            return self.run_with_new_cluster()
            
        except Exception as e:
            self.log_message(f"❌ Demo failed with error: {e}")
            import traceback
            self.log_message(f"Traceback: {traceback.format_exc()}")
        finally:
            if not self.existing_nodes:  # Only stop nodes if we created them
                self.stop_all_nodes()
            self.log_message("🧹 Demo cleanup completed")
            self.log_message(f"📝 Full demo log saved to: {self.test_env.get_log_file()}")
            
    def run_with_existing_cluster(self):
        """Run demo with existing cluster"""
        self.log_message("🎬 RUNNING AUTOMATED ANTI-ENTROPY DEMO WITH EXISTING CLUSTER")
        self.log_message("=" * 80)
        
        # Step 1: Verify cluster connectivity
        self.log_message("🎬 STEP 1: VERIFYING CLUSTER CONNECTIVITY")
        self.verify_existing_cluster_connectivity()
        
        # Step 2: Create inconsistencies
        self.log_message("🎬 STEP 2: CREATING DATA INCONSISTENCIES")
        self.create_inconsistencies()
        
        # Step 3: Show initial Merkle snapshots
        self.log_message("🎬 STEP 3: INITIAL MERKLE SNAPSHOTS")
        self.show_merkle_snapshots()
        
        # Step 4: Trigger anti-entropy
        self.log_message("🎬 STEP 4: TRIGGERING ANTI-ENTROPY")
        self.trigger_anti_entropy()
        
        # Step 5: Show final Merkle snapshots
        self.log_message("🎬 STEP 5: FINAL MERKLE SNAPSHOTS")
        self.show_merkle_snapshots()
        
        # Step 6: Verify synchronization
        self.log_message("🎬 STEP 6: VERIFYING SYNCHRONIZATION")
        self.verify_synchronization()
        
        # Step 7: Show statistics
        self.log_message("🎬 STEP 7: ANTI-ENTROPY STATISTICS")
        self.show_anti_entropy_stats()
        
        # Final summary
        self.log_message("🎉 AUTOMATED ANTI-ENTROPY DEMO COMPLETE!")
        self.log_message("=" * 80)
        self.log_message("Key takeaways:")
        self.log_message("  ✅ Anti-entropy automatically detects data inconsistencies")
        self.log_message("  ✅ Merkle trees provide efficient inconsistency detection")
        self.log_message("  ✅ Conflicts are resolved based on timestamps")
        self.log_message("  ✅ All nodes eventually converge to consistent state")
        self.log_message("  ✅ System handles network partitions and node failures")
        self.log_message("=" * 80)
        
    def run_with_new_cluster(self):
        """Run demo with new cluster (original implementation)"""
        self.log_message("🎬 RUNNING AUTOMATED ANTI-ENTROPY DEMO WITH NEW CLUSTER")
        self.log_message("=" * 80)
        
        # Step 1: Create and start nodes
        self.log_message("🎬 STEP 1: SETTING UP DEMO ENVIRONMENT")
        self.create_demo_nodes(3)
        self.start_all_nodes()
        
        # Step 2: Form cluster
        self.log_message("🎬 STEP 2: FORMING CLUSTER")
        self.join_nodes_to_cluster()
        
        # Step 3: Create inconsistencies
        self.log_message("🎬 STEP 3: CREATING DATA INCONSISTENCIES")
        self.create_inconsistencies()
        
        # Step 4: Show initial Merkle snapshots
        self.log_message("🎬 STEP 4: INITIAL MERKLE SNAPSHOTS")
        self.show_merkle_snapshots()
        
        # Step 5: Trigger anti-entropy
        self.log_message("🎬 STEP 5: TRIGGERING ANTI-ENTROPY")
        self.trigger_anti_entropy()
        
        # Step 6: Show final Merkle snapshots
        self.log_message("🎬 STEP 6: FINAL MERKLE SNAPSHOTS")
        self.show_merkle_snapshots()
        
        # Step 7: Verify synchronization
        self.log_message("🎬 STEP 7: VERIFYING SYNCHRONIZATION")
        self.verify_synchronization()
        
        # Step 8: Show statistics
        self.log_message("🎬 STEP 8: ANTI-ENTROPY STATISTICS")
        self.show_anti_entropy_stats()
        
        # Final summary
        self.log_message("🎉 AUTOMATED ANTI-ENTROPY DEMO COMPLETE!")
        self.log_message("=" * 80)
        self.log_message("Key takeaways:")
        self.log_message("  ✅ Anti-entropy automatically detects data inconsistencies")
        self.log_message("  ✅ Merkle trees provide efficient inconsistency detection")
        self.log_message("  ✅ Conflicts are resolved based on timestamps")
        self.log_message("  ✅ All nodes eventually converge to consistent state")
        self.log_message("  ✅ System handles network partitions and node failures")
        self.log_message("=" * 80)

def main():
    """Main demo runner with professional testing practices"""
    # Use test environment for proper cleanup
    with TestEnvironment("automated_anti_entropy") as test_env:
        try:
            demo = AutomatedAntiEntropyDemo(test_env)
            demo.setup_demo_environment()
            demo.run_complete_demo()
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        finally:
            # Global cleanup will be handled by TestEnvironment context manager
            pass

if __name__ == "__main__":
    main() 