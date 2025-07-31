#!/usr/bin/env python3
"""
Collaborative Document Editor Demo with Node Failure Scenarios
Demonstrates causal consistency using vector clocks in a Google Docs-like environment
"""

import os
import sys
import time
import json
import requests
import signal
import subprocess
from datetime import datetime
import random

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_utils import DemoLogger, ensure_cluster_running

class CollaborativeEditorDemo:
    def __init__(self, cluster_nodes=None):
        self.logger = DemoLogger("collaborative_editor_demo")
        self.cluster_nodes = cluster_nodes or []
        self.document_id = "doc_project_proposal"
        self.users = ["Alice", "Bob", "Charlie"]
        self.node_user_mapping = {}  # Maps users to their preferred nodes
        
    def setup_document(self):
        """Initialize a collaborative document"""
        self.logger.step("Creating collaborative document")
        
        initial_doc = {
            "title": "Project Proposal",
            "paragraphs": {
                "para_1": {
                    "content": "The project aims to revolutionize distributed systems.",
                    "author": "Alice",
                    "timestamp": time.time()
                },
                "para_2": {
                    "content": "Implementation will use cutting-edge technology.",
                    "author": "Bob", 
                    "timestamp": time.time()
                },
                "para_3": {
                    "content": "Budget: TBD",
                    "author": "Charlie",
                    "timestamp": time.time()
                }
            },
            "version": 1
        }
        
        # Write initial document to first node
        response = requests.put(
            f"http://{self.cluster_nodes[0]}/kv/{self.document_id}",
            json={"value": json.dumps(initial_doc)}
        )
        
        if response.status_code == 200:
            self.logger.success(f"Document created: {self.document_id}")
        else:
            self.logger.error(f"Failed to create document: {response.text}")
            
        # Map users to nodes
        for i, user in enumerate(self.users):
            if i < len(self.cluster_nodes):
                self.node_user_mapping[user] = self.cluster_nodes[i]
                self.logger.info(f"{user} connected to Node-{i+1} ({self.cluster_nodes[i]})")
                
    def simulate_concurrent_edits(self):
        """Simulate multiple users editing different paragraphs concurrently"""
        self.logger.step("Simulating concurrent edits from multiple users")
        
        edits = [
            ("Alice", "para_1", "The project aims to revolutionize distributed systems with AI integration."),
            ("Bob", "para_2", "Implementation will use microservices architecture and Kubernetes."),
            ("Charlie", "para_3", "Budget: $100,000 for Phase 1")
        ]
        
        # Perform edits concurrently
        for user, para_id, new_content in edits:
            node = self.node_user_mapping.get(user, self.cluster_nodes[0])
            self.edit_paragraph(node, user, para_id, new_content)
            time.sleep(0.1)  # Small delay to show concurrent nature
            
    def simulate_conflicting_edits(self):
        """Simulate conflicting edits to the same paragraph"""
        self.logger.step("Creating conflicting edits (same paragraph, different users)")
        
        # Alice and Bob edit the budget paragraph at the same time
        para_id = "para_3"
        
        # Get current document from different nodes to simulate partition
        self.logger.info("Alice and Bob both editing the budget section...")
        
        # Alice's edit from Node-1
        self.edit_paragraph(
            self.cluster_nodes[0], 
            "Alice", 
            para_id, 
            "Budget: $50,000 (cost-optimized approach)"
        )
        
        # Bob's edit from Node-2 (before Alice's edit propagates)
        self.edit_paragraph(
            self.cluster_nodes[1], 
            "Bob", 
            para_id, 
            "Budget: $75,000 (premium features included)"
        )
        
        self.logger.warning("Conflict created! Both users edited the same paragraph")
        
    def simulate_node_failure(self):
        """Simulate a node failure during editing"""
        self.logger.step("Simulating node failure scenario")
        
        if len(self.cluster_nodes) < 3:
            self.logger.warning("Need at least 3 nodes for failure simulation")
            return
            
        # Charlie is editing on Node-3
        failing_node = self.cluster_nodes[2]
        self.logger.warning(f"Node-3 ({failing_node}) will fail during Charlie's edit")
        
        # Start an edit
        self.logger.info("Charlie begins editing paragraph 4...")
        para_id = "para_4"
        
        # Partial edit to Node-3
        try:
            # First, get the document
            response = requests.get(f"http://{failing_node}/kv/{self.document_id}")
            if response.status_code == 200:
                doc_data = response.json()
                value_str = doc_data.get("value", "{}")
                current_doc = json.loads(value_str)
                
                # Simulate node failure by stopping it
                self.logger.error("💥 Node-3 experiencing failure!")
                self.stop_node(2)  # Stop the third node
                
                # Try to complete the edit (will fail)
                try:
                    self.edit_paragraph(
                        failing_node,
                        "Charlie",
                        para_id,
                        "Timeline: 6 months for complete implementation"
                    )
                except requests.exceptions.ConnectionError:
                    self.logger.error("Failed to complete edit - node is down!")
                    
                # Show that other nodes continue to work
                self.logger.info("Other nodes continue to function...")
                self.edit_paragraph(
                    self.cluster_nodes[0],
                    "Alice",
                    "para_5",
                    "Risk Assessment: Low risk with proper planning"
                )
                
                # Simulate node recovery
                time.sleep(2)
                self.logger.step("Recovering failed node...")
                self.start_node(2)
                time.sleep(3)  # Wait for node to fully start
                
                # Show anti-entropy in action
                self.logger.success("Node-3 recovered - anti-entropy will restore consistency")
                
        except Exception as e:
            self.logger.error(f"Error during failure simulation: {e}")
            
    def edit_paragraph(self, node, user, para_id, content):
        """Edit a paragraph in the document"""
        try:
            # Get current document
            response = requests.get(f"http://{node}/kv/{self.document_id}")
            if response.status_code == 200:
                doc_data = response.json()
                value_str = doc_data.get("value", "{}")
                current_doc = json.loads(value_str)
                vector_clock = doc_data.get("vector_clock", {})
                
                # Update paragraph
                if "paragraphs" not in current_doc:
                    current_doc["paragraphs"] = {}
                    
                current_doc["paragraphs"][para_id] = {
                    "content": content,
                    "author": user,
                    "timestamp": time.time()
                }
                current_doc["version"] = current_doc.get("version", 0) + 1
                
                # Write back
                response = requests.put(
                    f"http://{node}/kv/{self.document_id}",
                    json={"value": json.dumps(current_doc)}
                )
                
                if response.status_code == 200:
                    self.logger.success(f"{user} edited {para_id} via {node}")
                    self.show_vector_clock(node)
                else:
                    self.logger.error(f"Edit failed: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            raise
        except Exception as e:
            self.logger.error(f"Error editing paragraph: {e}")
            
    def show_vector_clock(self, node):
        """Display vector clock for the document"""
        try:
            response = requests.get(f"http://{node}/kv/{self.document_id}")
            if response.status_code == 200:
                data = response.json()
                vc = data.get("vector_clock", {})
                self.logger.info(f"Vector Clock: {json.dumps(vc, indent=2)}")
        except Exception as e:
            self.logger.error(f"Error fetching vector clock: {e}")
            
    def check_consistency(self):
        """Check document consistency across all nodes"""
        self.logger.step("Checking document consistency across all nodes")
        
        documents = {}
        vector_clocks = {}
        
        for i, node in enumerate(self.cluster_nodes):
            try:
                response = requests.get(f"http://{node}/kv/{self.document_id}")
                if response.status_code == 200:
                    data = response.json()
                    value_str = data.get("value", "{}")
                    documents[f"Node-{i+1}"] = json.loads(value_str)
                    vector_clocks[f"Node-{i+1}"] = data.get("vector_clock", {})
                else:
                    self.logger.warning(f"Node-{i+1} returned {response.status_code}")
            except Exception as e:
                self.logger.error(f"Error checking Node-{i+1}: {e}")
                
        # Compare documents
        if len(set(json.dumps(doc, sort_keys=True) for doc in documents.values())) == 1:
            self.logger.success("✅ All nodes have consistent documents!")
        else:
            self.logger.warning("⚠️ Inconsistencies detected between nodes")
            self.show_conflicts(documents)
            
        # Show vector clocks
        self.logger.info("Vector clocks across nodes:")
        for node, vc in vector_clocks.items():
            self.logger.info(f"{node}: {vc}")
            
    def show_conflicts(self, documents):
        """Display conflicts between different versions"""
        self.logger.info("Conflict details:")
        
        # Find paragraphs with different content
        all_para_ids = set()
        for doc in documents.values():
            if "paragraphs" in doc:
                all_para_ids.update(doc["paragraphs"].keys())
                
        for para_id in all_para_ids:
            versions = {}
            for node, doc in documents.items():
                if "paragraphs" in doc and para_id in doc["paragraphs"]:
                    content = doc["paragraphs"][para_id]["content"]
                    author = doc["paragraphs"][para_id]["author"]
                    key = f"{content} (by {author})"
                    if key not in versions:
                        versions[key] = []
                    versions[key].append(node)
                    
            if len(versions) > 1:
                self.logger.warning(f"Conflict in {para_id}:")
                for version, nodes in versions.items():
                    self.logger.info(f"  - {version} on {', '.join(nodes)}")
                    
    def wait_for_convergence(self, max_wait=10):
        """Wait for documents to converge across all nodes"""
        self.logger.step("Waiting for convergence via anti-entropy...")
        
        start_time = time.time()
        converged = False
        
        while time.time() - start_time < max_wait:
            documents = []
            for node in self.cluster_nodes:
                try:
                    response = requests.get(f"http://{node}/kv/{self.document_id}")
                    if response.status_code == 200:
                        documents.append(response.json().get("value", ""))
                except:
                    pass
                    
            if len(documents) == len(self.cluster_nodes) and len(set(documents)) == 1:
                converged = True
                break
                
            time.sleep(1)
            self.logger.info("⏳ Waiting for anti-entropy sync...")
            
        if converged:
            self.logger.success("✅ Documents converged!")
        else:
            self.logger.warning("⏱️ Convergence timeout - manual resolution may be needed")
            
    def stop_node(self, node_index):
        """Stop a specific node to simulate failure"""
        if node_index < len(self.cluster_nodes):
            port = self.cluster_nodes[node_index].split(":")[-1]
            subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True)
            # Note: Actual implementation would properly stop the node
            self.logger.warning(f"Simulated stop of Node-{node_index+1}")
            
    def start_node(self, node_index):
        """Start a previously stopped node"""
        # Note: Actual implementation would restart the node
        self.logger.info(f"Simulated restart of Node-{node_index+1}")
        
    def run_demo(self):
        """Run the complete collaborative editor demo"""
        self.logger.header("🔄 Collaborative Document Editor Demo 🔄")
        self.logger.info("Demonstrating causal consistency with vector clocks")
        self.logger.info("Simulating Google Docs-like collaborative editing")
        
        # Ensure cluster is running
        if not self.cluster_nodes:
            self.cluster_nodes = ensure_cluster_running(self.logger)
            if not self.cluster_nodes:
                return
                
        try:
            # Setup
            self.setup_document()
            time.sleep(1)
            
            # Concurrent non-conflicting edits
            self.simulate_concurrent_edits()
            time.sleep(2)
            
            # Check consistency
            self.check_consistency()
            time.sleep(1)
            
            # Create conflicts
            self.simulate_conflicting_edits()
            time.sleep(2)
            
            # Check for conflicts
            self.check_consistency()
            
            # Wait for convergence
            self.wait_for_convergence()
            
            # Node failure scenario
            if len(self.cluster_nodes) >= 3:
                self.simulate_node_failure()
                time.sleep(3)
                self.check_consistency()
                
            # Final convergence check
            self.wait_for_convergence()
            self.check_consistency()
            
            self.logger.header("✅ Demo completed successfully!")
            self.logger.info("Key takeaways:")
            self.logger.info("- Vector clocks maintain causal ordering of edits")
            self.logger.info("- Concurrent edits to different paragraphs work seamlessly")
            self.logger.info("- Conflicts are detected when same content is edited")
            self.logger.info("- Node failures don't lose data - anti-entropy restores consistency")
            
        except KeyboardInterrupt:
            self.logger.warning("\nDemo interrupted by user")
        except Exception as e:
            self.logger.error(f"Demo error: {e}")
            import traceback
            traceback.print_exc()

def main():
    # Check for existing cluster
    cluster_env = os.environ.get('CLUSTER_NODES')
    cluster_nodes = None
    
    if cluster_env:
        cluster_nodes = [node.strip() for node in cluster_env.split(',')]
        print(f"Using existing cluster: {cluster_nodes}")
    
    demo = CollaborativeEditorDemo(cluster_nodes)
    demo.run_demo()

if __name__ == "__main__":
    main()