#!/usr/bin/env python3
"""
TDD Step 2: Simple Synchronous Gossip Node using PySyncObj
Using PySyncObj for distributed consensus and state replication

Simple approach:
- Using PySyncObj for peer discovery and state replication
- Simple HTTP server using Flask for external communication
- Automatic peer list management through PySyncObj
- Predictable, easy to test

Prerequisites:
pip install -r requirements.txt

Run tests:
python gossip_tdd_step2_pygossip.py
"""

import unittest
import time
import socket
import json
import threading
from typing import Set, List
from flask import Flask, jsonify, request
import logging
import requests
from pysyncobj import SyncObj, SyncObjConf, SyncObjConsumer, replicated
import random

# Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Disable Flask's request logging to reduce noise
# logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Import centralized logging
from logging_utils import setup_logging, get_logger

# Setup centralized logging
logger = get_logger(__name__)


class GossipState(SyncObjConsumer):
    """State object that will be replicated across nodes using PySyncObj"""
    
    def __init__(self):
        super(GossipState, self).__init__()
        self._peers = set()
        self._node_id = None
    
    @replicated
    def add_peer(self, peer_address: str) -> List[str]:
        """Add a peer to the replicated state"""
        self._peers.add(peer_address)
        return list(self._peers)
    
    @replicated
    def remove_peer(self, peer_address: str) -> List[str]:
        """Remove a peer from the replicated state"""
        self._peers.discard(peer_address)
        return list(self._peers)
    
    @replicated
    def set_node_id(self, node_id: str) -> str:
        """Set the node ID in the replicated state"""
        self._node_id = node_id
        return self._node_id
    
    def get_peers(self) -> Set[str]:
        """Get the current set of peers"""
        return self._peers.copy()
    
    def get_node_id(self) -> str:
        """Get the node ID"""
        return self._node_id


class SimpleGossipNode:
    """
    Simple synchronous gossip node using PySyncObj for distributed state.
    Uses PySyncObj for peer discovery and state replication.
    """
    
    def __init__(self, node_id: str, host: str, port: int):
        """Initialize a new gossip node.
        
        Args:
            node_id (str): Unique identifier for this node
            host (str): Host address to bind to
            port (int): Port to bind to
        """
        if not isinstance(host, str):
            raise ValueError("Host must be a string")
        if not isinstance(port, int):
            raise ValueError("Port must be an integer")
            
        self.node_id = node_id
        self.host = host
        self.port = port
        self.address = f"{host}:{port}"
        
        # Initialize state object
        self.state = GossipState()
        
        # Initialize PySyncObj with our state
        conf = SyncObjConf(
            fullDumpFile=None,  # Disable full dump file
            journalFile=None,   # Disable journal file
            commandsWaitLeader=True,  # Wait for leader before executing commands
            onReady=self._on_sync_ready,  # Callback when sync is ready
            dynamicMembershipChange=True  # Enable dynamic membership change
        )
        
        self.sync_obj = SyncObj(
            self.address,
            [],  # Other nodes will be added here
            consumers=[self.state],
            conf=conf
        )
        
        # Wait for SyncObj to be ready
        self.sync_obj.waitReady()
        
        # Now we can safely set the node ID and add self to peers
        self.state.set_node_id(node_id)
        self.state.add_peer(self.address)
        
        # Initialize Flask app
        self.app = Flask(f"gossip-{node_id}")
        self._setup_routes()
        
        # Flask app for HTTP endpoints
        self.server = None
        self.thread = None
        self.is_running = False
        
    def _on_sync_ready(self):
        """Callback when PySyncObj is ready and synchronized"""
        logger.info(f"Node {self.node_id} is ready and synchronized")
        
    def _setup_routes(self):
        """Set up routes for the Flask app."""
        @self.app.route('/peers', methods=['GET'])
        def get_peers():
            """Return list of known peers (just the list, for test compatibility)"""
            return jsonify(list(self.state.get_peers()))
        
        @self.app.route('/join', methods=['POST'])
        def join():
            """Handle join request from another node."""
            try:
                data = request.get_json()
                peer_address = data.get('address')
                if not peer_address:
                    return jsonify({"error": "No address provided"}), 400
                
                # Add the peer to our state
                self.state.add_peer(peer_address)
                # Also add ourselves to the peer's state (so both know about each other)
                self.state.add_peer(self.address)
                # Optionally, merge peer lists from the response
                new_peers = set()
                if 'peers' in data:
                    for peer in data['peers']:
                        if peer != self.address and peer not in self.state.get_peers():
                            new_peers.add(peer)
                        self.state.add_peer(peer)
                # Recursively join any newly discovered peers (except self and already known)
                for peer in new_peers:
                    self.join(peer)
                return jsonify({"peers": list(self.state.get_peers())})
            except Exception as e:
                logger.error(f"Error in join: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/remove_peer', methods=['POST'])
        def remove_peer():
            """Handle peer removal request."""
            try:
                data = request.get_json()
                peer_address = data.get('address')
                if not peer_address:
                    return jsonify({"error": "No address provided"}), 400
                if peer_address == self.address:
                    return jsonify({"error": "Cannot remove self"}), 400
                self.state.remove_peer(peer_address)
                return jsonify({"peers": list(self.state.get_peers())})
            except Exception as e:
                logger.error(f"Error in remove_peer: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/info', methods=['GET'])
        def get_info():
            """Return node information"""
            return jsonify({
                'node_id': self.state.get_node_id(),
                'address': self.address,
                'is_running': self.is_running,
                'peer_count': len(self.state.get_peers())
            })
        
    def start(self):
        """Start the node's HTTP server and PySyncObj node."""
        if self.is_running:
            return
            
        # Start Flask server in background thread
        self.is_running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        time.sleep(0.5)  # Give server time to start
        
    def _run_server(self):
        """Run Flask server in background thread."""
        self.server = self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        
    def join(self, peer_address):
        """Join another node by sending a join request."""
        try:
            response = requests.post(f"http://{peer_address}/join", json={"address": self.address})
            if response.status_code == 200:
                data = response.json()
                # Add the peer to our state
                self.state.add_peer(peer_address)
                # Also add ourselves to the peer's state (so both know about each other)
                self.state.add_peer(self.address)
                # Optionally, merge peer lists from the response
                new_peers = set()
                if 'peers' in data:
                    for peer in data['peers']:
                        if peer != self.address and peer not in self.state.get_peers():
                            new_peers.add(peer)
                        self.state.add_peer(peer)
                # Recursively join any newly discovered peers (except self and already known)
                for peer in new_peers:
                    self.join(peer)
                return True
            else:
                logger.error(f"Error joining {peer_address}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error joining {peer_address}: {e}")
            return False
        
    def discover_peers(self):
        """Discover new peers by querying all known peers' /peers endpoints."""
        new_peers = 0
        current_peers = list(self.state.get_peers())
        
        for peer in current_peers:
            if peer == self.address:
                continue
                
            try:
                url = f"http://{peer}/peers"
                response = requests.get(url, timeout=3)
                
                if response.status_code == 200:
                    data = response.json()
                    peer_list = data.get('peers', [])
                    
                    # Add any new peers we didn't know about
                    for discovered_peer in peer_list:
                        if discovered_peer not in self.state.get_peers():
                            self.state.add_peer(discovered_peer)
                            new_peers += 1
                            logger.debug(f"Discovered new peer: {discovered_peer}")
                            
            except Exception as e:
                logger.debug(f"Could not reach peer {peer}: {e}")
        
        if new_peers > 0:
            logger.info(f"Discovered {new_peers} new peers")
        
        return new_peers
        
    def get_peer_count(self):
        """Get the number of peers.
        
        Returns:
            int: Number of peers
        """
        return len(self.state.get_peers())
        
    def stop(self):
        """Stop the node's HTTP server and PySyncObj node."""
        self.is_running = False
        if self.server:
            self.server.shutdown()
            self.server = None
        # Remove self from all other nodes' states
        for peer in self.state.get_peers():
            if peer != self.address:
                try:
                    requests.post(f"http://{peer}/remove_peer", json={"address": self.address})
                except Exception as e:
                    logger.debug(f"Error removing self from {peer}: {e}")
        self.sync_obj.destroy()

    def getNodes(self) -> Set[str]:
        """Get all known nodes (including self)"""
        return self.state.get_peers().copy()


def find_free_port() -> int:
    """Find a free port for testing using random selection to avoid OS exhaustion"""
    start_port = 50000
    end_port = 65535
    for _ in range(50):  # Try up to 50 random attempts
        port = random.randint(start_port, end_port)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(0.05)
                s.bind(('localhost', port))
                return port
        except (OSError, socket.error):
            continue
    raise RuntimeError('No free ports available in the range 50000-65535')


class TestSimpleGossip(unittest.TestCase):
    """Simple synchronous tests for gossip functionality"""
    
    def setUp(self):
        """Set up test fixtures."""
        self.nodes = []
        self.max_wait = 3.0  # seconds to wait for state propagation
        self.poll_interval = 0.05
        
    def tearDown(self):
        """Clean up test fixtures."""
        for node in self.nodes:
            node.stop()
        self.nodes = []
    
    def wait_for_peer_count(self, node, expected_count, timeout=None):
        """Wait for node.get_peer_count() == expected_count, or timeout."""
        if timeout is None:
            timeout = self.max_wait
        waited = 0.0
        while waited < timeout:
            if node.get_peer_count() == expected_count:
                return True
            time.sleep(self.poll_interval)
            waited += self.poll_interval
        return False
    
    def test_node_creation(self):
        """Test that a node can be created with valid parameters."""
        port = find_free_port()
        node = SimpleGossipNode(node_id='test', host='localhost', port=port)
        self.nodes.append(node)
        self.assertEqual(node.host, 'localhost')
        self.assertEqual(node.port, port)
        # Wait for self to appear in peer set
        self.assertTrue(self.wait_for_peer_count(node, 1), f"Peer count is {node.get_peer_count()}, expected 1")
    
    def test_invalid_node_creation(self):
        """Test that invalid parameters raise errors."""
        with self.assertRaises(ValueError):
            SimpleGossipNode(node_id='test', host=123, port=9000)
        with self.assertRaises(ValueError):
            SimpleGossipNode(node_id='test', host='localhost', port='notaport')
    
    def test_single_node_startup(self):
        """Test that a single node can start successfully."""
        port = find_free_port()
        node = SimpleGossipNode(node_id='test', host='localhost', port=port)
        self.nodes.append(node)
        node.start()
        self.assertTrue(self.wait_for_peer_count(node, 1), f"Peer count is {node.get_peer_count()}, expected 1")
    
    def test_http_endpoints(self):
        """Test that HTTP endpoints work correctly."""
        port = find_free_port()
        node = SimpleGossipNode(node_id='test', host='localhost', port=port)
        self.nodes.append(node)
        node.start()
        self.assertTrue(self.wait_for_peer_count(node, 1), f"Peer count is {node.get_peer_count()}, expected 1")
        # Test /peers endpoint returns just the list
        response = requests.get(f"http://{node.host}:{node.port}/peers")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [f"{node.host}:{node.port}"])
    
    def test_two_nodes_join(self):
        """Test that two nodes can join each other."""
        port1 = find_free_port()
        port2 = find_free_port()
        node1 = SimpleGossipNode(node_id='test1', host='localhost', port=port1)
        node2 = SimpleGossipNode(node_id='test2', host='localhost', port=port2)
        self.nodes.extend([node1, node2])
        node1.start()
        node2.start()
        self.assertTrue(self.wait_for_peer_count(node1, 1))
        self.assertTrue(self.wait_for_peer_count(node2, 1))
        success = node2.join(node1.address)
        self.assertTrue(success)
        # Wait for both to see each other
        self.assertTrue(self.wait_for_peer_count(node1, 2), f"node1 peers: {node1.getNodes()}")
        self.assertTrue(self.wait_for_peer_count(node2, 2), f"node2 peers: {node2.getNodes()}")
    
    def test_node_with_seed_peers(self):
        """Test that a node can join another node manually (no seed_peers support)."""
        port1 = find_free_port()
        port2 = find_free_port()
        node1 = SimpleGossipNode(node_id='test1', host='localhost', port=port1)
        node2 = SimpleGossipNode(node_id='test2', host='localhost', port=port2)
        self.nodes.extend([node1, node2])
        node1.start()
        node2.start()
        self.assertTrue(self.wait_for_peer_count(node1, 1))
        self.assertTrue(self.wait_for_peer_count(node2, 1))
        success = node2.join(node1.address)
        self.assertTrue(success)
        self.assertTrue(self.wait_for_peer_count(node2, 2), f"node2 peers: {node2.getNodes()}")
        self.assertTrue(self.wait_for_peer_count(node1, 2), f"node1 peers: {node1.getNodes()}")
    
    def test_three_nodes_chain(self):
        """Test that three nodes can form a chain and discover each other."""
        ports = [find_free_port() for _ in range(3)]
        nodes = [SimpleGossipNode(node_id=f'test{i+1}', host='localhost', port=ports[i]) for i in range(3)]
        for node in nodes:
            self.nodes.append(node)
            node.start()
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 1))
        # Chain join
        nodes[1].join(nodes[0].address)
        nodes[2].join(nodes[1].address)
        # Wait for full mesh
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 3), f"node peers: {node.getNodes()}")
    
    def test_join_nonexistent_peer(self):
        """Test that joining a nonexistent peer fails gracefully."""
        port = find_free_port()
        node = SimpleGossipNode(node_id='test', host='localhost', port=port)
        self.nodes.append(node)
        node.start()
        self.assertTrue(self.wait_for_peer_count(node, 1))
        success = node.join('nonexistent:1234')
        self.assertFalse(success)
        self.assertTrue(self.wait_for_peer_count(node, 1))

    def test_new_node_awareness(self):
        """Test that all nodes become aware of a new node when it joins"""
        # Start with 3 nodes
        port1 = find_free_port()
        port2 = find_free_port()
        port3 = find_free_port()
        
        node1 = SimpleGossipNode("node1", "127.0.0.1", port1)
        node2 = SimpleGossipNode("node2", "127.0.0.1", port2)
        node3 = SimpleGossipNode("node3", "127.0.0.1", port3)
        self.nodes.extend([node1, node2, node3])
        
        # Start all nodes
        node1.start()
        node2.start()
        node3.start()
        time.sleep(0.5)  # Give servers time to start
        
        # Join them in a chain: node1 <- node2 <- node3
        node2.join(node1.address)
        node3.join(node2.address)
        time.sleep(1)  # Give time for cluster formation
        
        # Verify initial cluster formation
        self.assertEqual(len(node1.state.get_peers()), 3)
        self.assertEqual(len(node2.state.get_peers()), 3)
        self.assertEqual(len(node3.state.get_peers()), 3)
        
        # Add a new node
        port4 = find_free_port()
        node4 = SimpleGossipNode("node4", "127.0.0.1", port4)
        self.nodes.append(node4)
        node4.start()
        time.sleep(0.5)
        
        # Join the new node to node1
        node4.join(node1.address)
        time.sleep(1)  # Give time for state replication
        
        # Verify all nodes know about node4
        logger.info(f"Node1 peers: {node1.state.get_peers()}")
        logger.info(f"Node2 peers: {node2.state.get_peers()}")
        logger.info(f"Node3 peers: {node3.state.get_peers()}")
        logger.info(f"Node4 peers: {node4.state.get_peers()}")
        
        self.assertIn(node4.address, node1.state.get_peers())
        self.assertIn(node4.address, node2.state.get_peers())
        self.assertIn(node4.address, node3.state.get_peers())
        self.assertEqual(len(node1.state.get_peers()), 4)
        self.assertEqual(len(node2.state.get_peers()), 4)
        self.assertEqual(len(node3.state.get_peers()), 4)
        self.assertEqual(len(node4.state.get_peers()), 4)
        
        # Clean up
        node1.stop()
        node2.stop()
        node3.stop()
        node4.stop()

    def test_node_removal_awareness(self):
        """Test that all nodes become aware when a node is removed from the system"""
        # Start with 4 nodes
        port1 = find_free_port()
        port2 = find_free_port()
        port3 = find_free_port()
        port4 = find_free_port()
        
        node1 = SimpleGossipNode("node1", "127.0.0.1", port1)
        node2 = SimpleGossipNode("node2", "127.0.0.1", port2)
        node3 = SimpleGossipNode("node3", "127.0.0.1", port3)
        node4 = SimpleGossipNode("node4", "127.0.0.1", port4)
        self.nodes.extend([node1, node2, node3, node4])
        
        # Start all nodes
        node1.start()
        node2.start()
        node3.start()
        node4.start()
        time.sleep(0.5)  # Give servers time to start
        
        # Join them in a chain: node1 <- node2 <- node3 <- node4
        node2.join(node1.address)
        node3.join(node2.address)
        node4.join(node3.address)
        time.sleep(1)  # Give time for cluster formation
        
        # Verify initial cluster formation
        self.assertEqual(len(node1.state.get_peers()), 4)
        self.assertEqual(len(node2.state.get_peers()), 4)
        self.assertEqual(len(node3.state.get_peers()), 4)
        self.assertEqual(len(node4.state.get_peers()), 4)
        
        # Remove node4
        node4.stop()
        time.sleep(1)  # Give time for state replication
        
        # Verify all remaining nodes know about node4's removal
        logger.info(f"Node1 peers after removal: {node1.state.get_peers()}")
        logger.info(f"Node2 peers after removal: {node2.state.get_peers()}")
        logger.info(f"Node3 peers after removal: {node3.state.get_peers()}")
        
        self.assertNotIn(node4.address, node1.state.get_peers())
        self.assertNotIn(node4.address, node2.state.get_peers())
        self.assertNotIn(node4.address, node3.state.get_peers())
        self.assertEqual(len(node1.state.get_peers()), 3)
        self.assertEqual(len(node2.state.get_peers()), 3)
        self.assertEqual(len(node3.state.get_peers()), 3)
        
        # Clean up remaining nodes
        node1.stop()
        node2.stop()
        node3.stop()


def run_tests():
    """Run all tests"""
    print(" Running TDD Step 2: Simple Synchronous Gossip Tests (PySyncObj)")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSimpleGossip))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All Step 2 tests passed! Ready for Step 3.")
        print(f"📊 Ran {result.testsRun} tests successfully")
        print("\n🎉 Step 2 Complete! You now have:")
        print("  ✅ Simple synchronous HTTP-based gossip")
        print("  ✅ Basic peer discovery and joining")
        print("  ✅ Predictable, testable code")
        print("  ✅ No complex async/await")
    else:
        print("❌ Some tests failed!")
        print(f"📊 Ran {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
        
        if result.failures:
            print("\nFailures:")
            for test, trace in result.failures:
                print(f"- {test}: {trace}")
        
        if result.errors:
            print("\nErrors:")
            for test, trace in result.errors:
                print(f"- {test}: {trace}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    
    if success:
        print("\n🚀 Simple Synchronous Step 2 Complete!")
        print("Key benefits:")
        print("  🔧 No async/await - predictable behavior")
        print("  🔧 Simple Flask HTTP server")
        print("  🔧 Basic requests for HTTP client")
        print("  🔧 Easy to understand and debug")
        print("\nTo run manually:")
        print("1. pip install -r requirements.txt")
        print("2. python gossip_tdd_step2_pygossip.py")
        print("\nReady for Step 3: Simple Failure Detection")
    else:
        print("\n🔧 Fix failing tests before proceeding") 