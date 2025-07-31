#!/usr/bin/env python3
"""
Robust Hashing Gossip Node
Extends the robust wrapper with consistent hashing functionality
"""

import time
import requests
import json
from typing import List, Dict, Optional
from flask import jsonify, request
import logging
import threading
from flask import Flask
from werkzeug.serving import make_server
import socket

# Import the robust wrapper
from node import RobustSimpleGossipNode, RobustGossipState
from pysyncobj import SyncObj, SyncObjConf

# Use hashring for consistent hashing
try:
    from hashring import HashRing
except ImportError:
    print("Install hashring: pip install hashring")
    raise

from yaml_config import yaml_config

logger = logging.getLogger(__name__)

def find_free_port() -> int:
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

class RobustHashingGossipNode:
    """
    Robust gossip node with consistent hashing and its own Flask app/routes.
    Endpoints reuse logic from RobustSimpleGossipNode via composition.
    """
    def __init__(self, node_id: str, host: str, port: int, replication_factor: int = 3):
        # DEBUG: RobustHashingGossipNode
        # print(f"DEBUG RobustHashingGossipNode: Received port={port}, type={type(port)}")
        
        # Read gossip port from config instead of using passed port
        gossip_port = yaml_config.get_gossip_port_for_node(node_id)
        if gossip_port is None:
            # Fallback to passed port if config doesn't have gossip_port
            gossip_port = port
        print(f"DEBUG RobustHashingGossipNode: {node_id} using gossip_port = {gossip_port}")
        
        # Initialize parent with the gossip port
        self.simple_node = RobustSimpleGossipNode(node_id, host, gossip_port)
        
        # Copy attributes from parent
        self.node_id = node_id
        self.host = host
        self.port = gossip_port  # Use the gossip port
        self.address = f"{host}:{gossip_port}"
        self.replication_factor = replication_factor
        self.local_data = {}
        self.hash_ring = None
        
        # Flask app setup
        self.app = Flask(f"robust-hashing-{node_id}")
        self._add_hashing_routes()
        
        # Server management
        self.server_thread = None
        self.is_running = False
        logger.info(f"RobustHashingGossipNode {node_id} initialized")

    def _add_hashing_routes(self):
        @self.app.route('/kv/<key>', methods=['PUT'])
        def put_key(key):
            data = request.get_json()
            if not data or 'value' not in data:
                return jsonify({"error": "No value provided"}), 400
            
            value = str(data['value'])
            # Apply hashing logic first
            self._ensure_ring_exists()
            replicas = self._get_replicas_for_key(key)
            
            # Use parent logic for actual storage, but apply to replicas
            success_count = 0
            for replica in replicas:
                if self._write_to_node(replica, key, value):
                    success_count += 1
            
            required = max(1, (len(replicas) // 2) + 1)
            if success_count >= required:
                return jsonify({
                    "key": key,
                    "value": value,
                    "replicas": replicas,
                    "coordinator": self.address
                }), 200
            else:
                return jsonify({"error": "Write failed"}), 500

        @self.app.route('/kv/<key>', methods=['GET'])
        def get_key(key):
            # Apply hashing logic first
            self._ensure_ring_exists()
            replicas = self._get_replicas_for_key(key)
            
            # Read from all replicas and collect responses
            responses = {}
            for replica in replicas:
                value = self._read_from_node(replica, key)
                if value is not None:
                    responses[replica] = value
            
            # Check quorum (majority of replicas must respond)
            required = max(1, (len(replicas) // 2) + 1)
            if len(responses) >= required:
                # Verify consistency - all returned values should be the same
                unique_values = set(responses.values())
                if len(unique_values) == 1:
                    # All replicas returned the same value - consistent
                    value = list(unique_values)[0]
                    return jsonify({
                        "key": key,
                        "value": value,
                        "coordinator": self.address,
                        "replicas_responded": len(responses),
                        "total_replicas": len(replicas),
                        "quorum_required": required
                    }), 200
                else:
                    # Inconsistent values - data corruption or partial writes
                    logger.error(f"Inconsistent values for key {key}: {responses}")
                    return jsonify({
                        "error": "Data inconsistency detected",
                        "responses": responses
                    }), 500
            else:
                # Quorum not reached
                return jsonify({
                    "error": "Quorum not reached",
                    "responses_received": len(responses),
                    "quorum_required": required,
                    "total_replicas": len(replicas)
                }), 503

        @self.app.route('/kv/<key>/direct', methods=['PUT'])
        def put_direct(key):
            data = request.get_json()
            value = data.get('value')
            self.local_data[key] = value
            return jsonify({"key": key, "value": value}), 200

        @self.app.route('/kv/<key>/direct', methods=['GET'])
        def get_direct(key):
            value = self.local_data.get(key)
            if value is not None:
                return jsonify({"key": key, "value": value}), 200
            else:
                return jsonify({"error": "Key not found"}), 404

        @self.app.route('/join', methods=['POST'])
        def join_endpoint():
            """Join a cluster by connecting to an existing node"""
            try:
                data = request.get_json()
                peer_address = data.get('address')  # Use 'address' to match parent's API
                
                if not peer_address:
                    return jsonify({"error": "No address provided"}), 400
                
                # Use parent's join request handler
                result = self.simple_node.handle_join_request(peer_address, data.get('peers'))
                # Rebuild hash ring after join
                self._rebuild_hash_ring()
                
                return jsonify(result)
            except Exception as e:
                logger.error(f"Error in join endpoint: {str(e)}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/remove_peer', methods=['POST'])
        def remove_peer():
            data = request.get_json()
            peer_address = data.get('address')  # Use 'address' to match parent's API
            if not peer_address:
                return jsonify({"error": "No address provided"}), 400
            if peer_address == self.address:
                return jsonify({"error": "Cannot remove self"}), 400
            
            # Use parent's remove peer handler
            result = self.simple_node.handle_remove_peer_request(peer_address)
            # Rebuild hash ring after peer removal
            self._rebuild_hash_ring()
            
            return jsonify(result)

        @self.app.route('/peers', methods=['GET'])
        def get_peers_endpoint():
            """Get list of known peers - return same format as parent"""
            return jsonify(list(self.simple_node.get_peers()))

        @self.app.route('/info', methods=['GET'])
        def get_info():
            return jsonify(self.simple_node.get_node_info())

        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify(self.simple_node.get_health_info()), 200

        @self.app.route('/ring', methods=['GET'])
        def get_ring():
            self._ensure_ring_exists()
            nodes = list(self.hash_ring.nodes) if self.hash_ring else []
            logger.info(f"/ring endpoint returning nodes: {nodes}")
            return jsonify({
                "ring_size": len(nodes),
                "replication_factor": self.replication_factor,
                "nodes": nodes
            }), 200

    def _ensure_ring_exists(self):
        """Ensure hash ring exists and is up to date with current peers"""
        current_peers = list(self.simple_node.get_peers())
        # Include self in the ring - all nodes in cluster including self
        all_nodes = current_peers + [self.address]
        logger.info(f"Ensuring hash ring with all nodes: {all_nodes}")
        if (self.hash_ring is None or set(all_nodes) != set(self.hash_ring.nodes if self.hash_ring else [])):
            self.hash_ring = HashRing(all_nodes)
            logger.debug(f"Updated hash ring: {all_nodes}")

    def _get_replicas_for_key(self, key: str) -> List[str]:
        if not self.hash_ring or not self.hash_ring.nodes:
            return [self.address]
        all_nodes = list(self.hash_ring.nodes)
        if len(all_nodes) <= self.replication_factor:
            return all_nodes
        primary = self.hash_ring.get_node(key)
        primary_idx = all_nodes.index(primary)
        replicas = []
        for i in range(min(self.replication_factor, len(all_nodes))):
            idx = (primary_idx + i) % len(all_nodes)
            replicas.append(all_nodes[idx])
        return replicas

    def _write_to_node(self, node_address: str, key: str, value: str) -> bool:
        try:
            if node_address == self.address:
                self.local_data[key] = value
                return True
            else:
                response = requests.put(
                    f"http://{node_address}/kv/{key}/direct",
                    json={'value': value}, timeout=3
                )
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"Write to {node_address} failed: {e}")
            return False

    def _read_from_node(self, node_address: str, key: str) -> Optional[str]:
        try:
            if node_address == self.address:
                return self.local_data.get(key)
            else:
                response = requests.get(f"http://{node_address}/kv/{key}/direct", timeout=3)
                if response.status_code == 200:
                    return response.json()['value']
                return None
        except Exception as e:
            logger.debug(f"Read from {node_address} failed: {e}")
            return None

    def join(self, node_address):
        """Join a cluster by connecting to an existing node - reuse parent logic"""
        try:
            # Use parent's working join logic
            success = self.simple_node.join(node_address)
            if success:
                # Just rebuild hash ring after successful join
                self._rebuild_hash_ring()
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error joining cluster: {str(e)}")
            return False
    
    def get_peers(self):
        """Get list of known peers - use parent's state"""
        peers = self.simple_node.get_peers()
        print(f"DEBUG get_peers: {self.node_id} peers: {peers}")
        return peers
    
    def get_peer_count(self):
        """Get the number of peers - use parent's state"""
        return self.simple_node.get_peer_count()
    
    def get_address(self) -> str:
        return self.address

    def start(self):
        if self.is_running:
            return
        
        # Don't start parent's server - we handle all routes
        # Just start our own server
        self.is_running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.5)

    def _run_server(self):
        try:
            self.server = make_server(self.host, self.port, self.app)
            logger.info(f"RobustHashingGossipNode server started for {self.node_id} on {self.address}")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Server error for {self.node_id}: {e}")

    def stop(self):
        logger.info(f"Stopping RobustHashingGossipNode {self.node_id}")
        self.is_running = False
        
        # Stop our own server first
        if hasattr(self, 'server') and self.server:
            try:
                logger.info(f"Shutting down RobustHashingGossipNode server for {self.node_id}")
                self.server.shutdown()
                logger.info(f"RobustHashingGossipNode server shutdown for {self.node_id}")
            except Exception as e:
                logger.error(f"Error shutting down RobustHashingGossipNode server: {e}")
        
        # Wait for our server thread to finish
        if hasattr(self, 'server_thread') and self.server_thread:
            try:
                self.server_thread.join(timeout=3.0)
                logger.info(f"RobustHashingGossipNode server thread stopped for {self.node_id}")
            except Exception as e:
                logger.error(f"Error stopping RobustHashingGossipNode server thread: {e}")
        
        # Clear server references
        self.server = None
        self.server_thread = None
        
        # Use parent's stop logic
        self.simple_node.stop()
        
        logger.info(f"RobustHashingGossipNode {self.node_id} stopped")

    def handle_join_request(self, peer_address: str, peers: list = None) -> dict:
        # Call parent logic
        result = self.simple_node.handle_join_request(peer_address, peers)
        # Rebuild hash ring after peer change
        self._ensure_ring_exists()
        return result

    def handle_remove_peer_request(self, peer_address: str) -> dict:
        # Call parent logic
        result = self.simple_node.handle_remove_peer_request(peer_address)
        # Rebuild hash ring after peer change
        self._ensure_ring_exists()
        return result

    def _rebuild_hash_ring(self):
        """Rebuild the hash ring based on the current peers"""
        current_peers = list(self.simple_node.get_peers())
        # Include self in the ring - all nodes in cluster including self
        all_nodes = current_peers + [self.address]
        logger.info(f"Rebuilding hash ring with all nodes: {all_nodes}")
        if (self.hash_ring is None or set(all_nodes) != set(self.hash_ring.nodes if self.hash_ring else [])):
            self.hash_ring = HashRing(all_nodes)
            logger.info(f"Updated hash ring: {self.hash_ring.nodes}")

    def _get_peers_safe(self):
        """Get peers from parent's state"""
        return self.simple_node.get_peers()
    
    def _add_peer_safe(self, peer):
        """Add peer using parent's state"""
        self.simple_node.state.add_peer(peer)
    
    def _remove_peer_safe(self, peer):
        """Remove peer using parent's state"""
        self.simple_node.state.remove_peer(peer)


# ========================================
# TDD Test Suite for RobustHashingGossipNode
# ========================================

import unittest

class TestRobustConsistentHashingTDD(unittest.TestCase):
    """
    TDD Tests for Robust Consistent Hashing
    Each test drives implementation step by step
    """
    
    def setUp(self):
        """Set up test fixtures"""
        self.nodes = []
        self.max_wait = 3.0
        self.poll_interval = 0.05
    
    def tearDown(self):
        """Clean up test fixtures"""
        for node in self.nodes:
            try:
                node.stop()
            except:
                pass
        self.nodes = []
        time.sleep(0.5)  # Give time for cleanup
    
    def wait_for_peer_count(self, node, expected_count, timeout=None):
        """Wait for node.get_peer_count() == expected_count"""
        if timeout is None:
            timeout = self.max_wait
        waited = 0.0
        while waited < timeout:
            try:
                if node.get_peer_count() == expected_count:
                    return True
            except:
                pass
            time.sleep(self.poll_interval)
            waited += self.poll_interval
        return False
    
    # ========================================
    # TDD STEP 1: Basic Node Creation
    # ========================================
    
    def test_01_hashing_node_creation(self):
        """TDD Step 1: Create hashing node with basic properties"""
        port = find_free_port()
        node = RobustHashingGossipNode("test", "localhost", port)
        self.nodes.append(node)
        
        # Test basic properties exist
        self.assertEqual(node.node_id, "test")
        self.assertEqual(node.replication_factor, 3)
        self.assertIsNotNone(node.local_data)
        self.assertTrue(hasattr(node, 'hash_ring'))

    def test_02_basic_key_value_operations(self):
        """TDD Step 2: Basic key-value operations with consistent hashing"""
        # Create two nodes
        port1 = find_free_port()
        port2 = find_free_port()
        
        node1 = RobustHashingGossipNode("node1", "localhost", port1)
        node2 = RobustHashingGossipNode("node2", "localhost", port2)
        self.nodes.extend([node1, node2])
        
        # Start nodes
        node1.start()
        node2.start()
        time.sleep(0.5)  # Give servers time to start
        
        # Join nodes
        node2.join(node1.get_address())
        self.assertTrue(self.wait_for_peer_count(node1, 1))
        self.assertTrue(self.wait_for_peer_count(node2, 1))

        # Allow state to propagate
        time.sleep(0.5)
        
        # Test PUT operation
        key = "test_key"
        value = "test_value"
        
        response = requests.put(
            f"http://{node1.get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["key"], key)
        self.assertEqual(data["value"], value)
        self.assertIn("replicas", data)
        self.assertIn("coordinator", data)
        
        # Test GET operation
        response = requests.get(f"http://{node1.get_address()}/kv/{key}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["key"], key)
        self.assertEqual(data["value"], value)
        self.assertIn("coordinator", data)
        
        # Verify ring information
        response = requests.get(f"http://{node1.get_address()}/ring")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ring_size"], 2)
        self.assertEqual(data["replication_factor"], 3)
        self.assertEqual(len(data["nodes"]), 2)
        self.assertIn(node1.get_address(), data["nodes"])
        self.assertIn(node2.get_address(), data["nodes"])

    def test_03_replication_factor_and_distribution(self):
        """TDD Step 3: Replication factor and key distribution"""
        # Start 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)

        # Start all nodes
        for node in nodes:
            node.start()
        time.sleep(0.5)

        # Join nodes into a cluster
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key via node1
        key = "rf_test_key"
        value = "rf_value"
        response = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["key"], key)
        self.assertEqual(data["value"], value)
        self.assertEqual(len(data["replicas"]), 3)  # Replication factor default is 3
        for replica in data["replicas"]:
            # Check that the value is present on each replica
            r = requests.get(f"http://{replica}/kv/{key}/direct")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["value"], value)

        # Verify ring info
        ring_resp = requests.get(f"http://{nodes[0].get_address()}/ring")
        self.assertEqual(ring_resp.status_code, 200)
        ring_data = ring_resp.json()
        self.assertEqual(ring_data["ring_size"], 3)
        self.assertEqual(ring_data["replication_factor"], 3)
        self.assertEqual(len(ring_data["nodes"]), 3)
        for node in nodes:
            self.assertIn(node.get_address(), ring_data["nodes"])

    def test_04_ring_update_and_key_redistribution(self):
        """TDD Step 4: Ring update and key redistribution on node join"""
        # Start with 2 nodes
        port1 = find_free_port()
        port2 = find_free_port()
        node1 = RobustHashingGossipNode("node1", "localhost", port1)
        node2 = RobustHashingGossipNode("node2", "localhost", port2)
        self.nodes.extend([node1, node2])
        node1.start()
        node2.start()
        time.sleep(0.5)
        node2.join(node1.get_address())
        self.assertTrue(self.wait_for_peer_count(node1, 1))
        self.assertTrue(self.wait_for_peer_count(node2, 1))

        # Put a key via node1
        key = "redistribute_key"
        value = "before_join"
        put_resp = requests.put(
            f"http://{node1.get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.json()
        self.assertEqual(put_data["key"], key)
        self.assertEqual(put_data["value"], value)
        self.assertEqual(len(put_data["replicas"]), 2)

        # Add a 3rd node
        port3 = find_free_port()
        node3 = RobustHashingGossipNode("node3", "localhost", port3)
        self.nodes.append(node3)
        node3.start()
        time.sleep(0.5)
        node3.join(node1.get_address())
        self.assertTrue(self.wait_for_peer_count(node3, 2))

        # Verify ring is updated
        ring_resp = requests.get(f"http://{node1.get_address()}/ring")
        self.assertEqual(ring_resp.status_code, 200)
        ring_data = ring_resp.json()
        self.assertEqual(ring_data["ring_size"], 3)
        self.assertEqual(len(ring_data["nodes"]), 3)
        self.assertIn(node3.get_address(), ring_data["nodes"])

        # Verify key is still accessible
        get_resp = requests.get(f"http://{node1.get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)

        # Put should now use 3 replicas
        put_resp2 = requests.put(
            f"http://{node1.get_address()}/kv/{key}",
            json={"value": "after_join"}
        )
        self.assertEqual(put_resp2.status_code, 200)
        put_data2 = put_resp2.json()
        self.assertEqual(len(put_data2["replicas"]), 3)
        for replica in put_data2["replicas"]:
            r = requests.get(f"http://{replica}/kv/{key}/direct")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["value"], "after_join")

    def test_05_ring_update_and_key_redistribution_on_node_leave(self):
        """TDD Step 5: Ring update and key redistribution on node leave"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key via node1
        key = "leave_key"
        value = "before_leave"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.json()
        self.assertEqual(put_data["key"], key)
        self.assertEqual(put_data["value"], value)
        self.assertEqual(len(put_data["replicas"]), 3)

        # Remove node2
        nodes[1].stop()
        time.sleep(1.0)  # Give time for cluster to detect removal
        
        # Manually remove the stopped node from remaining nodes' peer lists
        stopped_node_address = nodes[1].get_address()
        for node in [nodes[0], nodes[2]]:
            remove_resp = requests.post(
                f"http://{node.get_address()}/remove_peer",
                json={"address": stopped_node_address}
            )
            self.assertEqual(remove_resp.status_code, 200)

        # Verify ring is updated
        ring_resp = requests.get(f"http://{nodes[0].get_address()}/ring")
        self.assertEqual(ring_resp.status_code, 200)
        ring_data = ring_resp.json()
        self.assertEqual(ring_data["ring_size"], 2)
        self.assertEqual(len(ring_data["nodes"]), 2)
        self.assertNotIn(nodes[1].get_address(), ring_data["nodes"])

        # Key should still be accessible
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)

        # Put should update replicas to remaining nodes
        put_resp2 = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": "after_leave"}
        )
        self.assertEqual(put_resp2.status_code, 200)
        put_data2 = put_resp2.json()
        self.assertEqual(len(put_data2["replicas"]), 2)
        for replica in put_data2["replicas"]:
            r = requests.get(f"http://{replica}/kv/{key}/direct")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["value"], "after_leave")

    def test_06_key_redistribution_on_node_failure(self):
        """TDD Step 6: Key redistribution when a node fails"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key via node1
        key = "failure_key"
        value = "before_failure"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.json()
        self.assertEqual(put_data["key"], key)
        self.assertEqual(put_data["value"], value)
        self.assertEqual(len(put_data["replicas"]), 3)

        # Simulate node2 failure by stopping it
        nodes[1].stop()
        time.sleep(1.0)  # Give time for cluster to detect failure
        
        # Manually remove the stopped node from remaining nodes' peer lists
        stopped_node_address = nodes[1].get_address()
        for node in [nodes[0], nodes[2]]:
            remove_resp = requests.post(
                f"http://{node.get_address()}/remove_peer",
                json={"address": stopped_node_address}
            )
            self.assertEqual(remove_resp.status_code, 200)

        # Verify ring is updated
        ring_resp = requests.get(f"http://{nodes[0].get_address()}/ring")
        self.assertEqual(ring_resp.status_code, 200)
        ring_data = ring_resp.json()
        self.assertEqual(ring_data["ring_size"], 2)
        self.assertEqual(len(ring_data["nodes"]), 2)
        self.assertNotIn(nodes[1].get_address(), ring_data["nodes"])

        # Key should still be accessible
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertIn("coordinator", get_data)

        # Put should update replicas to remaining nodes
        put_resp2 = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": "after_failure"}
        )
        self.assertEqual(put_resp2.status_code, 200)
        put_data2 = put_resp2.json()
        self.assertEqual(len(put_data2["replicas"]), 2)
        for replica in put_data2["replicas"]:
            r = requests.get(f"http://{replica}/kv/{key}/direct")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["value"], "after_failure")

    def test_07_ring_update_and_key_redistribution_on_node_join_with_data(self):
        """TDD Step 7: Ring update and key redistribution when a new node joins a cluster with data"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put some keys via node1
        test_keys = {
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        }
        for key, value in test_keys.items():
            put_resp = requests.put(
                f"http://{nodes[0].get_address()}/kv/{key}",
                json={"value": value}
            )
            self.assertEqual(put_resp.status_code, 200)
            put_data = put_resp.json()
            self.assertEqual(put_data["key"], key)
            self.assertEqual(put_data["value"], value)
            self.assertEqual(len(put_data["replicas"]), 3)

        # Add a 4th node
        port4 = find_free_port()
        node4 = RobustHashingGossipNode("node4", "localhost", port4)
        self.nodes.append(node4)
        node4.start()
        time.sleep(0.5)
        node4.join(nodes[0].get_address())
        self.assertTrue(self.wait_for_peer_count(node4, 3))

        # Verify ring is updated
        ring_resp = requests.get(f"http://{nodes[0].get_address()}/ring")
        self.assertEqual(ring_resp.status_code, 200)
        ring_data = ring_resp.json()
        self.assertEqual(ring_data["ring_size"], 4)
        self.assertEqual(len(ring_data["nodes"]), 4)
        self.assertIn(node4.get_address(), ring_data["nodes"])

        # Verify all keys are still accessible
        for key, value in test_keys.items():
            get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
            self.assertEqual(get_resp.status_code, 200)
            get_data = get_resp.json()
            self.assertEqual(get_data["key"], key)
            self.assertEqual(get_data["value"], value)
            self.assertIn("coordinator", get_data)

        # Verify new PUT operations use all 4 nodes
        new_key = "key4"
        new_value = "value4"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{new_key}",
            json={"value": new_value}
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.json()
        self.assertEqual(put_data["key"], new_key)
        self.assertEqual(put_data["value"], new_value)
        self.assertEqual(len(put_data["replicas"]), 3)  # Still maintain RF=3

        # Verify the new key is accessible from all nodes
        for node in nodes + [node4]:
            get_resp = requests.get(f"http://{node.get_address()}/kv/{new_key}")
            if get_resp.status_code == 200:
                get_data = get_resp.json()
                self.assertEqual(get_data["key"], new_key)
                self.assertEqual(get_data["value"], new_value)

    def test_08_quorum_based_reads_success(self):
        """TDD Step 8: Quorum-based reads succeed when majority of replicas respond consistently"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key that will be replicated to all 3 nodes
        key = "quorum_test_key"
        value = "quorum_test_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)
        put_data = put_resp.json()
        self.assertEqual(put_data["key"], key)
        self.assertEqual(put_data["value"], value)
        self.assertEqual(len(put_data["replicas"]), 3)

        # Read the key - should succeed with quorum
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertEqual(get_data["coordinator"], nodes[0].get_address())
        self.assertEqual(get_data["replicas_responded"], 3)
        self.assertEqual(get_data["total_replicas"], 3)
        self.assertEqual(get_data["quorum_required"], 2)

    def test_09_quorum_based_reads_partial_failure(self):
        """TDD Step 9: Quorum-based reads succeed when minority of replicas fail"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key
        key = "partial_failure_key"
        value = "partial_failure_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Stop one replica (node2) to simulate partial failure
        nodes[1].stop()
        time.sleep(1.0)

        # Read should still succeed (2 out of 3 replicas available)
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertEqual(get_data["replicas_responded"], 2)
        self.assertEqual(get_data["total_replicas"], 3)
        self.assertEqual(get_data["quorum_required"], 2)

    def test_10_quorum_based_reads_quorum_failure(self):
        """TDD Step 10: Quorum-based reads fail when majority of replicas are unavailable"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key
        key = "quorum_failure_key"
        value = "quorum_failure_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Stop two replicas (node1 and node2) to simulate quorum failure
        nodes[1].stop()
        nodes[2].stop()
        time.sleep(1.0)

        # Read should fail (only 1 out of 3 replicas available)
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 503)  # Service Unavailable
        get_data = get_resp.json()
        self.assertEqual(get_data["error"], "Quorum not reached")
        self.assertEqual(get_data["responses_received"], 1)
        self.assertEqual(get_data["quorum_required"], 2)
        self.assertEqual(get_data["total_replicas"], 3)

    def test_11_quorum_based_reads_data_inconsistency(self):
        """TDD Step 11: Quorum-based reads detect and report data inconsistency"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key
        key = "inconsistency_key"
        value = "original_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Manually corrupt one replica to simulate data inconsistency
        # Write different value directly to node2
        corrupt_resp = requests.put(
            f"http://{nodes[1].get_address()}/kv/{key}/direct",
            json={"value": "corrupted_value"}
        )
        self.assertEqual(corrupt_resp.status_code, 200)

        # Read should detect inconsistency and return 500
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 500)  # Internal Server Error
        get_data = get_resp.json()
        self.assertEqual(get_data["error"], "Data inconsistency detected")
        self.assertIn("responses", get_data)
        responses = get_data["responses"]
        self.assertEqual(len(responses), 3)  # All replicas responded
        # Should have both "original_value" and "corrupted_value"
        values = set(responses.values())
        self.assertIn("original_value", values)
        self.assertIn("corrupted_value", values)

    def test_12_quorum_based_reads_single_node(self):
        """TDD Step 12: Quorum-based reads work correctly with single node"""
        # Start with 1 node
        port = find_free_port()
        node = RobustHashingGossipNode("node1", "localhost", port)
        self.nodes.append(node)
        node.start()
        time.sleep(0.5)

        # Put a key
        key = "single_node_key"
        value = "single_node_value"
        put_resp = requests.put(
            f"http://{node.get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Read should succeed (quorum = 1 for single node)
        get_resp = requests.get(f"http://{node.get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertEqual(get_data["replicas_responded"], 1)
        self.assertEqual(get_data["total_replicas"], 1)
        self.assertEqual(get_data["quorum_required"], 1)

    def test_13_quorum_based_reads_two_nodes(self):
        """TDD Step 13: Quorum-based reads work correctly with two nodes"""
        # Start with 2 nodes
        ports = [find_free_port() for _ in range(2)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(2)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 1))

        # Put a key
        key = "two_node_key"
        value = "two_node_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Read should succeed (quorum = 2 for two nodes)
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertEqual(get_data["replicas_responded"], 2)
        self.assertEqual(get_data["total_replicas"], 2)
        self.assertEqual(get_data["quorum_required"], 2)

        # Stop one node - read should fail
        nodes[1].stop()
        time.sleep(1.0)

        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 503)  # Service Unavailable
        get_data = get_resp.json()
        self.assertEqual(get_data["error"], "Quorum not reached")
        self.assertEqual(get_data["responses_received"], 1)
        self.assertEqual(get_data["quorum_required"], 2)

    def test_14_quorum_based_reads_key_not_found(self):
        """TDD Step 14: Quorum-based reads handle key not found correctly"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Try to read a non-existent key
        key = "non_existent_key"
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 503)  # Service Unavailable
        get_data = get_resp.json()
        self.assertEqual(get_data["error"], "Quorum not reached")
        self.assertEqual(get_data["responses_received"], 0)
        self.assertEqual(get_data["quorum_required"], 2)
        self.assertEqual(get_data["total_replicas"], 3)

    def test_15_quorum_based_reads_ring_rebuild(self):
        """TDD Step 15: Quorum-based reads work correctly after ring rebuild"""
        # Start with 3 nodes
        ports = [find_free_port() for _ in range(3)]
        nodes = [RobustHashingGossipNode(f"node{i+1}", "localhost", ports[i]) for i in range(3)]
        self.nodes.extend(nodes)
        for node in nodes:
            node.start()
        time.sleep(0.5)
        nodes[1].join(nodes[0].get_address())
        nodes[2].join(nodes[0].get_address())
        for node in nodes:
            self.assertTrue(self.wait_for_peer_count(node, 2))

        # Put a key
        key = "ring_rebuild_key"
        value = "ring_rebuild_value"
        put_resp = requests.put(
            f"http://{nodes[0].get_address()}/kv/{key}",
            json={"value": value}
        )
        self.assertEqual(put_resp.status_code, 200)

        # Remove a peer to trigger ring rebuild
        remove_resp = requests.post(
            f"http://{nodes[0].get_address()}/remove_peer",
            json={"address": nodes[2].get_address()}
        )
        self.assertEqual(remove_resp.status_code, 200)

        # Read should still work with remaining replicas
        get_resp = requests.get(f"http://{nodes[0].get_address()}/kv/{key}")
        self.assertEqual(get_resp.status_code, 200)
        get_data = get_resp.json()
        self.assertEqual(get_data["key"], key)
        self.assertEqual(get_data["value"], value)
        self.assertEqual(get_data["replicas_responded"], 2)
        self.assertEqual(get_data["total_replicas"], 2)
        self.assertEqual(get_data["quorum_required"], 2)


def run_tests():
    """Run all tests"""
    print("🧪 Running TDD Step 3: Robust Consistent Hashing Tests with Quorum-based Reads")
    print("=" * 60)
    
    # Configure logging for tests
    # logging.basicConfig(level=logging.INFO)
    
    # Create test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRobustConsistentHashingTDD))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ All Robust Step 3 tests passed! Ready for Step 4.")
        print(f"📊 Ran {result.testsRun} tests successfully")
        print("\n🎉 Robust Step 3 Complete! You now have:")
        print("  ✅ Robust consistent hashing")
        print("  ✅ Key-value operations with quorum-based replication")
        print("  ✅ Ring updates on topology changes")
        print("  ✅ Proper Flask server shutdown")
        print("  ✅ Built on proven gossip foundation")
        print("  ✅ Quorum-based reads with consistency validation")
        print("  ✅ Data inconsistency detection and reporting")
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
        print("\n🚀 Robust Consistent Hashing Step 3 Complete!")
        print("Key benefits:")
        print("  🔧 Consistent hashing for key distribution")
        print("  🔧 Configurable replication factor")
        print("  🔧 Ring updates on topology changes")
        print("  🔧 Robust Flask server shutdown")
        print("  🔧 Quorum-based reads with consistency validation")
        print("  🔧 Data inconsistency detection and reporting")
        print("\nTo run manually:")
        print("1. pip install -r requirements.txt")
        print("2. python robust_hashing_gossip_node.py")
        print("\nReady for Step 4: Failure Detection")
    else:
        print("\n🔧 Fix failing tests before proceeding") 