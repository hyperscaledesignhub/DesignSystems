#!/usr/bin/env python3
"""
Collaborative Editor Demo for Distributed Database
Real-time document editing with causal consistency
Automatically simulates multiple users editing simultaneously
"""
import os
import sys
import json
import time
import threading
import requests
import random
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from demo.demo_utils import DemoLogger, check_cluster_status

app = Flask(__name__)
app.config['SECRET_KEY'] = 'collab-editor-demo-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global configuration
CLUSTER_NODES = []
ACTIVE_DOCUMENTS = []
DEMO_DOCUMENT_ID = None  # Main demo document

# Two automatic users editing simultaneously
USER_ALICE = {
    "name": "Alice",
    "color": "#FF6B6B",
    "avatar": "👩‍💻",
    "typing_speed": 0.1,  # seconds between characters
    "paragraphs": ["intro", "section1", "section3"]
}

USER_BOB = {
    "name": "Bob", 
    "color": "#4ECDC4",
    "avatar": "👨‍💻",
    "typing_speed": 0.12,
    "paragraphs": ["intro", "section2", "section4"]
}

def get_cluster_nodes():
    """Get cluster nodes from environment or default"""
    global CLUSTER_NODES
    if not CLUSTER_NODES:
        cluster_env = os.environ.get('CLUSTER_NODES')
        if cluster_env:
            CLUSTER_NODES = [node.strip() for node in cluster_env.split(',')]
        else:
            CLUSTER_NODES = ["localhost:9999", "localhost:10000", "localhost:10001"]
    return CLUSTER_NODES

@app.route('/')
def collab_editor_demo():
    """Collaborative editor demo UI"""
    return render_template('collab_editor_demo_auto.html', 
                         demo_document_id=DEMO_DOCUMENT_ID,
                         user_alice=USER_ALICE,
                         user_bob=USER_BOB)

@app.route('/api/demo_document')
def get_demo_document():
    """Get the main demo document with consistency info"""
    if not DEMO_DOCUMENT_ID:
        return jsonify({"success": False, "error": "Demo document not initialized"})
    
    nodes = get_cluster_nodes()
    documents = {}
    vector_clocks = {}
    
    # Get document from all nodes to show consistency
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/causal/kv/{DEMO_DOCUMENT_ID}", timeout=3)
            if response.status_code == 200:
                response_data = response.json()
                
                if "error" not in response_data:
                    value_str = response_data.get("value", "{}")
                    doc_data = json.loads(value_str)
                    documents[f"node-{i+1}"] = {
                        "address": node,
                        "status": "healthy",
                        "document": doc_data,
                        "vector_clock": response_data.get("vector_clock", {}),
                        "causal_operation": response_data.get("causal_operation", False)
                    }
                    vector_clocks[f"node-{i+1}"] = response_data.get("vector_clock", {})
        except Exception as e:
            documents[f"node-{i+1}"] = {
                "address": node,
                "status": "error",
                "error": str(e)
            }
    
    # Check consistency across nodes
    consistency_status = check_document_consistency(documents)
    
    return jsonify({
        "success": True,
        "document_id": DEMO_DOCUMENT_ID,
        "nodes": documents,
        "consistency": consistency_status,
        "vector_clocks": vector_clocks
    })

def check_document_consistency(documents):
    """Check if document is consistent across all nodes"""
    versions = []
    contents = []
    
    for node_id, node_data in documents.items():
        if node_data["status"] == "healthy" and "document" in node_data:
            doc = node_data["document"]
            versions.append(doc.get("version", 0))
            # Create a content hash for comparison
            paragraphs = doc.get("paragraphs", {})
            content_str = json.dumps(paragraphs, sort_keys=True)
            contents.append(content_str)
    
    is_consistent = len(set(contents)) <= 1  # All nodes have same content
    version_consistent = len(set(versions)) <= 1  # All nodes have same version
    
    return {
        "is_consistent": is_consistent and version_consistent,
        "versions": versions,
        "unique_content_versions": len(set(contents)),
        "message": "All nodes have identical content" if is_consistent else "Nodes are converging to consistency"
    }

@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all collaborative documents"""
    global ACTIVE_DOCUMENTS
    documents = []
    
    # Always include the demo document first
    if DEMO_DOCUMENT_ID:
        documents.append({
            "doc_id": DEMO_DOCUMENT_ID,
            "title": "Live Collaborative Demo",
            "is_demo": True
        })
    
    for doc_id in ACTIVE_DOCUMENTS[-10:]:  # Show last 10 documents
        if doc_id != DEMO_DOCUMENT_ID:  # Don't duplicate demo doc
            try:
                nodes = get_cluster_nodes()
                response = requests.get(f"http://{nodes[0]}/causal/kv/{doc_id}", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if "value" in data and "error" not in data:
                        doc_data = json.loads(data["value"])
                        documents.append({
                            "doc_id": doc_id,
                            "title": doc_data.get("title", "Untitled"),
                            "version": doc_data.get("version", 1),
                            "paragraphs": len(doc_data.get("paragraphs", {})),
                            "created_at": doc_data.get("created_at", time.time()),
                            "vector_clock": data.get("vector_clock", {})
                        })
            except Exception as e:
                print(f"Error loading document {doc_id}: {e}")
    
    return jsonify({"success": True, "documents": documents})

@app.route('/api/documents', methods=['POST'])
def create_document():
    """Create a new collaborative document with causal consistency"""
    data = request.json
    nodes = get_cluster_nodes()
    
    doc_id = f"doc_{int(time.time() * 1000)}"
    doc_data = {
        "title": data.get("title", "Untitled Document"),
        "paragraphs": {},
        "version": 1,
        "created_at": time.time(),
        "created_by": data.get("author", "Anonymous")
    }
    
    try:
        # Use causal consistency for document creation
        response = requests.put(
            f"http://{nodes[0]}/causal/kv/{doc_id}",
            json={"value": json.dumps(doc_data)},
            timeout=5
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if "error" in response_data:
                return jsonify({"success": False, "error": response_data["error"]}), 500
            
            # Track active document
            global ACTIVE_DOCUMENTS
            ACTIVE_DOCUMENTS.append(doc_id)
            if len(ACTIVE_DOCUMENTS) > 20:
                ACTIVE_DOCUMENTS.pop(0)
            
            # Emit real-time update
            socketio.emit('document_created', {
                'doc_id': doc_id,
                'title': doc_data["title"],
                'author': doc_data["created_by"],
                'timestamp': time.time(),
                'vector_clock': response_data.get("vector_clock", {})
            })
            
            return jsonify({
                "success": True, 
                "doc_id": doc_id, 
                "data": doc_data,
                "vector_clock": response_data.get("vector_clock", {})
            })
        else:
            return jsonify({"success": False, "error": f"Creation failed: {response.text}"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/documents/<doc_id>/edit', methods=['POST'])
def edit_document(doc_id):
    """Edit a paragraph in a document with causal consistency"""
    data = request.json
    para_id = data.get("para_id") 
    content = data.get("content")
    author = data.get("author", "Anonymous")
    author_color = data.get("author_color", "#000000")
    nodes = get_cluster_nodes()
    
    try:
        # Get current document with causal consistency for proper ordering
        response = requests.get(f"http://{nodes[0]}/causal/kv/{doc_id}", timeout=3)
        if response.status_code == 200:
            response_data = response.json()
            
            if "error" in response_data:
                return jsonify({"success": False, "error": response_data["error"]}), 500
            
            old_vector_clock = response_data.get("vector_clock", {})
            value_str = response_data.get("value", "{}")
            doc_data = json.loads(value_str)
            
            # Update paragraph with causal ordering
            if "paragraphs" not in doc_data:
                doc_data["paragraphs"] = {}
            
            doc_data["paragraphs"][para_id] = {
                "content": content,
                "author": author,
                "author_color": author_color,
                "timestamp": time.time(),
                "edit_id": f"edit_{int(time.time() * 1000000)}"  # Unique edit identifier
            }
            doc_data["version"] = doc_data.get("version", 0) + 1
            doc_data["last_modified"] = time.time()
            doc_data["last_author"] = author
            
            # Write back with causal consistency for proper edit ordering
            write_response = requests.put(
                f"http://{nodes[0]}/causal/kv/{doc_id}",
                json={"value": json.dumps(doc_data)},
                timeout=5
            )
            
            if write_response.status_code == 200:
                write_data = write_response.json()
                
                if "error" in write_data:
                    return jsonify({"success": False, "error": write_data["error"]}), 500
                
                new_vector_clock = write_data.get("vector_clock", {})
                
                # Emit real-time update to all connected clients
                socketio.emit('document_updated', {
                    'doc_id': doc_id,
                    'para_id': para_id,
                    'content': content,
                    'author': author,
                    'author_color': author_color,
                    'version': doc_data["version"],
                    'timestamp': time.time(),
                    'old_vector_clock': old_vector_clock,
                    'new_vector_clock': new_vector_clock,
                    'edit_id': doc_data["paragraphs"][para_id]["edit_id"]
                })
                
                return jsonify({
                    "success": True, 
                    "document": doc_data,
                    "old_vector_clock": old_vector_clock,
                    "new_vector_clock": new_vector_clock,
                    "causal_ordering": "preserved"
                })
            else:
                return jsonify({"success": False, "error": f"Write failed: {write_response.text}"}), 500
        else:
            return jsonify({"success": False, "error": "Document not found"}), 404
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/cluster/status')
def cluster_status():
    """Get cluster health status"""
    nodes = get_cluster_nodes()
    status = {}
    
    for i, node in enumerate(nodes):
        try:
            response = requests.get(f"http://{node}/health", timeout=2)
            if response.status_code == 200:
                status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "healthy",
                    "data": response.json()
                }
            else:
                status[f"node-{i+1}"] = {
                    "address": node,
                    "status": "error",
                    "message": f"HTTP {response.status_code}"
                }
        except Exception as e:
            status[f"node-{i+1}"] = {
                "address": node,
                "status": "offline",
                "message": str(e)
            }
    
    return jsonify(status)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to Collaborative Editor demo'})

@socketio.on('join_document')
def handle_join_document(data):
    """Handle joining a specific document"""
    doc_id = data.get('doc_id')
    author = data.get('author', 'Anonymous')
    
    # Join the document room for real-time updates
    from flask_socketio import join_room
    join_room(doc_id)
    
    emit('joined_document', {
        'doc_id': doc_id,
        'author': author,
        'timestamp': time.time()
    })

# Automatic user simulation functions
def simulate_alice_editing():
    """Simulate Alice editing the document"""
    while True:
        try:
            if DEMO_DOCUMENT_ID:
                # Alice's editing patterns
                alice_texts = [
                    "Alice here: I'm working on the introduction. ",
                    "The distributed database provides excellent consistency guarantees. ",
                    "With causal consistency, we ensure proper edit ordering. ",
                    "Notice how my edits always appear in the correct sequence. ",
                    "Even when Bob and I edit simultaneously, order is preserved! "
                ]
                
                para_id = random.choice(USER_ALICE["paragraphs"])
                text = random.choice(alice_texts)
                
                # Simulate typing character by character
                current_text = ""
                for char in text:
                    current_text += char
                    
                    requests.post(f'http://localhost:8002/api/documents/{DEMO_DOCUMENT_ID}/edit',
                                json={
                                    "doc_id": DEMO_DOCUMENT_ID,
                                    "para_id": para_id,
                                    "content": current_text,
                                    "author": USER_ALICE["name"],
                                    "author_color": USER_ALICE["color"]
                                }, timeout=3)
                    
                    time.sleep(USER_ALICE["typing_speed"])
                
                # Pause between edits
                time.sleep(random.uniform(3, 8))
                
        except Exception as e:
            print(f"Alice editing error: {e}")
            time.sleep(5)

def simulate_bob_editing():
    """Simulate Bob editing the document"""
    while True:
        try:
            if DEMO_DOCUMENT_ID:
                # Bob's editing patterns
                bob_texts = [
                    "Bob's input: The system handles concurrent edits beautifully. ",
                    "I can see Alice's changes in real-time as she types. ",
                    "Vector clocks ensure our edits never conflict. ",
                    "The causal consistency prevents any ordering issues. ",
                    "This is perfect for real-world collaborative applications! "
                ]
                
                para_id = random.choice(USER_BOB["paragraphs"])
                text = random.choice(bob_texts)
                
                # Simulate typing character by character
                current_text = ""
                for char in text:
                    current_text += char
                    
                    requests.post(f'http://localhost:8002/api/documents/{DEMO_DOCUMENT_ID}/edit',
                                json={
                                    "doc_id": DEMO_DOCUMENT_ID,
                                    "para_id": para_id,
                                    "content": current_text,
                                    "author": USER_BOB["name"],
                                    "author_color": USER_BOB["color"]
                                }, timeout=3)
                    
                    time.sleep(USER_BOB["typing_speed"])
                
                # Pause between edits
                time.sleep(random.uniform(4, 9))
                
        except Exception as e:
            print(f"Bob editing error: {e}")
            time.sleep(5)

def simulate_conflict_scenario():
    """Periodically simulate editing conflicts to show resolution"""
    while True:
        try:
            time.sleep(30)  # Every 30 seconds
            
            if DEMO_DOCUMENT_ID:
                # Both users edit the same paragraph simultaneously
                conflict_para = "intro"
                
                print("🔄 Simulating concurrent edit conflict...")
                
                # Alice starts typing
                threading.Thread(target=lambda: requests.post(
                    f'http://localhost:8002/api/documents/{DEMO_DOCUMENT_ID}/edit',
                    json={
                        "doc_id": DEMO_DOCUMENT_ID,
                        "para_id": conflict_para,
                        "content": "Alice: Starting my edit at " + datetime.now().strftime("%H:%M:%S"),
                        "author": USER_ALICE["name"],
                        "author_color": USER_ALICE["color"]
                    }, timeout=3
                )).start()
                
                # Bob edits same paragraph 100ms later
                time.sleep(0.1)
                threading.Thread(target=lambda: requests.post(
                    f'http://localhost:8002/api/documents/{DEMO_DOCUMENT_ID}/edit',
                    json={
                        "doc_id": DEMO_DOCUMENT_ID,
                        "para_id": conflict_para,
                        "content": "Bob: My concurrent edit at " + datetime.now().strftime("%H:%M:%S"),
                        "author": USER_BOB["name"],
                        "author_color": USER_BOB["color"]
                    }, timeout=3
                )).start()
                
                # Show how causal consistency resolves this
                print("✅ Causal consistency will order these edits properly!")
                
        except Exception as e:
            print(f"Conflict simulation error: {e}")

def init_demo_document():
    """Initialize the main demo document"""
    global DEMO_DOCUMENT_ID
    nodes = get_cluster_nodes()
    
    DEMO_DOCUMENT_ID = f"doc_collab_demo_{int(time.time())}"
    
    doc_data = {
        "title": "🚀 Live Collaborative Editing Demo",
        "paragraphs": {
            "intro": {
                "content": "Welcome! Alice and Bob will start editing this document...",
                "author": "System",
                "author_color": "#666666",
                "timestamp": time.time()
            },
            "section1": {
                "content": "Section 1: Alice primarily edits here",
                "author": "System",
                "author_color": "#666666",
                "timestamp": time.time()
            },
            "section2": {
                "content": "Section 2: Bob primarily edits here", 
                "author": "System",
                "author_color": "#666666",
                "timestamp": time.time()
            },
            "section3": {
                "content": "Section 3: Another section for Alice",
                "author": "System",
                "author_color": "#666666",
                "timestamp": time.time()
            },
            "section4": {
                "content": "Section 4: Another section for Bob",
                "author": "System",
                "author_color": "#666666",
                "timestamp": time.time()
            }
        },
        "version": 1,
        "created_at": time.time(),
        "created_by": "System"
    }
    
    try:
        response = requests.put(
            f"http://{nodes[0]}/causal/kv/{DEMO_DOCUMENT_ID}",
            json={"value": json.dumps(doc_data)},
            timeout=5
        )
        if response.status_code == 200:
            ACTIVE_DOCUMENTS.append(DEMO_DOCUMENT_ID)
            print(f"✅ Created demo document: {DEMO_DOCUMENT_ID}")
            print(f"📝 Alice and Bob will start editing automatically...")
            return True
    except Exception as e:
        print(f"Error creating demo document: {e}")
        return False

if __name__ == '__main__':
    # Initialize demo document
    if init_demo_document():
        # Start Alice's editing thread
        alice_thread = threading.Thread(target=simulate_alice_editing, daemon=True)
        alice_thread.start()
        
        # Start Bob's editing thread (slight delay to show interleaving)
        time.sleep(2)
        bob_thread = threading.Thread(target=simulate_bob_editing, daemon=True)
        bob_thread.start()
        
        # Start conflict simulation thread
        conflict_thread = threading.Thread(target=simulate_conflict_scenario, daemon=True)
        conflict_thread.start()
    
    print("📝 Starting Collaborative Editor Demo...")
    print("📍 URL: http://localhost:8002")
    print("🎯 Features: Real-time collaborative editing with causal consistency")
    print("🔄 Endpoints: Causal /causal/kv/ (proper edit ordering)")
    print("👥 Automatic Users:")
    print(f"   {USER_ALICE['avatar']} Alice (Color: {USER_ALICE['color']}) - Editing sections 1 & 3")
    print(f"   {USER_BOB['avatar']} Bob (Color: {USER_BOB['color']}) - Editing sections 2 & 4")
    print("⚡ Watch as they edit simultaneously with perfect consistency!")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=8002, allow_unsafe_werkzeug=True)