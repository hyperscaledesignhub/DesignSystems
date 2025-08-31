# S3 Storage System - Testing Guide

## 🧪 Complete Testing Documentation

This guide provides comprehensive instructions for testing the S3 Storage System, including all corner cases, performance validation, and edge conditions.

## 📋 Test Overview

### Test Suites Available

1. **Comprehensive API Tests** (`test_all.py`) - End-to-end functionality testing
2. **Individual Service Tests** (`test_individual_services.py`) - Unit tests for each microservice
3. **Performance Tests** (`test_performance.py`) - Load testing and performance validation
4. **Automated Test Runner** (`run_all_tests.sh`) - Orchestrates all test suites

### Test Coverage

- ✅ **Core Functionality**: All CRUD operations for buckets and objects
- ✅ **Authentication**: API key validation and unauthorized access prevention
- ✅ **Input Validation**: Invalid bucket names, malformed requests
- ✅ **Error Handling**: Non-existent resources, service failures
- ✅ **Performance**: Throughput, latency, concurrent operations
- ✅ **Corner Cases**: Long keys, special characters, edge conditions
- ✅ **Rate Limiting**: Request throttling and limits
- ✅ **Data Integrity**: Checksum validation, content verification

## 🚀 Quick Start Testing

### Option 1: Run All Tests (Recommended)

```bash
# Set your API key (get from identity service logs)
export API_KEY="s3_key_your_api_key_here"

# Run all test suites
./run_all_tests.sh
```

### Option 2: Docker Compose Testing

```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Get API key from logs
API_KEY=$(docker-compose logs identity-service | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //')

# Run tests
API_KEY="$API_KEY" ./run_all_tests.sh

# Cleanup
docker-compose down
```

### Option 3: Kubernetes Testing

```bash
# Deploy system
./deployment/deploy.sh

# Get API key
API_KEY=$(kubectl logs -n s3-storage -l app=identity-service | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //')

# Get gateway IP
GATEWAY_IP=$(kubectl get service api-gateway-service -n s3-storage -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Run tests
API_KEY="$API_KEY" GATEWAY_URL="http://$GATEWAY_IP" ./run_all_tests.sh

# Cleanup
./deployment/cleanup.sh
```

## 🔍 Individual Test Suites

### 1. Comprehensive API Tests

Tests all functionality through the API Gateway (end-to-end testing).

```bash
API_KEY="your_key" python3 tests/test_all.py
```

**What it tests:**
- **Bucket Operations**: Create, list, delete, validation
- **Object Operations**: Upload, download, delete, list with prefix
- **Authentication**: Valid/invalid API keys, missing auth
- **Rate Limiting**: High request rate handling
- **Concurrent Operations**: Multi-threaded uploads/downloads
- **Corner Cases**: Special characters, long paths, overwrites
- **Error Handling**: Non-existent resources, malformed requests

**Sample Output:**
```
🧪 S3 Storage System - Comprehensive Test Suite
============================================================
Gateway URL: http://localhost:7841
API Key: Bearer s3_key_ABCDEFGHIJKLMNOPQRSTUVWXYZabcd...

🔐 Testing Authentication
  [✅] Request without auth returns 401
  [✅] Request with invalid auth returns 401
  [✅] Request with malformed auth returns 401

📦 Testing Bucket Operations
  [✅] Create bucket 'test-bucket-basic'
  [✅] Create bucket 'test-bucket-special-123'
  [❌] Invalid bucket name 'A' rejected
```

### 2. Individual Service Tests

Tests each microservice directly, bypassing the API Gateway.

```bash
python3 tests/test_individual_services.py
```

**What it tests:**
- **Service Connectivity**: Health checks for all services
- **Identity Service**: User creation, API key validation
- **Bucket Service**: Direct bucket operations
- **Storage Service**: Raw data storage and retrieval
- **Metadata Service**: Object metadata management
- **Service Isolation**: Each service functioning independently

### 3. Performance Tests

Measures system performance and identifies bottlenecks.

```bash
API_KEY="your_key" python3 tests/test_performance.py
```

**What it tests:**
- **Upload Performance**: Different file sizes (1KB to 1MB)
- **Download Performance**: Throughput measurement
- **Concurrent Operations**: Multi-threaded operations
- **Mixed Workloads**: Upload, download, list operations together
- **Bucket Operations**: Creation and listing performance

**Sample Output:**
```
📤 Testing Upload Performance (1 threads)
------------------------------------------------------------
Size:      1 KB | Success:  1/1 | Avg Time:  0.045s | Throughput:  22.22 MB/s
Size:     10 KB | Success:  1/1 | Avg Time:  0.052s | Throughput: 192.31 MB/s
Size:    100 KB | Success:  1/1 | Avg Time:  0.089s | Throughput: 1123.60 MB/s
Size:   1024 KB | Success:  1/1 | Avg Time:  0.234s | Throughput: 4376.07 MB/s
```

## 🎯 Test Scenarios Covered

### Bucket Operations

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| Valid bucket creation | Standard bucket name | 201 Created |
| Duplicate bucket | Same name twice | 409 Conflict |
| Invalid name - too short | "A" | 400 Bad Request |
| Invalid name - uppercase | "BUCKET" | 400 Bad Request |
| Invalid name - special chars | "bucket.name" | 400 Bad Request |
| List empty buckets | No buckets exist | 200 OK, empty array |
| List with buckets | Buckets exist | 200 OK, array with buckets |
| Delete empty bucket | No objects in bucket | 204 No Content |
| Delete non-existent bucket | Bucket doesn't exist | 404 Not Found |

### Object Operations

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| Upload text file | Plain text content | 201 Created, correct ETag |
| Upload binary file | Random binary data | 201 Created, correct ETag |
| Upload large file | 1MB+ file | 201 Created |
| Upload empty file | 0 bytes | 400 Bad Request |
| Upload with special chars | Unicode filename | 201 Created |
| Upload nested path | deep/folder/structure/file.txt | 201 Created |
| Download existing object | Object exists | 200 OK, correct content |
| Download non-existent | Object doesn't exist | 404 Not Found |
| Object overwrite | Same key twice | 201 Created, new content |
| List with prefix | Prefix filter | 200 OK, filtered results |
| Delete existing object | Object exists | 204 No Content |
| Delete non-existent | Object doesn't exist | 404 Not Found |

### Authentication & Security

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| No auth header | Missing Authorization | 401 Unauthorized |
| Invalid API key | Wrong key | 401 Unauthorized |
| Malformed header | Invalid format | 401 Unauthorized |
| Valid API key | Correct key | 200 OK |
| Rate limiting | 100+ requests/minute | 429 Too Many Requests |
| Cross-user access | Access other user's bucket | 403 Forbidden |

### Corner Cases & Edge Conditions

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| Very long object key | 200+ character path | 201 Created |
| Multiple slashes | folder//file.txt | 201 Created |
| Unicode filename | 文件名.txt | 201 Created |
| Special characters | !@#$%^&*()_+.txt | 201 Created |
| Content-Type preservation | Various MIME types | Correct Content-Type |
| Large object (1MB+) | Performance test | Reasonable time |
| Concurrent uploads | Multiple threads | All succeed |
| Concurrent downloads | Multiple threads | All succeed |
| Empty bucket listing | No objects | Empty array |

### Error Handling

| Test Case | Description | Expected Result |
|-----------|-------------|-----------------|
| Service unavailable | Backend service down | 503 Service Unavailable |
| Malformed JSON | Invalid request body | 422 Unprocessable Entity |
| Missing required fields | Incomplete request | 400 Bad Request |
| Database connection error | DB unavailable | 500 Internal Server Error |
| Disk full | Storage exhausted | 500 Internal Server Error |
| Network timeout | Slow network | Timeout with retry |

## 📊 Performance Benchmarks

### Expected Performance Characteristics

| Metric | Small Objects (<1KB) | Medium Objects (1-100KB) | Large Objects (>1MB) |
|--------|---------------------|-------------------------|---------------------|
| **Upload Latency** | 50-100ms | 100-300ms | 1-5s |
| **Download Latency** | 10-50ms | 50-200ms | 1-3s |
| **Throughput** | 100-500 ops/s | 50-200 ops/s | 10-50 ops/s |
| **Concurrent Ops** | 95%+ success | 90%+ success | 85%+ success |

### Performance Test Interpretation

- **Good Performance**: >90% success rate, latency within expected ranges
- **Degraded Performance**: 80-90% success rate, 2x expected latency
- **Poor Performance**: <80% success rate, >5x expected latency

## 🔧 Troubleshooting Test Issues

### Common Issues and Solutions

#### Tests Fail with Connection Error
```bash
# Check if services are running
curl http://localhost:7841/health

# Docker Compose
docker-compose ps

# Kubernetes
kubectl get pods -n s3-storage
```

#### Authentication Errors
```bash
# Get API key from logs
docker-compose logs identity-service | grep "Admin API Key"
kubectl logs -n s3-storage -l app=identity-service | grep "Admin API Key"

# Set environment variable
export API_KEY="s3_key_your_actual_key_here"
```

#### Test Timeouts
```bash
# Increase timeout in test scripts
# Check system resources
docker stats
kubectl top pods -n s3-storage

# Check service logs for errors
docker-compose logs
kubectl logs -n s3-storage -l app=storage-service
```

#### Rate Limiting Errors
```bash
# Wait between test runs
sleep 60

# Or increase rate limits in api-gateway/main.py
RATE_LIMIT_REQUESTS = 200  # Increase from 100
```

#### Database Connection Errors
```bash
# Check PostgreSQL
docker-compose logs postgresql
kubectl logs -n s3-storage -l app=postgresql

# Check database connectivity
docker-compose exec postgresql psql -U postgres -l
```

## 📈 Test Results Analysis

### Interpreting Test Output

#### Success Indicators
- All core functionality tests pass (95%+ success rate)
- Performance within expected ranges
- No memory leaks or resource exhaustion
- Proper error handling for edge cases

#### Warning Signs
- Success rate below 90%
- Performance degradation over time
- Frequent timeout errors
- High error rates in concurrent tests

#### Failure Analysis
- Check service logs for error patterns
- Monitor resource usage (CPU, memory, disk)
- Verify network connectivity between services
- Check database performance and connections

### Test Report Interpretation

The automated test runner generates detailed reports:

1. **HTML Report**: `test_results/test_report_TIMESTAMP.html`
   - Visual overview of all test results
   - Detailed logs for each test suite
   - Easy to share and review

2. **Individual Logs**: `test_results/*_TIMESTAMP.txt`
   - Raw output from each test suite
   - Detailed error messages and stack traces
   - Performance metrics and timing data

## 🚨 Critical Test Scenarios

### Must-Pass Tests for Production

1. **Basic CRUD Operations**: Create bucket, upload object, download object, delete object
2. **Authentication**: Proper auth validation and unauthorized access prevention  
3. **Data Integrity**: Uploaded content matches downloaded content
4. **Error Handling**: Graceful handling of invalid requests
5. **Performance**: Reasonable response times under normal load

### Regression Test Suite

Before any deployment:

```bash
# Quick regression test (5 minutes)
API_KEY="$API_KEY" python3 tests/test_all.py

# Full test suite (15 minutes)
./run_all_tests.sh

# Performance baseline (10 minutes)
API_KEY="$API_KEY" python3 tests/test_performance.py
```

## 💡 Adding New Tests

### Test Structure

```python
def test_new_functionality(self):
    """Test description"""
    print(f"\n{BLUE}=== Testing New Functionality ==={RESET}")
    
    try:
        # Test setup
        # Test execution
        # Assertions
        self.log_test("Test name", success_condition, error_details)
    except Exception as e:
        self.log_test("Test name", False, str(e))
```

### Best Practices

1. **Descriptive Names**: Use clear, descriptive test names
2. **Independent Tests**: Each test should be self-contained
3. **Cleanup**: Always clean up test resources
4. **Error Handling**: Catch and log exceptions properly
5. **Assertions**: Verify expected vs actual results
6. **Documentation**: Comment complex test logic

## 🎯 Continuous Integration

### CI/CD Integration

```yaml
# Example GitHub Actions workflow
name: Test S3 Storage System
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Start services
        run: docker-compose up -d
      - name: Wait for services
        run: sleep 60
      - name: Run tests
        run: |
          API_KEY=$(docker-compose logs identity-service | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //')
          API_KEY="$API_KEY" ./run_all_tests.sh
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

This comprehensive testing framework ensures the S3 Storage System works correctly under all conditions and provides confidence for production deployment!