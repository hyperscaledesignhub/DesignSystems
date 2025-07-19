#!/usr/bin/env python3
"""
Unified Cluster Demo Runner with Professional Testing Practices

This script provides a unified interface to run distributed database demos on:
1. Existing cluster (nodes already running, specified in config file)
2. New cluster (creates and manages nodes as needed)

PROFESSIONAL FEATURES:
- Temporary directory management for test isolation
- Automatic cleanup after each demo
- Professional error handling and reporting
- Test result tracking and metrics
- Centralized logging to logs/ folder

FEATURES:
- Automatic cluster management (start/stop nodes)
- Support for multiple config formats (local, Kubernetes, custom)
- Demo execution with proper environment setup
- Cluster verification and health checks
- Automatic cleanup of created resources

AVAILABLE DEMOS:
- vector_clock_db: Vector clock functionality with causal consistency
- convergence: Multi-node convergence and conflict resolution
- anti_entropy: Anti-entropy synchronization between nodes
- automated_anti_entropy: Automated anti-entropy with data verification
- consistent_hashing: Consistent hashing and data distribution
- replication: Data replication and consistency
- quick: Quick overview of all features
- persistence_anti_entropy: Persistence with anti-entropy

CONFIG FILES:
- config-local.yaml: Local development cluster (localhost:9999-10001)
- config.yaml: Kubernetes cluster (default)
- Any custom YAML config with cluster.seed_nodes or nodes section

USAGE EXAMPLES:

1. Run on existing local cluster:
   python cluster_demo_runner.py vector_clock_db --config config-local.yaml --use-existing

2. Run on existing Kubernetes cluster:
   python cluster_demo_runner.py convergence --config config.yaml --use-existing

3. Create new local cluster and run demo:
   python cluster_demo_runner.py anti_entropy --config config-local.yaml

4. Create new cluster from custom config:
   python cluster_demo_runner.py consistent_hashing --config my-custom-config.yaml

5. Quick demo on local cluster:
   python cluster_demo_runner.py quick --config config-local.yaml

ENVIRONMENT VARIABLES:
- CONFIG_FILE: Override default config file
- SEED_NODE_ID: Node ID for new nodes (auto-generated if not set)

CLUSTER MANAGEMENT:
- Automatically starts nodes on ports 9999, 10000, 10001 (configurable)
- Forms cluster by joining nodes together
- Verifies cluster health before running demos
- Cleans up created nodes after demo completion

For more details on each demo, see the individual demo files in this directory.
"""

import argparse
import yaml
import subprocess
import time
import requests
import os
import signal
import sys
from typing import Dict, List, Optional, Tuple
import importlib.util

# Add distributed path to Python path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'distributed'))

# Import professional testing utilities
from test_utils import TestEnvironment, setup_test_logging, global_test_cleanup

class ClusterDemoRunner:
    """Unified demo runner for cluster-based demos with professional testing practices"""
    
    def __init__(self, config_file: str = "config-local.yaml", test_env: TestEnvironment = None):
        self.config_file = config_file
        self.test_env = test_env
        self.logger = setup_test_logging(test_env, "cluster_demo_runner") if test_env else None
        self.config = self.load_config()
        self.nodes = []
        self.created_nodes = []
        self.test_results = {}
        
    def load_config(self) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✅ Loaded config from {self.config_file}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.info(f"Loaded config from {self.config_file}")
            return config
        except Exception as e:
            print(f"❌ Failed to load config {self.config_file}: {e}")
            if hasattr(self, 'logger') and self.logger:
                self.logger.error(f"Failed to load config {self.config_file}: {e}")
            sys.exit(1)
    
    def get_existing_nodes(self) -> List[Dict]:
        """Get existing nodes from config"""
        nodes = []
        
        # Check for different config formats
        if 'nodes' in self.config:
            # Direct nodes list
            for node_config in self.config['nodes']:
                nodes.append({
                    'id': node_config.get('id', f"node-{len(nodes)}"),
                    'address': f"{node_config.get('host', 'localhost')}:{node_config.get('port', 9999)}",
                    'process': None  # Existing node, no process to manage
                })
        
        elif 'cluster' in self.config and 'seed_nodes' in self.config['cluster']:
            # Current config format with cluster.seed_nodes
            for node_config in self.config['cluster']['seed_nodes']:
                nodes.append({
                    'id': node_config.get('id', f"node-{len(nodes)}"),
                    'address': f"{node_config.get('host', 'localhost')}:{node_config.get('http_port', 9999)}",
                    'process': None  # Existing node, no process to manage
                })
        
        elif 'kubernetes' in self.config:
            # Kubernetes config
            k8s_config = self.config['kubernetes']
            service_name = k8s_config.get('service_name', 'kvdb-service')
            namespace = k8s_config.get('namespace', 'default')
            replicas = k8s_config.get('replicas', 3)
            
            for i in range(replicas):
                nodes.append({
                    'id': f"{service_name}-{i}",
                    'address': f"{service_name}-{i}.{service_name}.{namespace}.svc.cluster.local:9999",
                    'process': None
                })
        
        elif 'local' in self.config:
            # Local cluster config
            local_config = self.config['local']
            base_port = local_config.get('base_port', 9999)
            node_count = local_config.get('node_count', 3)
            
            for i in range(node_count):
                nodes.append({
                    'id': f"db-node-{i+1}",
                    'address': f"localhost:{base_port + i}",
                    'process': None
                })
        
        print(f"📋 Found {len(nodes)} existing nodes in config")
        for node in nodes:
            print(f"   - {node['id']}: {node['address']}")
        
        return nodes
    
    def wait_for_node_ready(self, address: str, timeout: int = 15) -> bool:
        """Wait for a node to be ready"""
        start = time.time()
        while time.time() - start < timeout:
            try:
                r = requests.get(f"http://{address}/health", timeout=1)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False
    
    def verify_existing_cluster(self, nodes: List[Dict]) -> bool:
        """Verify that existing nodes are reachable"""
        print(f"\n🔍 Verifying existing cluster ({len(nodes)} nodes)...")
        
        reachable_nodes = []
        for node in nodes:
            if self.wait_for_node_ready(node['address'], timeout=10):
                print(f"✅ {node['id']} is reachable at {node['address']}")
                reachable_nodes.append(node)
            else:
                print(f"❌ {node['id']} is not reachable at {node['address']}")
        
        if len(reachable_nodes) == 0:
            print("❌ No nodes are reachable!")
            return False
        
        if len(reachable_nodes) < len(nodes):
            print(f"⚠️ Only {len(reachable_nodes)}/{len(nodes)} nodes are reachable")
        
        self.nodes = reachable_nodes
        return True
    
    def start_new_cluster(self) -> bool:
        """Start a new cluster based on config"""
        print(f"\n🚀 Starting new cluster from {self.config_file}...")
        
        nodes = []
        base_port = 9999
        node_count = 3
        
        # Determine cluster setup from config
        if 'local' in self.config:
            local_config = self.config['local']
            base_port = local_config.get('base_port', 9999)
            node_count = local_config.get('node_count', 3)
        
        for i in range(node_count):
            node_id = f"db-node-{i+1}"
            port = base_port + i
            address = f"localhost:{port}"
            
            # Start node process
            env = dict(os.environ)
            env['SEED_NODE_ID'] = node_id
            env['CONFIG_FILE'] = self.config_file
            
            process = subprocess.Popen(
                ["python", "robust_gossip_wrapper.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            print(f"Starting {node_id} on {address}...")
            
            if self.wait_for_node_ready(address, timeout=20):
                print(f"✅ {node_id} is healthy!")
                nodes.append({
                    'id': node_id,
                    'address': address,
                    'process': process
                })
            else:
                print(f"❌ {node_id} failed to become healthy!")
                process.terminate()
                return False
        
        # Form cluster
        if len(nodes) > 1:
            print("\n🔗 Forming cluster...")
            for i in range(1, len(nodes)):
                try:
                    response = requests.post(
                        f"http://{nodes[i]['address']}/join",
                        json={"address": nodes[0]['address']},
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"✅ {nodes[i]['id']} joined {nodes[0]['id']}")
                    else:
                        print(f"❌ Failed to join {nodes[i]['id']}")
                except Exception as e:
                    print(f"❌ Error joining {nodes[i]['id']}: {e}")
            
            print("⏳ Waiting for cluster to stabilize...")
            time.sleep(5)
        
        self.nodes = nodes
        self.created_nodes = nodes
        return True
    
    def cleanup_created_nodes(self):
        """Clean up nodes that were created by this runner"""
        if not self.created_nodes:
            return
        
        print("\n🧹 Cleaning up created nodes...")
        for node in self.created_nodes:
            if node['process']:
                try:
                    node['process'].terminate()
                    node['process'].wait(timeout=5)
                    print(f"✅ Stopped {node['id']}")
                except Exception as e:
                    print(f"❌ Error stopping {node['id']}: {e}")
                    try:
                        node['process'].kill()
                    except:
                        pass
    
    def run_demo(self, demo_name: str, use_existing: bool = False) -> bool:
        """Run a specific demo"""
        print(f"\n🎬 Running demo: {demo_name}")
        
        # Map demo names to actual files
        demo_files = {
            'vector_clock_db': 'vector_clock_db_demo.py',
            'convergence': 'convergence_test.py',
            'anti_entropy': 'working_anti_entropy_demo.py',
            'automated_anti_entropy': 'automated_anti_entropy_demo.py',
            'consistent_hashing': 'consistent_hashing_demo.py',
            'replication': 'replication_demo.py',
            'quick': 'quick_demo.py',
            'persistence_anti_entropy': 'demo_persistence_anti_entropy.py'
        }
        
        if demo_name not in demo_files:
            print(f"❌ Unknown demo: {demo_name}")
            print(f"Available demos: {list(demo_files.keys())}")
            return False
        
        demo_file = demo_files[demo_name]
        demo_cwd = os.path.dirname(os.path.abspath(__file__))
        demo_path = os.path.join(demo_cwd, demo_file)
        
        if not os.path.exists(demo_path):
            print(f"❌ Demo file not found: {demo_path}")
            return False
        
        try:
            # Set environment variables for the demo
            env = dict(os.environ)
            env['CLUSTER_NODES'] = ','.join([node['address'] for node in self.nodes])
            env['CLUSTER_CONFIG'] = self.config_file
            
            # Debug: Print environment variables
            print(f"🔧 Setting CLUSTER_NODES: {env['CLUSTER_NODES']}")
            print(f"🔧 Setting CLUSTER_CONFIG: {env['CLUSTER_CONFIG']}")
            
            # Preserve REPLICATION_FACTOR if set in parent environment
            if 'REPLICATION_FACTOR' in os.environ:
                env['REPLICATION_FACTOR'] = os.environ['REPLICATION_FACTOR']
                print(f"📊 Using replication factor: {os.environ['REPLICATION_FACTOR']}")
            
            # Run the demo
            print(f"📁 Running {demo_file}...")
            print(f"🔧 About to run subprocess with CLUSTER_NODES: {env['CLUSTER_NODES']}")
            result = subprocess.run([sys.executable, demo_file], env=env, cwd=demo_cwd)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Error running demo: {e}")
            return False
    
    def run(self, demo_name: str, use_existing: bool = False) -> bool:
        """Main run method"""
        try:
            # Get or create cluster
            if use_existing:
                self.nodes = self.get_existing_nodes()
                if not self.nodes:
                    print("❌ No existing nodes found in config")
                    return False
                
                if not self.verify_existing_cluster(self.nodes):
                    print("❌ Existing cluster verification failed")
                    return False
            else:
                if not self.start_new_cluster():
                    print("❌ Failed to start new cluster")
                    return False
            
            # Run the demo
            success = self.run_demo(demo_name, use_existing)
            
            return success
            
        except KeyboardInterrupt:
            print("\n⚠️ Demo interrupted by user")
            return False
        except Exception as e:
            print(f"\n❌ Demo failed with error: {e}")
            return False
        finally:
            self.cleanup_created_nodes()

def main():
    parser = argparse.ArgumentParser(
        description="Unified Cluster Demo Runner for Distributed Key-Value Database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Run vector clock demo on existing local cluster
  python cluster_demo_runner.py vector_clock_db --config config-local.yaml --use-existing
  
  # Run convergence demo on existing Kubernetes cluster  
  python cluster_demo_runner.py convergence --config config.yaml --use-existing
  
  # Create new local cluster and run anti-entropy demo
  python cluster_demo_runner.py anti_entropy --config config-local.yaml
  
  # Quick demo on local cluster
  python cluster_demo_runner.py quick --config config-local.yaml
  
  # List all available demos
  python cluster_demo_runner.py --help
        """
    )
    
    parser.add_argument(
        "demo", 
        help="""Demo to run. Available demos:
  vector_clock_db      - Vector clock functionality with causal consistency
  convergence          - Multi-node convergence and conflict resolution  
  anti_entropy         - Anti-entropy synchronization between nodes
  automated_anti_entropy - Automated anti-entropy with data verification
  consistent_hashing   - Consistent hashing and data distribution
  replication          - Data replication and consistency
  quick                - Quick overview of all features
  persistence_anti_entropy - Persistence with anti-entropy"""
    )
    
    parser.add_argument(
        "--config", 
        default="config-local.yaml", 
        help="""Configuration file to use. Options:
  config-local.yaml    - Local development cluster (default)
  config.yaml          - Kubernetes cluster
  <custom>.yaml        - Custom configuration file"""
    )
    
    parser.add_argument(
        "--use-existing", 
        action="store_true", 
        help="""Use existing cluster instead of creating new one.
  When specified, the runner will connect to nodes specified in the config file.
  When not specified, the runner will create and manage new nodes."""
    )
    
    parser.add_argument(
        "--list-demos", 
        action="store_true", 
        help="List all available demos and exit"
    )
    
    parser.add_argument(
        "--professional", 
        action="store_true", 
        help="Use professional testing practices with temporary directories and cleanup"
    )
    
    args = parser.parse_args()
    
    # Handle list demos option
    if args.list_demos:
        print("AVAILABLE DEMOS:")
        demos = {
            'vector_clock_db': 'Vector clock functionality with causal consistency',
            'convergence': 'Multi-node convergence and conflict resolution',
            'anti_entropy': 'Anti-entropy synchronization between nodes',
            'automated_anti_entropy': 'Automated anti-entropy with data verification',
            'consistent_hashing': 'Consistent hashing and data distribution',
            'replication': 'Data replication and consistency',
            'quick': 'Quick overview of all features',
            'persistence_anti_entropy': 'Persistence with anti-entropy'
        }
        for demo, description in demos.items():
            print(f"  {demo:<20} - {description}")
        return
    
    # Validate demo name
    valid_demos = [
        'vector_clock_db', 'convergence', 'anti_entropy', 'automated_anti_entropy',
        'consistent_hashing', 'replication', 'quick', 'persistence_anti_entropy'
    ]
    
    if args.demo not in valid_demos:
        print(f"❌ Unknown demo: {args.demo}")
        print("Available demos:")
        for demo in valid_demos:
            print(f"  - {demo}")
        print("\nUse --list-demos for detailed descriptions")
        sys.exit(1)
    
    # Use professional testing practices if requested
    if args.professional:
        print("🚀 Using Professional Testing Practices")
        print("=" * 50)
        print("✅ Temporary directories for test isolation")
        print("✅ Automatic cleanup after demo completion")
        print("✅ Professional logging and error handling")
        print("✅ Test result tracking and metrics")
        print("=" * 50)
        
        # Use test environment for professional testing
        with TestEnvironment(f"demo_{args.demo}") as test_env:
            try:
                runner = ClusterDemoRunner(args.config, test_env)
                success = runner.run(args.demo, args.use_existing)
                
                # Print test results summary
                if runner.test_results:
                    print("\n📊 TEST RESULTS SUMMARY")
                    print("=" * 50)
                    for demo_name, result in runner.test_results.items():
                        status_icon = "✅" if result['status'] == 'PASSED' else "❌"
                        print(f"{status_icon} {demo_name}: {result['status']} ({result['duration']:.2f}s)")
                        if result['error']:
                            print(f"    Error: {result['error']}")
                
                if not success:
                    sys.exit(1)
                    
            except Exception as e:
                print(f"❌ Demo execution failed: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                sys.exit(1)
    else:
        # Use traditional approach (backward compatibility)
        print(f"🎬 Cluster Demo Runner")
        print(f"📁 Config: {args.config}")
        print(f"🔧 Mode: {'Existing cluster' if args.use_existing else 'New cluster'}")
        print(f"🎯 Demo: {args.demo}")
        print("=" * 60)
        
        try:
            runner = ClusterDemoRunner(args.config)
            success = runner.run(args.demo, args.use_existing)
            
            if success:
                print("\n✅ Demo completed successfully!")
            else:
                print("\n❌ Demo failed!")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Demo execution failed: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            sys.exit(1)

if __name__ == "__main__":
    main() 