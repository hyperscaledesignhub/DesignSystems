#!/bin/bash

# Test script for S3 Storage System API
set -e

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:7841}"
API_KEY="${API_KEY:-}"

if [ -z "$API_KEY" ]; then
    echo "❌ Please set API_KEY environment variable"
    echo "Usage: API_KEY=your_api_key ./test-api.sh"
    exit 1
fi

echo "🧪 Testing S3 Storage System API"
echo "Gateway URL: $GATEWAY_URL"
echo "API Key: ${API_KEY:0:20}..."
echo ""

# Test bucket operations
echo "📦 Testing Bucket Operations..."

echo "  Creating bucket 'test-bucket'..."
curl -s -X POST "$GATEWAY_URL/buckets" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "test-bucket"}' | jq .

echo "  Listing buckets..."
curl -s -X GET "$GATEWAY_URL/buckets" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo ""

# Test object operations
echo "📄 Testing Object Operations..."

echo "  Uploading text file..."
echo "Hello, S3 World! This is a test file." | curl -s -X PUT "$GATEWAY_URL/buckets/test-bucket/objects/hello.txt" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: text/plain" \
  --data-binary @- | jq .

echo "  Uploading JSON file..."
echo '{"message": "Hello from JSON", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' | curl -s -X PUT "$GATEWAY_URL/buckets/test-bucket/objects/data.json" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @- | jq .

echo "  Uploading file in subfolder..."
echo "This file is in a subfolder" | curl -s -X PUT "$GATEWAY_URL/buckets/test-bucket/objects/folder/subfolder/nested.txt" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: text/plain" \
  --data-binary @- | jq .

echo "  Listing all objects..."
curl -s -X GET "$GATEWAY_URL/buckets/test-bucket/objects" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo "  Listing objects with prefix 'folder/'..."
curl -s -X GET "$GATEWAY_URL/buckets/test-bucket/objects?prefix=folder/" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo "  Downloading hello.txt..."
curl -s -X GET "$GATEWAY_URL/buckets/test-bucket/objects/hello.txt" \
  -H "Authorization: Bearer $API_KEY"
echo ""

echo "  Downloading data.json..."
curl -s -X GET "$GATEWAY_URL/buckets/test-bucket/objects/data.json" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo ""

# Test error cases
echo "❌ Testing Error Cases..."

echo "  Trying to access non-existent object..."
curl -s -X GET "$GATEWAY_URL/buckets/test-bucket/objects/nonexistent.txt" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo "  Trying to access non-existent bucket..."
curl -s -X GET "$GATEWAY_URL/buckets/nonexistent-bucket/objects" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo "  Trying to create bucket with invalid name..."
curl -s -X POST "$GATEWAY_URL/buckets" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"bucket_name": "A"}' | jq .

echo ""

# Cleanup
echo "🧹 Cleanup..."

echo "  Deleting objects..."
curl -s -X DELETE "$GATEWAY_URL/buckets/test-bucket/objects/hello.txt" \
  -H "Authorization: Bearer $API_KEY"

curl -s -X DELETE "$GATEWAY_URL/buckets/test-bucket/objects/data.json" \
  -H "Authorization: Bearer $API_KEY"

curl -s -X DELETE "$GATEWAY_URL/buckets/test-bucket/objects/folder/subfolder/nested.txt" \
  -H "Authorization: Bearer $API_KEY"

echo "  Deleting bucket..."
curl -s -X DELETE "$GATEWAY_URL/buckets/test-bucket" \
  -H "Authorization: Bearer $API_KEY" | jq .

echo ""
echo "✅ API testing completed successfully!"