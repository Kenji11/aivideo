#!/bin/bash

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  AI Video Generation Pipeline Monitor${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Function to show container status
show_status() {
    echo -e "${BLUE}=== Container Status ===${NC}"
    docker-compose ps --format "table {{.Name}}\t{{.Status}}"
    echo ""
}

# Function to monitor logs
monitor_logs() {
    echo -e "${GREEN}=== Starting Live Log Monitor ===${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
    echo ""
    
    # Follow logs from all services with colors
    docker-compose logs -f --tail=50 api worker 2>&1 | while IFS= read -r line; do
        # Color code different log levels
        if echo "$line" | grep -qi "error\|exception\|failed\|fail"; then
            echo -e "${RED}$line${NC}"
        elif echo "$line" | grep -qi "warning\|warn"; then
            echo -e "${YELLOW}$line${NC}"
        elif echo "$line" | grep -qi "phase\|✅\|🚀\|💰\|📊"; then
            echo -e "${GREEN}$line${NC}"
        elif echo "$line" | grep -qi "info\|INFO"; then
            echo -e "${CYAN}$line${NC}"
        else
            echo "$line"
        fi
    done
}

# Show initial status
show_status

# Start monitoring
monitor_logs
