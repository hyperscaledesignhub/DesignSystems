#!/bin/bash

# Comprehensive Test Artifacts Cleanup Script
# This script removes all old test folders and artifacts created by previous tests

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🧹 COMPREHENSIVE TEST ARTIFACTS CLEANUP${NC}"
echo "=============================================="
echo "This script will remove all test artifacts from previous runs:"
echo "  • Test data directories"
echo "  • Demo data directories"
echo "  • Temporary test directories"
echo "  • Old log files"
echo "  • Test artifacts in project root"
echo "=============================================="
echo

# Function to safely remove directories
safe_remove_dir() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}Removing ${description}: ${dir}${NC}"
        rm -rf "$dir"
        echo -e "${GREEN}✅ Removed: ${dir}${NC}"
    else
        echo -e "${BLUE}⏭️  Skipping ${description}: ${dir} (not found)${NC}"
    fi
}

# Function to safely remove files
safe_remove_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo -e "${YELLOW}Removing ${description}: ${file}${NC}"
        rm -f "$file"
        echo -e "${GREEN}✅ Removed: ${file}${NC}"
    else
        echo -e "${BLUE}⏭️  Skipping ${description}: ${file} (not found)${NC}"
    fi
}

# Function to remove files by pattern
remove_files_by_pattern() {
    local pattern="$1"
    local description="$2"
    
    if ls $pattern 1> /dev/null 2>&1; then
        echo -e "${YELLOW}Removing ${description} files...${NC}"
        rm -f $pattern
        echo -e "${GREEN}✅ Removed ${description} files${NC}"
    else
        echo -e "${BLUE}⏭️  No ${description} files found${NC}"
    fi
}

# Function to cleanup test data directories
cleanup_test_data_dirs() {
    echo -e "${BLUE}📁 Cleaning up test data directories...${NC}"
    echo "----------------------------------------------"
    
    # Common test data directories
    test_dirs=(
        "data"
        "demo_data"
        "automated_anti_entropy_demo_data"
        "demo_persistence_data"
        "test_data"
        "test_logs"
        "temp_test"
        "test_artifacts"
        "test_results"
        "test_output"
        "test_cache"
        "test_temp"
    )
    
    for dir in "${test_dirs[@]}"; do
        safe_remove_dir "$dir" "test data directory"
    done
    
    echo
}

# Function to cleanup demo-specific directories
cleanup_demo_dirs() {
    echo -e "${BLUE}🎬 Cleaning up demo-specific directories...${NC}"
    echo "----------------------------------------------"
    
    # Demo-specific directories that might have been created
    demo_dirs=(
        "vector_clock_demo_data"
        "convergence_demo_data"
        "anti_entropy_demo_data"
        "consistent_hashing_demo_data"
        "replication_demo_data"
        "persistence_demo_data"
        "causal_consistency_demo_data"
        "merkle_demo_data"
        "gossip_demo_data"
        "hash_ring_demo_data"
    )
    
    for dir in "${demo_dirs[@]}"; do
        safe_remove_dir "$dir" "demo data directory"
    done
    
    echo
}

# Function to cleanup temporary directories
cleanup_temp_dirs() {
    echo -e "${BLUE}🗂️  Cleaning up temporary directories...${NC}"
    echo "----------------------------------------------"
    
    # Find and remove temporary test directories
    if [ -d "/tmp" ]; then
        echo -e "${YELLOW}Searching for temporary test directories...${NC}"
        
        # Find temporary directories created by our tests
        temp_dirs=$(find /tmp -maxdepth 1 -name "test_demo_*" -type d 2>/dev/null || true)
        
        if [ -n "$temp_dirs" ]; then
            echo -e "${YELLOW}Found temporary test directories:${NC}"
            echo "$temp_dirs"
            echo -e "${YELLOW}Removing temporary test directories...${NC}"
            find /tmp -maxdepth 1 -name "test_demo_*" -type d -exec rm -rf {} \; 2>/dev/null || true
            echo -e "${GREEN}✅ Removed temporary test directories${NC}"
        else
            echo -e "${BLUE}⏭️  No temporary test directories found${NC}"
        fi
    fi
    
    echo
}

# Function to cleanup log files
cleanup_log_files() {
    echo -e "${BLUE}📝 Cleaning up test log files...${NC}"
    echo "----------------------------------------------"
    
    # Remove test log files from demo directory
    if [ -d "demo" ]; then
        echo -e "${YELLOW}Cleaning up demo directory log files...${NC}"
        remove_files_by_pattern "demo/*.log" "demo log"
        remove_files_by_pattern "demo/*_demo_*.log" "demo-specific log"
    fi
    
    # Remove test log files from root directory
    echo -e "${YELLOW}Cleaning up root directory test log files...${NC}"
    remove_files_by_pattern "node*.log" "node log"
    remove_files_by_pattern "*_restart.log" "restart log"
    remove_files_by_pattern "test_*.log" "test log"
    remove_files_by_pattern "*_demo_*.log" "demo log"
    
    # Remove any other test-related log files
    remove_files_by_pattern "*test*.log" "test-related log"
    remove_files_by_pattern "*demo*.log" "demo-related log"
    
    echo
}

# Function to cleanup cache and temporary files
cleanup_cache_files() {
    echo -e "${BLUE}🗑️  Cleaning up cache and temporary files...${NC}"
    echo "----------------------------------------------"
    
    # Remove Python cache directories
    if [ -d "demo" ]; then
        safe_remove_dir "demo/__pycache__" "Python cache directory"
    fi
    
    if [ -d "distributed" ]; then
        safe_remove_dir "distributed/__pycache__" "Python cache directory"
    fi
    
    # Remove any .pyc files
    remove_files_by_pattern "**/*.pyc" "Python compiled file"
    remove_files_by_pattern "**/*.pyo" "Python optimized file"
    
    # Remove any temporary files
    remove_files_by_pattern "**/*.tmp" "temporary file"
    remove_files_by_pattern "**/*.temp" "temporary file"
    
    echo
}

# Function to cleanup any remaining artifacts
cleanup_remaining_artifacts() {
    echo -e "${BLUE}🔍 Cleaning up any remaining artifacts...${NC}"
    echo "----------------------------------------------"
    
    # Remove any files with test-related names
    test_files=(
        "test_results.json"
        "test_output.txt"
        "test_artifacts.zip"
        "demo_results.json"
        "demo_output.txt"
        "test_coverage.xml"
        "test_report.html"
    )
    
    for file in "${test_files[@]}"; do
        safe_remove_file "$file" "test artifact file"
    done
    
    # Remove any directories that might have been created with timestamps
    if [ -d "." ]; then
        echo -e "${YELLOW}Searching for timestamped test directories...${NC}"
        timestamp_dirs=$(find . -maxdepth 1 -name "*_2025*" -type d 2>/dev/null || true)
        
        if [ -n "$timestamp_dirs" ]; then
            echo -e "${YELLOW}Found timestamped directories:${NC}"
            echo "$timestamp_dirs"
            echo -e "${YELLOW}Removing timestamped directories...${NC}"
            find . -maxdepth 1 -name "*_2025*" -type d -exec rm -rf {} \; 2>/dev/null || true
            echo -e "${GREEN}✅ Removed timestamped directories${NC}"
        else
            echo -e "${BLUE}⏭️  No timestamped directories found${NC}"
        fi
    fi
    
    echo
}

# Function to verify cleanup
verify_cleanup() {
    echo -e "${BLUE}🔍 Verifying cleanup...${NC}"
    echo "----------------------------------------------"
    
    # Check if any test directories still exist
    remaining_dirs=()
    
    for dir in "data" "demo_data" "automated_anti_entropy_demo_data" "test_data" "test_logs"; do
        if [ -d "$dir" ]; then
            remaining_dirs+=("$dir")
        fi
    done
    
    if [ ${#remaining_dirs[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All test directories successfully removed${NC}"
    else
        echo -e "${RED}❌ Some test directories still exist:${NC}"
        for dir in "${remaining_dirs[@]}"; do
            echo -e "${RED}   - ${dir}${NC}"
        done
    fi
    
    # Check if any test log files still exist
    remaining_logs=$(find . -name "*.log" -path "*/demo/*" 2>/dev/null | head -5 || true)
    
    if [ -z "$remaining_logs" ]; then
        echo -e "${GREEN}✅ All test log files successfully removed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some test log files still exist:${NC}"
        echo "$remaining_logs"
    fi
    
    echo
}

# Function to show disk usage before and after
show_disk_usage() {
    echo -e "${BLUE}💾 Disk usage information...${NC}"
    echo "----------------------------------------------"
    
    if command -v du >/dev/null 2>&1; then
        current_usage=$(du -sh . 2>/dev/null | cut -f1 || echo "unknown")
        echo -e "${BLUE}Current directory size: ${current_usage}${NC}"
    fi
    
    echo
}

# Main cleanup function
main_cleanup() {
    echo -e "${BLUE}Starting comprehensive test artifacts cleanup...${NC}"
    echo
    
    # Show initial disk usage
    show_disk_usage
    
    # Perform all cleanup operations
    cleanup_test_data_dirs
    cleanup_demo_dirs
    cleanup_temp_dirs
    cleanup_log_files
    cleanup_cache_files
    cleanup_remaining_artifacts
    
    # Verify cleanup
    verify_cleanup
    
    # Show final disk usage
    show_disk_usage
    
    echo -e "${GREEN}🎉 COMPREHENSIVE CLEANUP COMPLETED!${NC}"
    echo "=============================================="
    echo "All test artifacts have been removed:"
    echo "  ✅ Test data directories"
    echo "  ✅ Demo data directories"
    echo "  ✅ Temporary directories"
    echo "  ✅ Test log files"
    echo "  ✅ Cache files"
    echo "  ✅ Remaining artifacts"
    echo ""
    echo "Your project is now clean and ready for professional testing!"
    echo ""
}

# Handle script interruption
trap 'echo -e "\n${RED}⚠️ Cleanup interrupted. Some files may not have been removed.${NC}"; exit 1' INT TERM

# Run main cleanup
main_cleanup 