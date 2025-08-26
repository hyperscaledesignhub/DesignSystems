# 🚀 AdClick Demo - Simple Running Instructions

## ✅ **NO DOCKER REQUIRED!**

This is a **standalone Python demo** that runs without Docker. Here's how to use it:

## 📦 **Option 1: Direct Python Run (Simplest)**

```bash
# From the demo directory, run:
python3 simple_demo_api.py
```

That's it! The demo is now running at: **http://localhost:8900**

## 📦 **Option 2: Using Virtual Environment (Recommended)**

```bash
# 1. Create virtual environment (only once)
python3 -m venv demo_env

# 2. Activate it
source demo_env/bin/activate

# 3. Install dependencies (only once)
pip install flask flask-cors kafka-python influxdb-client requests

# 4. Run the demo
python simple_demo_api.py
```

## 🎯 **Access the Demo**

Once running, open your browser and go to:

### **Main Dashboard**: http://localhost:8900
- Interactive web interface with controls
- Real-time metrics display
- Start/stop simulation buttons
- Scenario switching dropdown

### **API Endpoints**:
- Health Check: http://localhost:8900/health
- Scenarios: http://localhost:8900/api/scenarios
- Real-time Metrics: http://localhost:8900/api/metrics/realtime
- Fraud Alerts: http://localhost:8900/api/fraud/alerts

## 🎬 **How to Use the Demo**

### **Step 1: Open the Dashboard**
Go to http://localhost:8900 in your browser

### **Step 2: Start the Simulation**
1. Select a scenario from the dropdown (E-commerce, Gaming, Finance, Social)
2. Click "▶️ Start Simulation" button
3. Watch the metrics update in real-time!

### **Step 3: Explore Features**
- **Real-time Metrics**: Total clicks, revenue/hour, fraud rate, clicks/second
- **Top Performing Ads**: Live ranking of best performing advertisements
- **Recent Events**: Stream of actual click events being generated
- **Fraud Alerts**: Security warnings and suspicious activity detection

### **Step 4: Test Different Scenarios**
Switch between scenarios to show different business use cases:
- **E-commerce Holiday Sale**: High-volume retail patterns
- **Mobile Gaming Campaign**: Gaming app promotions
- **Financial Services**: Conservative, compliance-focused
- **Social Media Platform**: Viral marketing patterns

## 🛠️ **Test the API Directly**

### Start simulation:
```bash
curl -X POST http://localhost:8900/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"speed": 1.0}'
```

### Get real-time metrics:
```bash
curl http://localhost:8900/api/metrics/realtime | python3 -m json.tool
```

### Check fraud alerts:
```bash
curl http://localhost:8900/api/fraud/alerts | python3 -m json.tool
```

### Stop simulation:
```bash
curl -X POST http://localhost:8900/api/simulation/stop
```

## ⚠️ **Important Notes**

1. **This demo does NOT require Docker** - It's a standalone Python application
2. **The complex Docker setup is optional** - You can ignore all docker-compose files
3. **All features work without external dependencies** - No Kafka, InfluxDB, or other services needed
4. **Data is simulated in-memory** - Perfect for demonstrations

## 🎯 **What This Demo Shows**

✅ **Real-time Event Processing** - Simulates up to 5000 events/second
✅ **Business Scenarios** - 4 different industry use cases
✅ **Fraud Detection** - Live security monitoring and alerts
✅ **Performance Metrics** - System health and throughput monitoring
✅ **Interactive Dashboard** - Professional web interface
✅ **REST API** - Complete API for integration demonstrations

## 🛑 **To Stop the Demo**

Press `Ctrl+C` in the terminal where the demo is running.

---

**That's all! The demo is fully functional and ready for customer presentations.**

No Docker, no complex setup - just run and demonstrate! 🎉