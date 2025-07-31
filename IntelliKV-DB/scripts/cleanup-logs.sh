#!/bin/bash

# Cleanup script for centralized logging
# This script removes old log files from the root directory and ensures the logs folder exists

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🧹 Cleaning up log files${NC}"
echo "=========================="

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo -e "${GREEN}Creating logs directory...${NC}"
    mkdir -p logs
fi

# Remove old log files from root directory
echo -e "${YELLOW}Removing old log files from root directory...${NC}"

# List of common log files to remove
log_files=(
    "node1.log"
    "node2.log" 
    "node3.log"
    "node1_restart.log"
    "node2_restart.log"
    "node3_restart.log"
    "*.log"
)

for log_file in "${log_files[@]}"; do
    if ls $log_file 1> /dev/null 2>&1; then
        echo "Removing: $log_file"
        rm -f $log_file
    fi
done

echo -e "${GREEN}✅ Log cleanup complete!${NC}"
echo ""
echo -e "${BLUE}📁 Log files will now be stored in the 'logs' folder${NC}"
echo "The centralized logging system will automatically:"
echo "  • Create timestamped log files for each node"
echo "  • Rotate logs when they get too large"
echo "  • Separate error logs from regular logs"
echo "  • Use proper log formatting with timestamps"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  • All logs: ls -la logs/"
echo "  • Node logs: ls -la logs/db-node-*.log"
echo "  • Error logs: ls -la logs/db-node-*_error.log"
echo "  • Follow logs: tail -f logs/db-node-1_*.log" 