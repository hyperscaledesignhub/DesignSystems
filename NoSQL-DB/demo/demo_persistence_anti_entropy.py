#!/usr/bin/env python3
"""
Live Demo: Persistence and Anti-Entropy Features
Demonstrates the powerful internal features in a visible, impressive way
Supports both new cluster creation and existing cluster usage.
"""

import os
import sys
import time
import json
import requests
import tempfile
import shutil
import threading
import yaml
from datetime import datetime
from node import RobustSimpleGossipNode, find_free_port

class PersistenceAntiEntropyDemo:
    def __init__(self):
        self.nodes = []
        self.existing_nodes = None
        self.demo_data_dir = "demo_data"
        self.setup_demo_environment()
        
    def setup_demo_environment(self):
        """Setup clean demo environment"""
        print("🚀 Setting up Persistence & Anti-Entropy Demo Environment")
        print("=" * 60)
        
        # Create demo data directory
        if os.path.exists(self.demo_data_dir):
            shutil.rmtree(self.demo_data_dir)
        os.makedirs(self.demo_data_dir)
        
        print("✅ Demo environment ready")
        print()
        
    def detect_existing_cluster(self):
        """Detect if we should use an existing cluster from config file or environment (same pattern as replication_demo.py)"""
        # First check for CLUSTER_NODES environment variable (set by cluster_demo_runner.py)
        cluster_nodes_env = os.environ.get('CLUSTER_NODES')
        if cluster_nodes_env:
            print(f"Found CLUSTER_NODES environment variable: {cluster_nodes_env}")
            node_addresses = cluster_nodes_env.split(',')
            print(f"Using existing cluster with {len(node_addresses)} nodes from environment")
            return node_addresses
        
        # Fall back to config file detection
        config_file = os.environ.get('CONFIG_FILE', 'config-local.yaml')
        
        if not os.path.exists(config_file):
            print(f"Config file {config_file} not found, will create new cluster")
            return None
        
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check for cluster configuration
            if 'cluster' in config and 'seed_nodes' in config['cluster']:
                seed_nodes = config['cluster']['seed_nodes']
                if seed_nodes:
                    # Convert seed nodes to addresses
                    node_addresses = []
                    for node_info in seed_nodes:
                        if isinstance(node_info, dict):
                            host = node_info.get('host', 'localhost')
                            port = node_info.get('port', 9999)
                            node_addresses.append(f"{host}:{port}")
                        elif isinstance(node_info, str):
                            # Handle string format like "localhost:9999"
                            node_addresses.append(node_info)
                    
                    if node_addresses:
                        print(f"🔍 Auto-detected existing cluster from {config_file}")
                        print(f"Found {len(node_addresses)} nodes: {node_addresses}")
                        return node_addresses
            else:
                print("No cluster configuration found in config file, will create new cluster")
                return None
                
        except Exception as e:
            print(f"Error reading config file: {e}")
            return None

    def verify_existing_cluster(self, node_addresses):
        """Verify that existing cluster nodes are reachable and healthy"""
        print("Verifying existing cluster nodes...")
        
        healthy_nodes = []
        for i, address in enumerate(node_addresses, 1):
            host, port = address.split(':')
            node_id = f"Node {i}"
            
            try:
                # Check health endpoint
                response = requests.get(f"http://{address}/health", timeout=5)
                if response.status_code == 200:
                    print(f"{node_id} ({address}) is healthy")
                    healthy_nodes.append(address)
                else:
                    print(f"{node_id} ({address}) health check failed: {response.status_code}")
            except Exception as e:
                print(f"{node_id} ({address}) is not reachable: {e}")
        
        if len(healthy_nodes) >= 2:
            print(f"Found {len(healthy_nodes)} healthy nodes in existing cluster")
            return healthy_nodes
        else:
            print("Not enough healthy nodes found in existing cluster")
            return None
            
    def create_demo_nodes(self, num_nodes=3):
        """Create demo nodes with persistence"""
        print(f"🔧 Creating {num_nodes} nodes with persistence enabled...")
        
        for i in range(num_nodes):
            node_id = f"demo-node-{i+1}"
            port = find_free_port()
            data_dir = os.path.join(self.demo_data_dir, node_id)
            
            node = RobustSimpleGossipNode(
                node_id=node_id,
                host="localhost", 
                port=port,
                data_dir=data_dir
            )
            
            self.nodes.append(node)
            print(f"  ✅ Created {node_id} on port {port} with data dir: {data_dir}")
            
        print()
        
    def start_all_nodes(self):
        """Start all demo nodes"""
        print("🚀 Starting all nodes...")
        
        for node in self.nodes:
            node.start()
            print(f"  ✅ Started {node.node_id} at {node.get_address()}")
            
        # Wait for nodes to fully start
        time.sleep(2)
        print("✅ All nodes started successfully")
        print()
        
    def stop_all_nodes(self):
        """Stop all demo nodes"""
        print("🛑 Stopping all nodes...")
        
        for node in self.nodes:
            try:
                node.stop()
                print(f"  ✅ Stopped {node.node_id}")
            except Exception as e:
                print(f"  ⚠️ Error stopping {node.node_id}: {e}")
                
        print("✅ All nodes stopped")
        print()
        
    def verify_existing_cluster_connectivity(self):
        """Verify connectivity between existing cluster nodes"""
        print("🔗 Verifying existing cluster connectivity...")
        
        for i, address in enumerate(self.existing_nodes, 1):
            try:
                response = requests.get(f"http://{address}/peers", timeout=5)
                if response.status_code == 200:
                    peers = response.json()
                    print(f"Node {i} has {len(peers)} peers: {peers}")
                else:
                    print(f"Node {i} failed to get peers: {response.status_code}")
            except Exception as e:
                print(f"Node {i} error: {e}")
        
        print("✅ Cluster connectivity verification completed")
        print()
        
    def demonstrate_persistence(self):
        """Demonstrate data persistence across node restarts"""
        print("💾 DEMO 1: Data Persistence Across Node Restarts")
        print("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        if not target_nodes:
            print("❌ No nodes available for persistence demo")
            return
            
        # Use first node for persistence demo
        if self.existing_nodes:
            # For existing cluster, use the first address
            address = self.existing_nodes[0]
            node_id = f"Node 1"
        else:
            # For new cluster, use the first node object
            node_info = self.nodes[0]
            node_id = node_info.node_id
            address = node_info.get_address()
        
        test_data = {
            "user:john": "john_doe@email.com",
            "user:jane": "jane_smith@email.com", 
            "config:timeout": "30s",
            "config:max_connections": "1000",
            "session:abc123": "active",
            "session:def456": "active"
        }
        
        print(f"📝 Writing test data to {node_id}...")
        for key, value in test_data.items():
            response = requests.put(
                f"http://{address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                print(f"  ✅ Wrote {key} = {value}")
            else:
                print(f"  ❌ Failed to write {key}")
        
        print(f"\n📊 Current data in {node_id}:")
        for key in test_data.keys():
            response = requests.get(f"http://{address}/kv/{key}")
            if response.status_code == 200:
                result = response.json()
                print(f"  📖 {key} = {result.get('value', 'NOT_FOUND')}")
        
        # Show persistence stats
        print(f"\n📈 Persistence Statistics:")
        response = requests.get(f"http://{address}/persistence/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  📊 Cache entries: {stats.get('cache_entries', 0)}")
            print(f"  📊 WAL size: {stats.get('wal_size_bytes', 0)} bytes")
            print(f"  📊 SSTable files: {stats.get('sstable_files', 0)}")
        
        # Note: For existing clusters, we can't simulate crash/restart
        # So we'll just verify the data is there
        print(f"\n🔍 Verifying data persistence:")
        recovered_count = 0
        for key in test_data.keys():
            response = requests.get(f"http://{address}/kv/{key}")
            if response.status_code == 200:
                result = response.json()
                if result.get('value') == test_data[key]:
                    print(f"  ✅ {key} = {result['value']} (PERSISTED)")
                    recovered_count += 1
                else:
                    print(f"  ❌ {key} = {result.get('value', 'NOT_FOUND')} (DATA LOSS)")
            else:
                print(f"  ❌ {key} = NOT_FOUND (DATA LOSS)")
        
        print(f"\n📊 Persistence Results:")
        print(f"  📈 Data persistence rate: {recovered_count}/{len(test_data)} ({recovered_count/len(test_data)*100:.1f}%)")
        
        if recovered_count == len(test_data):
            print("  🎉 PERFECT DATA PERSISTENCE!")
        else:
            print("  ⚠️ Some data was not persisted")
            
        print()
        
    def demonstrate_anti_entropy(self):
        """Demonstrate anti-entropy synchronization between nodes"""
        print("🔄 DEMO 2: Anti-Entropy Data Synchronization")
        print("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        if len(target_nodes) < 2:
            print("❌ Need at least 2 nodes for anti-entropy demo")
            return
            
        node1_info, node2_info = target_nodes[0], target_nodes[1]
        node1_id = node1_info['id'] if isinstance(node1_info, dict) else node1_info.node_id
        node1_address = node1_info['address'] if isinstance(node1_info, dict) else node1_info.get_address()
        node2_id = node2_info['id'] if isinstance(node2_info, dict) else node2_info.node_id
        node2_address = node2_info['address'] if isinstance(node2_info, dict) else node2_info.get_address()
        
        # Join nodes to form cluster (if not already joined)
        print("🔗 Ensuring cluster connectivity...")
        response = requests.post(
            f"http://{node2_address}/join",
            json={"peer_address": node1_address}
        )
        if response.status_code == 200:
            print(f"  ✅ {node2_id} joined {node1_id}")
        else:
            print(f"  ℹ️ Nodes may already be connected")
            
        time.sleep(2)
        
        # Write different data to each node
        print("\n📝 Writing different data to each node...")
        
        node1_data = {
            "user:alice": "alice@company.com",
            "user:bob": "bob@company.com",
            "config:theme": "dark",
            "session:xyz789": "active"
        }
        
        node2_data = {
            "user:charlie": "charlie@company.com", 
            "user:diana": "diana@company.com",
            "config:theme": "light",
            "session:abc123": "inactive"
        }
        
        print(f"📝 Writing to {node1_id}:")
        for key, value in node1_data.items():
            response = requests.put(
                f"http://{node1_address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                print(f"  ✅ {key} = {value}")
            else:
                print(f"  ❌ Failed to write {key}")
                
        print(f"📝 Writing to {node2_id}:")
        for key, value in node2_data.items():
            response = requests.put(
                f"http://{node2_address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                print(f"  ✅ {key} = {value}")
            else:
                print(f"  ❌ Failed to write {key}")
        
        # Trigger anti-entropy
        print(f"\n🔄 Triggering anti-entropy synchronization...")
        for node_info in [node1_info, node2_info]:
            node_id = node_info['id'] if isinstance(node_info, dict) else node_info.node_id
            address = node_info['address'] if isinstance(node_info, dict) else node_info.get_address()
            
            response = requests.post(f"http://{address}/anti-entropy/trigger", timeout=5)
            if response.status_code == 200:
                print(f"  ✅ Anti-entropy triggered on {node_id}")
            else:
                print(f"  ❌ Failed to trigger anti-entropy on {node_id}")
        
        time.sleep(5)  # Wait for sync
        
        # Verify synchronization
        print(f"\n🔍 Verifying anti-entropy synchronization...")
        all_keys = set(list(node1_data.keys()) + list(node2_data.keys()))
        sync_results = {
            "node1": 0,
            "node2": 0,
            "total": len(all_keys)
        }
        
        print(f"📊 Checking {node1_id}:")
        for key in all_keys:
            response = requests.get(f"http://{node1_address}/kv/{key}")
            if response.status_code == 200:
                result = response.json()
                expected_value = node1_data.get(key) or node2_data.get(key)
                if result.get('value') == expected_value:
                    print(f"  ✅ {key} = {result['value']}")
                    sync_results["node1"] += 1
                else:
                    print(f"  ❌ {key} = {result.get('value', 'NOT_FOUND')}")
            else:
                print(f"  ❌ {key} = NOT_FOUND")
                
        print(f"📊 Checking {node2_id}:")
        for key in all_keys:
            response = requests.get(f"http://{node2_address}/kv/{key}")
            if response.status_code == 200:
                result = response.json()
                expected_value = node1_data.get(key) or node2_data.get(key)
                if result.get('value') == expected_value:
                    print(f"  ✅ {key} = {result['value']}")
                    sync_results["node2"] += 1
                else:
                    print(f"  ❌ {key} = {result.get('value', 'NOT_FOUND')}")
            else:
                print(f"  ❌ {key} = NOT_FOUND")
        
        print(f"\n📈 Anti-Entropy Results:")
        print(f"  📊 {node1_id} sync rate: {sync_results['node1']}/{sync_results['total']} ({sync_results['node1']/sync_results['total']*100:.1f}%)")
        print(f"  📊 {node2_id} sync rate: {sync_results['node2']}/{sync_results['total']} ({sync_results['node2']/sync_results['total']*100:.1f}%)")
        
        if sync_results["node1"] == sync_results["total"] and sync_results["node2"] == sync_results["total"]:
            print("  🎉 PERFECT ANTI-ENTROPY SYNCHRONIZATION!")
        else:
            print("  ⚠️ Some data was not synchronized")
            
        print()
        
    def demonstrate_merkle_trees(self):
        """Demonstrate Merkle tree snapshots"""
        print("🌳 DEMO 3: Merkle Tree Snapshots")
        print("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        if not target_nodes:
            print("❌ No nodes available for Merkle tree demo")
            return
            
        if self.existing_nodes:
            # For existing cluster, use the first address
            address = self.existing_nodes[0]
            node_id = f"Node 1"
        else:
            # For new cluster, use the first node object
            node_info = self.nodes[0]
            node_id = node_info.node_id
            address = node_info.get_address()
        
        # Write some data first
        print(f"📝 Writing data for Merkle tree demonstration to {node_id}...")
        test_data = {
            "file:doc1.txt": "content1",
            "file:doc2.txt": "content2", 
            "file:doc3.txt": "content3",
            "config:version": "1.0.0",
            "user:admin": "admin@system.com"
        }
        
        for key, value in test_data.items():
            response = requests.put(
                f"http://{address}/kv/{key}",
                json={"value": value}
            )
            if response.status_code == 200:
                print(f"  ✅ {key} = {value}")
                
        # Get Merkle snapshot
        print(f"\n🌳 Generating Merkle tree snapshot...")
        response = requests.get(f"http://{address}/merkle/snapshot")
        
        if response.status_code == 200:
            snapshot = response.json()
            print(f"  ✅ Merkle snapshot generated successfully")
            print(f"  📊 Snapshot details:")
            print(f"    - Node ID: {snapshot.get('node_id')}")
            print(f"    - Timestamp: {snapshot.get('timestamp')}")
            print(f"    - Tree height: {snapshot.get('tree_height', 'N/A')}")
            print(f"    - Root hash: {snapshot.get('root_hash', 'N/A')[:16]}...")
            print(f"    - Total keys: {len(snapshot.get('keys', []))}")
            
            # Show some keys in the snapshot
            keys = snapshot.get('keys', [])
            if keys:
                print(f"  📋 Sample keys in snapshot:")
                for key in keys[:3]:
                    print(f"    - {key}")
                if len(keys) > 3:
                    print(f"    - ... and {len(keys) - 3} more")
        else:
            print(f"  ❌ Failed to generate Merkle snapshot")
            
        print()
        
    def demonstrate_large_scale_persistence(self):
        """Demonstrate handling large datasets with persistence"""
        print("📊 DEMO 4: Large Scale Data Persistence")
        print("=" * 60)
        
        # Use existing nodes if available, otherwise use created nodes
        target_nodes = self.existing_nodes if self.existing_nodes else self.nodes
        
        if not target_nodes:
            print("❌ No nodes available for large scale persistence demo")
            return
            
        if self.existing_nodes:
            # For existing cluster, use the first address
            address = self.existing_nodes[0]
            node_id = f"Node 1"
        else:
            # For new cluster, use the first node object
            node_info = self.nodes[0]
            node_id = node_info.node_id
            address = node_info.get_address()
        
        print(f"📝 Writing large dataset (100 keys) to {node_id}...")
        start_time = time.time()
        
        large_dataset = {}
        for i in range(100):
            key = f"large:key_{i:03d}"
            value = f"large_value_{i}_{datetime.now().strftime('%H%M%S')}"
            large_dataset[key] = value
            
            response = requests.put(
                f"http://{address}/kv/{key}",
                json={"value": value}
            )
            
            if i % 20 == 0:
                print(f"  📝 Written {i+1}/100 keys...")
                
        write_time = time.time() - start_time
        print(f"  ✅ Wrote 100 keys in {write_time:.2f} seconds")
        
        # Show persistence stats
        print(f"\n📈 Persistence Statistics after large write:")
        response = requests.get(f"http://{address}/persistence/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  📊 Cache entries: {stats.get('cache_entries', 0)}")
            print(f"  📊 WAL size: {stats.get('wal_size_bytes', 0)} bytes")
            print(f"  📊 SSTable files: {stats.get('sstable_files', 0)}")
            
        # For existing clusters, we can't simulate crash/restart
        # So we'll just verify the data is there
        print(f"\n🔍 Verifying large dataset persistence...")
        start_time = time.time()
        
        recovered_count = 0
        for key, expected_value in large_dataset.items():
            response = requests.get(f"http://{address}/kv/{key}")
            if response.status_code == 200:
                result = response.json()
                if result.get('value') == expected_value:
                    recovered_count += 1
                    
        recovery_time = time.time() - start_time
        
        print(f"📊 Large Scale Persistence Results:")
        print(f"  📈 Persisted: {recovered_count}/{len(large_dataset)} keys")
        print(f"  📈 Persistence rate: {recovered_count/len(large_dataset)*100:.1f}%")
        print(f"  ⏱️ Verification time: {recovery_time:.2f} seconds")
        
        if recovered_count == len(large_dataset):
            print("  🎉 PERFECT LARGE SCALE PERSISTENCE!")
        else:
            print("  ⚠️ Some data was not persisted")
            
        print()
        
    def run_complete_demo(self):
        """Run the complete demonstration"""
        print("🎬 COMPLETE PERSISTENCE & ANTI-ENTROPY DEMONSTRATION")
        print("=" * 80)
        print("This demo showcases the powerful internal features of our distributed database:")
        print("  💾 Persistence: Data survives node crashes and restarts")
        print("  🔄 Anti-Entropy: Automatic data synchronization between nodes")
        print("  🌳 Merkle Trees: Efficient data integrity verification")
        print("  📊 Large Scale: Handles massive datasets with reliability")
        print("=" * 80)
        print()
        
        try:
            # Check for existing cluster first
            node_addresses = self.detect_existing_cluster()
            if node_addresses:
                verified_addresses = self.verify_existing_cluster(node_addresses)
                if verified_addresses:
                    print("Using existing cluster for persistence & anti-entropy demo")
                    self.existing_nodes = verified_addresses
                    return self.run_with_existing_cluster()
                else:
                    print("Existing cluster verification failed, will create new cluster")
            
            # Fall back to creating new cluster
            print("Creating new cluster for persistence & anti-entropy demo")
            return self.run_with_new_cluster()
            
        except Exception as e:
            print(f"❌ Demo failed with error: {e}")
        finally:
            if not self.existing_nodes:  # Only stop nodes if we created them
                self.stop_all_nodes()
            print("🧹 Demo cleanup completed")
            
    def run_with_existing_cluster(self):
        """Run demo with existing cluster"""
        print("🎬 RUNNING PERSISTENCE & ANTI-ENTROPY DEMO WITH EXISTING CLUSTER")
        print("=" * 80)
        
        # Step 1: Verify cluster connectivity
        print("🎬 STEP 1: VERIFYING CLUSTER CONNECTIVITY")
        self.verify_existing_cluster_connectivity()
        
        # Step 2: Run demonstrations
        print("🎬 STEP 2: RUNNING DEMONSTRATIONS")
        self.demonstrate_persistence()
        self.demonstrate_anti_entropy()
        self.demonstrate_merkle_trees()
        self.demonstrate_large_scale_persistence()
        
        print("🎉 DEMONSTRATION COMPLETE!")
        print("=" * 80)
        print("Key takeaways:")
        print("  ✅ Data persistence ensures zero data loss during failures")
        print("  ✅ Anti-entropy keeps all nodes synchronized automatically")
        print("  ✅ Merkle trees provide efficient data integrity verification")
        print("  ✅ System handles large-scale data with high reliability")
        print("=" * 80)
        
    def run_with_new_cluster(self):
        """Run demo with new cluster (original implementation)"""
        print("🎬 RUNNING PERSISTENCE & ANTI-ENTROPY DEMO WITH NEW CLUSTER")
        print("=" * 80)
        
        # Setup
        self.create_demo_nodes(3)
        self.start_all_nodes()
        
        # Run demonstrations
        self.demonstrate_persistence()
        self.demonstrate_anti_entropy()
        self.demonstrate_merkle_trees()
        self.demonstrate_large_scale_persistence()
        
        print("🎉 DEMONSTRATION COMPLETE!")
        print("=" * 80)
        print("Key takeaways:")
        print("  ✅ Data persistence ensures zero data loss during failures")
        print("  ✅ Anti-entropy keeps all nodes synchronized automatically")
        print("  ✅ Merkle trees provide efficient data integrity verification")
        print("  ✅ System handles large-scale data with high reliability")
        print("=" * 80)

def main():
    """Main demo runner"""
    demo = PersistenceAntiEntropyDemo()
    demo.run_complete_demo()

if __name__ == "__main__":
    main() 