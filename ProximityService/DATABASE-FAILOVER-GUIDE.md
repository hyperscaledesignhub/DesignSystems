# 🔍 Database Failover Testing Guide

## How to Test Primary Database Failure

### **Method 1: Using UI (Recommended for Demos)**

1. **Open the Demo UI**: http://localhost:8081
2. **Go to "Failover" Tab**
3. **Click "Kill Primary DB"** - This shows you the command to run
4. **Run the command in terminal**: `docker-compose stop postgres-primary`
5. **Click "Monitor" tab** to see health status changes

### **Method 2: Command Line**

```bash
# Kill primary database
docker-compose stop postgres-primary

# Check failover status
./check-db-failover.sh

# Restore primary database
docker-compose start postgres-primary
```

## How to Verify Database Failover Worked

### **🔍 Check Container Status**
```bash
docker-compose ps | grep postgres
```
**Expected Output:**
- `postgres-primary`: **Exited** (or not listed)
- `postgres-replica1`: **Up** ✅
- `postgres-replica2`: **Up** ✅

### **🔍 Check Application Behavior**

#### **1. Read Operations (Should Work) ✅**
```bash
curl -s "http://localhost:8921/nearby?latitude=37.7849&longitude=-122.4094&radius=1000" | python3 -c "import sys,json; data=json.load(sys.stdin); print(f'Found {len(data[\"businesses\"])} businesses')"
```
**Expected**: `Found X businesses` (reads continue via replicas)

#### **2. Write Operations (Should Fail) ❌**
```bash
curl -X POST "http://localhost:9823/businesses" -H "Content-Type: application/json" -d '{"name":"Test","latitude":37.7749,"longitude":-122.4194,"address":"123 St","city":"SF","state":"CA","country":"USA","category":"Test"}'
```
**Expected**: `{"detail":"Internal server error"}` (writes fail without primary)

#### **3. Search via UI (Should Work) ✅**
- Go to http://localhost:8081 → Search tab
- Click "Search Nearby"
- **Expected**: Business results appear (reads work)

#### **4. Create via UI (Should Fail) ❌** 
- Go to Create tab → Fill form → Click "Create Business"  
- **Expected**: Error message (writes fail)

### **🔍 Check Service Health**
```bash
curl -s "http://localhost:9823/health" | python3 -m json.tool
```
**Expected Output:**
```json
{
  "status": "healthy",
  "database": {
    "primary": false,           ← Primary is down
    "promoted_primary": false,
    "replicas": [
      {"replica": 1, "healthy": true},  ← Replicas still healthy
      {"replica": 2, "healthy": true}
    ]
  },
  "redis": {
    "master": true,
    "slaves": [{"slave": 1, "healthy": true}],
    "sentinels": true
  }
}
```

### **🔍 Check Application Logs**
```bash
docker-compose logs business-service --tail 20
```
**Expected**: Error messages about primary database connection failures

## Verification Checklist

### ✅ **Successful Failover Indicators:**

| Test | Expected Result | Status |
|------|----------------|--------|
| Primary Container | `Exited` or not running | ❌ |
| Replica Containers | `Up` and running | ✅ |
| Read Operations | Return business data | ✅ |
| Write Operations | Return error messages | ❌ |
| Search UI | Shows search results | ✅ |
| Create UI | Shows error message | ❌ |
| Health Endpoint | `"primary": false` | ❌ |
| Service Health | Still reports "healthy" | ✅ |

### ❌ **Failed Failover Indicators:**
- Replicas also down/unhealthy
- Read operations return errors
- Complete service outage
- Health endpoint unreachable

## Database Failover States

### **🟢 Normal Operation**
- ✅ Primary: Running
- ✅ Replicas: Running  
- ✅ Reads: Work
- ✅ Writes: Work

### **🟡 Failover Mode (Primary Down)**
- ❌ Primary: Down
- ✅ Replicas: Running
- ✅ Reads: Work (via replicas)
- ❌ Writes: Fail (no primary)

### **🔴 Complete Outage** 
- ❌ Primary: Down
- ❌ Replicas: Down
- ❌ Reads: Fail
- ❌ Writes: Fail

## Restoring Normal Operation

### **Command Line:**
```bash
docker-compose start postgres-primary
```

### **Verification After Restore:**
```bash
# Wait a few seconds for startup
sleep 5

# Check all operations work
./check-db-failover.sh
```

**Expected**: All operations should return to normal ✅

## Advanced Checks

### **Direct Database Connection Test:**
```bash
# Test primary (should fail when down)
docker exec 10-proximityservice-postgres-primary-1 pg_isready -U postgres

# Test replicas (should succeed)
docker exec 10-proximityservice-postgres-replica1-1 pg_isready -U postgres
docker exec 10-proximityservice-postgres-replica2-1 pg_isready -U postgres
```

### **Check Database Connections in Code:**
The database connection routing logic is in:
- `services/business-service/db_pool.py:get_write_connection()`
- `services/location-service/db_pool.py:get_read_connection()`

These handle failover automatically by trying primary first, then falling back to replicas.

---

**🎯 Summary**: Primary database failure should result in **graceful degradation** - reads continue via replicas while writes fail, demonstrating proper high-availability architecture!