# 🌐 CDN Demo - Complete Guide

## Prerequisites

1. Python 3.x installed
2. Required dependencies (`pip install -r requirements.txt`)
3. Distributed database cluster running

## Step-by-Step Instructions

### 1️⃣ Start the Database Cluster

```bash
# Navigate to project root
cd /Users/vijayabhaskarv/hyper-scale/kvdb/DesignSystems/NoSQL-DB

# Start the cluster
./scripts/start-cluster-local.sh

# Wait for nodes to initialize (about 10 seconds)
```

### 2️⃣ Launch the CDN Demo

```bash
# Navigate to demo directory
cd demo/ui

# Run the CDN demo
./run_cdn_demo.sh
```

### 3️⃣ Open the Demo Interface

Open your web browser and go to: **http://localhost:8004**

## 🎮 How to Use the Demo

### A. Initialize the Hash Ring
1. Click **"🔄 Initialize Ring"** button
2. Watch the visualization of consistent hashing
3. See how content maps to nodes

### B. Upload Content
1. Enter a content name (e.g., "movie_avengers_4k.mp4")
2. Set content size (e.g., 2000 MB)
3. Select content type (Video/Image/Document)
4. Click **"🚀 Upload Content"**
5. Watch content get distributed across nodes

### C. Simulate User Requests
1. Content is automatically requested from different regions
2. Monitor cache hits vs misses
3. See response times from different regions

### D. Test Node Failures
1. Click **"➖ Remove Node"** to simulate CDN node failure
2. Watch content redistribute automatically
3. Notice how consistent hashing minimizes redistribution

### E. Add New Nodes
1. Click **"➕ Add Node"** to scale the CDN
2. See minimal content movement
3. Load rebalances automatically

## 📊 What to Observe

### Hash Ring Visualization
- **Blue dots**: CDN nodes on the hash ring
- **Red dots**: Content items mapped to nodes
- **Lines**: Show which content belongs to which node

### Geographic Distribution
- **US-East**: Primary region (Node 1)
- **US-West**: Secondary region (Node 2)
- **EU-West**: European region (Node 3)
- Shows content replication across regions

### Performance Metrics
- **Cache Hit Ratio**: Higher is better (>80% is good)
- **Average Latency**: Lower is better (<50ms is excellent)
- **Load Distribution**: Should be roughly even across nodes

### Real-time Updates
- Watch content requests in real-time
- See cache performance per region
- Monitor node load balancing

## 🔧 Advanced Features

### Content Invalidation
- Simulates updating content across all edge locations
- Click on any content item to invalidate its cache
- Watch it propagate across regions

### Traffic Patterns
- Demo simulates realistic traffic patterns
- More requests from certain regions
- Time-of-day variations

### Monitoring
- Real-time statistics update
- Per-node load monitoring
- Global CDN performance metrics

## 🛑 Stopping the Demo

```bash
# Stop just the CDN demo
pkill -f "7-cdn_demo.py"

# Or stop all demos
./demo/ui/run_all_demos.sh
# Select option 7 (Stop All Demos)

# Stop the cluster when done
cd ../..
./scripts/stop-cluster.sh
```

## 💡 Key Takeaways

1. **Consistent Hashing** ensures minimal data movement when scaling
2. **Geographic Distribution** reduces latency for global users
3. **Caching** dramatically improves performance
4. **Fault Tolerance** keeps content available during node failures
5. **Load Balancing** distributes traffic evenly

## 🐛 Troubleshooting

### Demo won't start
- Check if cluster is running: `curl http://localhost:9999/health`
- Kill existing demo: `pkill -f "7-cdn_demo.py"`
- Check logs for errors

### No content appearing
- Ensure cluster has 3 nodes running
- Refresh the page
- Check browser console for errors

### Performance issues
- Ensure you're running locally (not over network)
- Check system resources
- Reduce content size for testing

## 📚 Learn More

- Study the consistent hashing implementation
- Examine cache invalidation strategies
- Explore geographic routing logic
- Understand load balancing algorithms