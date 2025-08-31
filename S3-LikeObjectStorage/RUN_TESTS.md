# 🧪 S3 Storage System - How to Run Tests

## ⚡ Quick Start (30 seconds)

```bash
# 1. Start the system
docker-compose up -d

# 2. Run quick test
./test-quick.sh

# 3. See if it works!
```

## 🎯 Test Options

### Option 1: Quick Validation (1 minute)
```bash
./test-quick.sh
```
**What it does**: Tests basic CRUD operations to verify system is working

### Option 2: Full Test Suite (10 minutes)
```bash
./run_all_tests.sh
```
**What it does**: Runs all tests, generates detailed reports

### Option 3: Manual API Testing (5 minutes)
```bash
# Get API key first
API_KEY=$(docker-compose logs identity-service | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //')

# Run manual tests
API_KEY="$API_KEY" ./test-api.sh
```

## 🚀 Different Deployment Methods

### Docker Compose Testing
```bash
# Start services
docker-compose up -d
sleep 30  # Wait for services to start

# Run tests (auto-detects API key)
./run_all_tests.sh

# Cleanup
docker-compose down
```

### Kubernetes Testing
```bash
# Deploy to Kubernetes
./deployment/deploy.sh

# Get gateway IP
GATEWAY_IP=$(kubectl get service api-gateway-service -n s3-storage -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Run tests
GATEWAY_URL="http://$GATEWAY_IP" ./run_all_tests.sh

# Cleanup
./deployment/cleanup.sh
```

### Local Development Testing
```bash
# Start services individually in separate terminals
cd services/identity && python main.py      # Terminal 1
cd services/bucket && python main.py        # Terminal 2
cd services/storage && python main.py       # Terminal 3
cd services/metadata && python main.py      # Terminal 4
cd services/object && python main.py        # Terminal 5
cd services/api-gateway && python main.py   # Terminal 6

# In another terminal, run tests
./run_all_tests.sh
```

## 📊 Test Results Explained

### ✅ Success Output
```
🎉 All test suites passed!
Total Test Suites: 3
Passed: 3
Failed: 0
Success Rate: 100%
```

### ❌ Failure Output
```
❌ Some test suites failed. Check the results for details.
Total Test Suites: 3
Passed: 2
Failed: 1
Success Rate: 66%
```

### 📈 Performance Output
```
📤 Testing Upload Performance (1 threads)
Size:      1 KB | Success:  1/1 | Avg Time:  0.045s | Throughput:  22.22 MB/s
Size:     10 KB | Success:  1/1 | Avg Time:  0.052s | Throughput: 192.31 MB/s
```

## 🛠️ Troubleshooting

### Problem: "Services not reachable"
```bash
# Check if services are running
docker-compose ps
curl http://localhost:7841/health

# If not running, start them
docker-compose up -d
```

### Problem: "Could not get API key"
```bash
# Get API key manually
docker-compose logs identity-service | grep "Admin API Key"

# Set it manually
export API_KEY="s3_key_your_actual_key_here"
./run_all_tests.sh
```

### Problem: "Tests timing out"
```bash
# Wait longer for services to start
sleep 60

# Check service logs for errors
docker-compose logs api-gateway
docker-compose logs identity-service
```

### Problem: "Rate limiting errors"
```bash
# Wait between test runs
sleep 60
./run_all_tests.sh
```

## 📋 What Each Test Checks

### Quick Test (`test-quick.sh`)
- ✅ Services are running
- ✅ Can create bucket
- ✅ Can upload object
- ✅ Can download object (content verification)
- ✅ Can list objects
- ✅ Can delete object
- ✅ Can delete bucket
- ✅ Authentication works

### Comprehensive Test (`test_all.py`)
- ✅ All bucket operations + edge cases
- ✅ All object operations + special files
- ✅ Authentication & authorization
- ✅ Rate limiting
- ✅ Concurrent operations
- ✅ Error handling
- ✅ Data integrity checks

### Performance Test (`test_performance.py`)
- ✅ Upload/download speed
- ✅ Different file sizes
- ✅ Concurrent operations
- ✅ Mixed workloads
- ✅ Throughput measurement

### Service Test (`test_individual_services.py`)
- ✅ Each service individually
- ✅ Service-to-service communication
- ✅ Database connectivity
- ✅ Health checks

## 🔍 Reading Test Reports

After running tests, check the `test_results/` directory:

```
test_results/
├── test_report_20241127_143022.html     # Visual HTML report
├── Comprehensive_API_Tests_20241127_143022.txt
├── Individual_Services_20241127_143022.txt
└── Performance_Tests_20241127_143022.txt
```

Open the HTML report in your browser for a nice visual overview!

## 🎯 Before Production Deployment

**Must-pass checklist:**

```bash
# 1. Quick smoke test
./test-quick.sh

# 2. Full functionality test
./run_all_tests.sh

# 3. Performance validation
API_KEY="$API_KEY" python3 tests/test_performance.py

# 4. Load test (optional)
# Run multiple test instances in parallel to simulate load
```

## 🚨 CI/CD Integration

### GitHub Actions Example
```yaml
name: Test S3 Storage
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          docker-compose up -d
          sleep 60
          ./run_all_tests.sh
```

### Jenkins Example
```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'docker-compose up -d'
                sh 'sleep 60'
                sh './run_all_tests.sh'
            }
        }
    }
    post {
        always {
            sh 'docker-compose down'
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'test_results',
                reportFiles: '*.html',
                reportName: 'Test Report'
            ])
        }
    }
}
```

## 💡 Test Development

### Adding New Tests

1. **API Tests**: Add to `tests/test_all.py`
2. **Service Tests**: Add to `tests/test_individual_services.py`  
3. **Performance Tests**: Add to `tests/test_performance.py`

### Test Structure
```python
def test_new_feature(self):
    """Test new functionality"""
    try:
        # Setup
        # Execute
        # Verify
        self.log_test("Test name", success, details)
    except Exception as e:
        self.log_test("Test name", False, str(e))
```

## 📝 Test Coverage Matrix

| Feature | API Test | Service Test | Performance Test | Corner Cases |
|---------|----------|--------------|------------------|--------------|
| Create Bucket | ✅ | ✅ | ✅ | ✅ |
| Upload Object | ✅ | ✅ | ✅ | ✅ |
| Download Object | ✅ | ✅ | ✅ | ✅ |
| Delete Object | ✅ | ✅ | ✅ | ✅ |
| List Objects | ✅ | ✅ | ✅ | ✅ |
| Authentication | ✅ | ✅ | ❌ | ✅ |
| Rate Limiting | ✅ | ❌ | ❌ | ✅ |
| Error Handling | ✅ | ✅ | ❌ | ✅ |
| Concurrency | ✅ | ❌ | ✅ | ✅ |
| Data Integrity | ✅ | ✅ | ❌ | ✅ |

**Legend**: ✅ Covered, ❌ Not applicable/covered

This testing framework ensures your S3 Storage System is production-ready and handles all edge cases correctly!