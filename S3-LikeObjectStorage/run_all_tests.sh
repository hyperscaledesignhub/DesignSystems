#!/bin/bash

# Automated test runner for S3 Storage System
# Runs all test suites and generates comprehensive report

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
GATEWAY_URL="${GATEWAY_URL:-http://localhost:7841}"
TESTS_DIR="$(dirname "$0")/tests"
RESULTS_DIR="$(dirname "$0")/test_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}S3 Storage System - Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Gateway URL: $GATEWAY_URL"
echo "Results Directory: $RESULTS_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Check if Python dependencies are available
check_dependencies() {
    echo -e "${BLUE}Checking dependencies...${NC}"
    
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not found${NC}"
        exit 1
    fi
    
    python3 -c "import requests" 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Installing requests module...${NC}"
        pip3 install requests
    }
    
    echo -e "${GREEN}✅ Dependencies OK${NC}"
    echo ""
}

# Check if services are running
check_services() {
    echo -e "${BLUE}Checking service availability...${NC}"
    
    # Check API Gateway
    if curl -s "$GATEWAY_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API Gateway available at $GATEWAY_URL${NC}"
    else
        echo -e "${RED}❌ API Gateway not reachable at $GATEWAY_URL${NC}"
        echo "Please start the services first:"
        echo "  Docker Compose: docker-compose up -d"
        echo "  Kubernetes: kubectl get pods -n s3-storage"
        exit 1
    fi
    
    # Check individual services (if running locally)
    SERVICES=("identity:7851" "bucket:7861" "object:7871" "storage:7881" "metadata:7891")
    for service in "${SERVICES[@]}"; do
        name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name service available${NC}"
        else
            echo -e "${YELLOW}⚠️  $name service not reachable directly (may be behind gateway)${NC}"
        fi
    done
    
    echo ""
}

# Get API key from identity service
get_api_key() {
    echo -e "${BLUE}Getting API key...${NC}"
    
    # Try to get API key from environment
    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✅ Using API key from environment${NC}"
        return 0
    fi
    
    # Try to get from identity service logs (Docker Compose)
    if command -v docker-compose &> /dev/null; then
        API_KEY=$(docker-compose logs identity-service 2>/dev/null | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //' || echo "")
        if [ -n "$API_KEY" ]; then
            export API_KEY
            echo -e "${GREEN}✅ Retrieved API key from Docker Compose logs${NC}"
            return 0
        fi
    fi
    
    # Try to get from Kubernetes logs
    if command -v kubectl &> /dev/null; then
        API_KEY=$(kubectl logs -n s3-storage -l app=identity-service 2>/dev/null | grep "Admin API Key" | tail -1 | sed 's/.*Admin API Key: //' || echo "")
        if [ -n "$API_KEY" ]; then
            export API_KEY
            echo -e "${GREEN}✅ Retrieved API key from Kubernetes logs${NC}"
            return 0
        fi
    fi
    
    # Try to create a new user via API
    echo -e "${YELLOW}⚠️  Attempting to create test user...${NC}"
    TEMP_USER_ID="test-runner-$(date +%s)"
    
    # This might fail if identity service requires auth, but worth trying
    API_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/../:7851/users" \
        -H "Content-Type: application/json" \
        -d "{\"user_id\": \"$TEMP_USER_ID\"}" 2>/dev/null || echo "")
    
    if [ -n "$API_RESPONSE" ]; then
        API_KEY=$(echo "$API_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('api_key', ''))" 2>/dev/null || echo "")
        if [ -n "$API_KEY" ]; then
            export API_KEY
            echo -e "${GREEN}✅ Created test user and got API key${NC}"
            return 0
        fi
    fi
    
    echo -e "${RED}❌ Could not obtain API key${NC}"
    echo "Please set the API_KEY environment variable:"
    echo "  export API_KEY=your_api_key_here"
    echo "Or check the identity service logs for the admin API key."
    exit 1
}

# Run a test suite
run_test_suite() {
    local test_name="$1"
    local test_script="$2"
    local result_file="$RESULTS_DIR/${test_name}_${TIMESTAMP}.txt"
    
    echo -e "${BLUE}Running $test_name...${NC}"
    
    if [ ! -f "$test_script" ]; then
        echo -e "${RED}❌ Test script not found: $test_script${NC}"
        return 1
    fi
    
    # Run test and capture output
    if API_KEY="$API_KEY" GATEWAY_URL="$GATEWAY_URL" python3 "$test_script" > "$result_file" 2>&1; then
        echo -e "${GREEN}✅ $test_name PASSED${NC}"
        # Show summary from output
        grep -E "(Test Summary|Success Rate|Duration)" "$result_file" | while read line; do
            echo "   $line"
        done
        return 0
    else
        echo -e "${RED}❌ $test_name FAILED${NC}"
        # Show last few lines of output
        echo "   Last few lines of output:"
        tail -5 "$result_file" | sed 's/^/   /'
        return 1
    fi
}

# Generate HTML report
generate_html_report() {
    local html_file="$RESULTS_DIR/test_report_${TIMESTAMP}.html"
    
    echo -e "${BLUE}Generating HTML report...${NC}"
    
    cat > "$html_file" << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>S3 Storage System Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f4f4f4; padding: 20px; border-radius: 5px; }
        .test-section { margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }
        .test-header { background: #e9e9e9; padding: 10px; font-weight: bold; }
        .test-content { padding: 15px; }
        .pass { color: green; }
        .fail { color: red; }
        .warning { color: orange; }
        pre { background: #f8f8f8; padding: 10px; border-radius: 3px; overflow-x: auto; }
        .summary { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>S3 Storage System Test Report</h1>
        <p><strong>Generated:</strong> TIMESTAMP_PLACEHOLDER</p>
        <p><strong>Gateway URL:</strong> GATEWAY_URL_PLACEHOLDER</p>
    </div>
EOF

    # Add timestamp and URL
    sed -i.bak "s/TIMESTAMP_PLACEHOLDER/$(date)/" "$html_file"
    sed -i.bak "s/GATEWAY_URL_PLACEHOLDER/$GATEWAY_URL/" "$html_file"
    rm "$html_file.bak" 2>/dev/null || true
    
    # Add test results
    for result_file in "$RESULTS_DIR"/*_${TIMESTAMP}.txt; do
        if [ -f "$result_file" ]; then
            test_name=$(basename "$result_file" | sed "s/_${TIMESTAMP}.txt//")
            
            echo "    <div class=\"test-section\">" >> "$html_file"
            echo "        <div class=\"test-header\">$test_name</div>" >> "$html_file"
            echo "        <div class=\"test-content\">" >> "$html_file"
            echo "            <pre>" >> "$html_file"
            cat "$result_file" >> "$html_file"
            echo "            </pre>" >> "$html_file"
            echo "        </div>" >> "$html_file"
            echo "    </div>" >> "$html_file"
        fi
    done
    
    echo "</body></html>" >> "$html_file"
    
    echo -e "${GREEN}✅ HTML report generated: $html_file${NC}"
}

# Main execution
main() {
    echo "Starting test execution..."
    echo ""
    
    check_dependencies
    check_services
    get_api_key
    
    echo -e "${BLUE}Starting test suites...${NC}"
    echo ""
    
    # Track overall results
    total_tests=0
    passed_tests=0
    
    # Test suites to run
    declare -A test_suites=(
        ["Individual Services"]="$TESTS_DIR/test_individual_services.py"
        ["Comprehensive API Tests"]="$TESTS_DIR/test_all.py"
        ["Performance Tests"]="$TESTS_DIR/test_performance.py"
    )
    
    # Run each test suite
    for test_name in "${!test_suites[@]}"; do
        total_tests=$((total_tests + 1))
        
        if run_test_suite "$test_name" "${test_suites[$test_name]}"; then
            passed_tests=$((passed_tests + 1))
        fi
        echo ""
    done
    
    # Generate reports
    generate_html_report
    
    # Final summary
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Final Test Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo "Total Test Suites: $total_tests"
    echo "Passed: $passed_tests"
    echo "Failed: $((total_tests - passed_tests))"
    echo "Success Rate: $(( passed_tests * 100 / total_tests ))%"
    echo ""
    echo "Detailed results saved in: $RESULTS_DIR"
    echo ""
    
    if [ $passed_tests -eq $total_tests ]; then
        echo -e "${GREEN}🎉 All test suites passed!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Some test suites failed. Check the results for details.${NC}"
        exit 1
    fi
}

# Handle script interruption
trap 'echo -e "\n${YELLOW}Test execution interrupted${NC}"; exit 130' INT TERM

# Run main function
main "$@"