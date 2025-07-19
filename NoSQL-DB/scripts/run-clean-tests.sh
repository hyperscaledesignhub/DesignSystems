#!/bin/bash

# Clean Test Runner Script
# This script automatically cleans up old test artifacts before running tests with professional practices

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🚀 CLEAN TEST RUNNER${NC}"
echo "=============================================="
echo "This script will:"
echo "  1. 🧹 Clean up all old test artifacts"
echo "  2. 🎬 Run tests with professional practices"
echo "  3. ✅ Ensure clean test environment"
echo "=============================================="
echo

# Function to run cleanup
run_cleanup() {
    echo -e "${YELLOW}🧹 STEP 1: CLEANING UP OLD TEST ARTIFACTS${NC}"
    echo "=============================================="
    
    if [ -f "./scripts/cleanup-test-artifacts.sh" ]; then
        ./scripts/cleanup-test-artifacts.sh
    else
        echo -e "${RED}❌ Cleanup script not found: ./scripts/cleanup-test-artifacts.sh${NC}"
        echo "Performing basic cleanup..."
        
        # Basic cleanup if script not found
        rm -rf data demo_data automated_anti_entropy_demo_data demo_persistence_data test_data test_logs 2>/dev/null || true
        rm -f demo/*.log node*.log *_restart.log test_*.log *_demo_*.log 2>/dev/null || true
        rm -rf demo/__pycache__ distributed/__pycache__ 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        
        echo -e "${GREEN}✅ Basic cleanup completed${NC}"
    fi
    
    echo
}

# Function to check cluster status
check_cluster_status() {
    echo -e "${YELLOW}🔍 STEP 2: CHECKING CLUSTER STATUS${NC}"
    echo "=============================================="
    
    # Check if nodes are running
    local nodes=("localhost:9999" "localhost:10000" "localhost:10001")
    local healthy_nodes=0
    
    for node in "${nodes[@]}"; do
        if curl -s "http://$node/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Node $node is healthy${NC}"
            ((healthy_nodes++))
        else
            echo -e "${RED}❌ Node $node is not responding${NC}"
        fi
    done
    
    if [ $healthy_nodes -ge 2 ]; then
        echo -e "${GREEN}✅ Cluster is ready for testing${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ Cluster is not ready. Starting cluster...${NC}"
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

# Function to run tests with professional practices
run_professional_tests() {
    echo -e "${YELLOW}🎬 STEP 3: RUNNING TESTS WITH PROFESSIONAL PRACTICES${NC}"
    echo "=============================================="
    
    # Get demo name from arguments
    local demo_name="$1"
    local config_file="${2:-yaml/config-local.yaml}"
    local use_existing="${3:-true}"
    
    if [ -z "$demo_name" ]; then
        echo -e "${RED}❌ Demo name is required${NC}"
        echo "Usage: $0 <demo_name> [config_file] [use_existing]"
        echo ""
        echo "Available demos:"
        cd demo
        python cluster_demo_runner_local.py --list-demos
        cd ..
        exit 1
    fi
    
    echo -e "${BLUE}Running demo: ${demo_name}${NC}"
    echo -e "${BLUE}Config file: ${config_file}${NC}"
    echo -e "${BLUE}Mode: ${use_existing}${NC}"
    echo ""
    
    cd demo
    
    # Run the demo with professional practices
    if [ "$use_existing" = "true" ]; then
        python cluster_demo_runner_local.py "$demo_name" --config "../$config_file" --use-existing --professional
    else
        python cluster_demo_runner_local.py "$demo_name" --config "../$config_file" --professional
    fi
    
    cd ..
}

# Function to show available demos
show_available_demos() {
    echo -e "${BLUE}📋 AVAILABLE DEMOS${NC}"
    echo "=============================================="
    cd demo
    python cluster_demo_runner_local.py --list-demos
    cd ..
    echo ""
}

# Function to cleanup after tests
final_cleanup() {
    echo -e "${YELLOW}🧹 STEP 4: FINAL CLEANUP${NC}"
    echo "=============================================="
    
    # Stop cluster if we started it
    if [ ! -z "$CLUSTER_PID" ]; then
        echo "Stopping cluster..."
        kill $CLUSTER_PID 2>/dev/null || true
        wait $CLUSTER_PID 2>/dev/null || true
    fi
    
    # Run global cleanup from test_utils
    cd demo
    python -c "from test_utils import global_test_cleanup; global_test_cleanup()" 2>/dev/null || true
    cd ..
    
    echo -e "${GREEN}✅ Final cleanup completed${NC}"
}

# Function to show usage
show_usage() {
    echo -e "${BLUE}USAGE: $0 <demo_name> [config_file] [use_existing]${NC}"
    echo ""
    echo "Arguments:"
    echo "  demo_name     - Name of the demo to run (required)"
    echo "  config_file   - Configuration file (default: yaml/config-local.yaml)"
    echo "  use_existing  - Use existing cluster (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0 vector_clock_db"
    echo "  $0 convergence yaml/config.yaml true"
    echo "  $0 anti_entropy yaml/config-local.yaml false"
    echo ""
    echo "Available demos:"
    show_available_demos
}

# Main execution
main() {
    # Check if help is requested
    if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ "$1" = "help" ]; then
        show_usage
        return
    fi
    
    # Check if list demos is requested
    if [ "$1" = "--list" ] || [ "$1" = "list" ]; then
        show_available_demos
        return
    fi
    
    echo -e "${BLUE}Starting clean test execution...${NC}"
    echo
    
    # Step 1: Clean up old artifacts
    run_cleanup
    
    # Step 2: Check/start cluster
    start_cluster_if_needed
    
    # Step 3: Run tests with professional practices
    run_professional_tests "$1" "$2" "$3"
    
    # Step 4: Final cleanup
    final_cleanup
    
    echo
    echo -e "${GREEN}🎉 CLEAN TEST EXECUTION COMPLETED!${NC}"
    echo "=============================================="
    echo "✅ All old artifacts cleaned up"
    echo "✅ Tests run with professional practices"
    echo "✅ Temporary directories automatically cleaned"
    echo "✅ All logs saved to logs/ folder"
    echo "✅ Project remains clean"
    echo ""
}

# Handle script interruption
trap 'echo -e "\n${RED}⚠️ Script interrupted. Performing cleanup...${NC}"; final_cleanup; exit 1' INT TERM

# Run main function with all arguments
main "$@" 