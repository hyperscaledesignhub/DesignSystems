# Demo UI Organization

## 📁 Directory Structure

### Main Demo Applications (Numbered by Complexity)

1. **`1-concurrent_writes_demo.py`** - Basic distributed consistency demo
   - Port: 8005
   - Demonstrates quorum consensus and concurrent write handling
   - Banking, e-commerce, and social media scenarios

2. **`2-crdt_counter_demo.py`** - CRDT counter mechanics demo
   - Demonstrates conflict-free replicated data types
   - Shows how distributed counters work

3. **`3-sync_demo.py`** - Data synchronization demo
   - Shows anti-entropy and data sync mechanisms
   - Node synchronization visualization

4. **`4-node_failure_demo.py`** - Node failure & recovery demo
   - Port: 8007
   - Simulates node failures and recovery
   - Shows data resilience and CRDT counter sync

5. **`5-twitter_demo.py`** - Real-time social media demo
   - Port: 8001
   - Twitter-like engagement tracking
   - Persistent counters for likes, retweets, etc.

6. **`6-collab_editor_demo.py`** - Collaborative editing demo
   - Port: 8002
   - Real-time document editing
   - Causal consistency demonstration

7. **`7-cdn_demo.py`** - Content distribution demo
   - Port: 8004
   - CDN simulation with regional distribution
   - Content optimization across regions

8. **`8-inventory_demo.py`** - Multi-warehouse inventory demo
   - Port: 8003
   - Distributed inventory management
   - Load-balanced operations

### Supporting Files

- **`app.py`** - Main demo launcher/hub (Port: 7342)
- **`api_extensions.py`** - API extensions for database operations
- **`real_traffic_generator.py`** - Traffic generation utility
- **`cumulative_counters.py`** - Counter management utilities

### Test Scripts

- **`test_concurrent_writes_15min.py`** - 15-minute performance test
- **`test_simplified_demo_5min.py`** - 5-minute quick test

### Shell Scripts

- **`run_all_demos.sh`** - Main launcher with menu
- **`run_*.sh`** - Individual demo launchers
- **`start_demo_ui.sh`** - Start main UI

### Directories

- **`templates/`** - HTML templates for demos
- **`static/`** - CSS and JavaScript files
- **`archived_files/`** - Deprecated/experimental files
  - Old test templates
  - Duplicate traffic generator
  - Log files

## 🚀 Running Demos

1. Start the cluster first:
   ```bash
   cd /Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB
   ./start-node-failure-cluster.sh
   ```

2. Run individual demos:
   ```bash
   ./run_concurrent_writes_demo.sh  # Demo 1
   python 4-node_failure_demo.py     # Demo 4 (direct)
   ```

3. Or use the main launcher:
   ```bash
   ./run_all_demos.sh
   ```

## 📝 Notes

- Demos are numbered by increasing complexity/features
- Each demo showcases specific distributed database capabilities
- All demos require the cluster to be running first
- Check individual demo files for specific ports and features