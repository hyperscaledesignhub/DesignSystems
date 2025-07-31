#!/bin/bash

# Professional Test Runner Script
# This script runs all demos with professional testing practices

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 PROFESSIONAL TEST RUNNER${NC}"
echo "=================================="
echo "This script will:"
echo "  ✅ Clean up any existing test artifacts"
echo "  ✅ Run all demos with temporary directories"
echo "  ✅ Ensure proper test isolation"
echo "  ✅ Clean up after each test"
echo "  ✅ Provide detailed test results"
echo "=================================="
echo

# Function to cleanup existing test artifacts
cleanup_existing_artifacts() {
    echo -e "${YELLOW}🧹 Cleaning up existing test artifacts...${NC}"
    
    # Remove test-related directories
    dirs_to_clean=(
        "data"
        "demo_data"
        "automated_anti_entropy_demo_data"
        "demo_persistence_data"
        "test_data"
        "test_logs"
        "temp_test"
    )
    
    for dir in "${dirs_to_clean[@]}"; do
        if [ -d "$dir" ]; then
            echo "  Removing: $dir"
            rm -rf "$dir"
        fi
    done
    
    # Remove test log files from demo directory
    if [ -d "demo" ]; then
        find demo -name "*.log" -type f -delete 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
    echo
}

# Function to check if cluster is running
check_cluster_status() {
    echo -e "${YELLOW}🔍 Checking cluster status...${NC}"
    
    # Check if nodes are running
    local nodes=("localhost:9999" "localhost:9998" "localhost:9997")
    local healthy_nodes=0
    
    for node in "${nodes[@]}"; do
        if curl -s "http://$node/health" >/dev/null 2>&1; then
            echo "  ✅ Node $node is healthy"
            ((healthy_nodes++))
        else
            echo "  ❌ Node $node is not responding"
        fi
    done
    
    if [ $healthy_nodes -ge 2 ]; then
        echo -e "${GREEN}✅ Cluster is ready for testing${NC}"
        return 0
    else
        echo -e "${RED}❌ Cluster is not ready. Starting cluster...${NC}"
        return 1
    fi
}

# Function to start cluster if needed
start_cluster_if_needed() {
    if ! check_cluster_status; then
        echo -e "${YELLOW}🚀 Starting cluster...${NC}"
        ./scripts/start-cluster-local.sh &
        CLUSTER_PID=$!
        
        # Wait for cluster to be ready
        echo "Waiting for cluster to be ready..."
        for i in {1..30}; do
            if check_cluster_status >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Cluster is ready${NC}"
                break
            fi
            sleep 2
        done
        
        if ! check_cluster_status >/dev/null 2>&1; then
            echo -e "${RED}❌ Failed to start cluster${NC}"
            exit 1
        fi
    fi
}

# Function to run professional tests
run_professional_tests() {
    echo -e "${BLUE}🧪 Running Professional Tests${NC}"
    echo "=================================="
    
    cd demo
    
    # Run the professional test runner
    python professional_test_runner.py --config ../yaml/config-local.yaml
    
    cd ..
}

# Function to cleanup after tests
final_cleanup() {
    echo -e "${YELLOW}🧹 Final cleanup...${NC}"
    
    # Stop cluster if we started it
    if [ ! -z "$CLUSTER_PID" ]; then
        echo "Stopping cluster..."
        kill $CLUSTER_PID 2>/dev/null || true
        wait $CLUSTER_PID 2>/dev/null || true
    fi
    
    # Run global cleanup
    cd demo
    python -c "from test_utils import global_test_cleanup; global_test_cleanup()"
    cd ..
    
    echo -e "${GREEN}✅ Final cleanup completed${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting professional test execution...${NC}"
    echo
    
    # Step 1: Cleanup existing artifacts
    cleanup_existing_artifacts
    
    # Step 2: Check/start cluster
    start_cluster_if_needed
    
    # Step 3: Run professional tests
    run_professional_tests
    
    # Step 4: Final cleanup
    final_cleanup
    
    echo
    echo -e "${GREEN}🎉 Professional test execution completed!${NC}"
    echo "All tests were run with proper isolation and cleanup."
}

# Handle script interruption
trap 'echo -e "\n${RED}⚠️ Script interrupted. Cleaning up...${NC}"; final_cleanup; exit 1' INT TERM

# Run main function
main "$@" 