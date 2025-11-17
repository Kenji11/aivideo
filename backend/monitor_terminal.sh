#!/bin/bash

# Real-time monitoring script for video generation pipeline
# Shows API and Worker logs with color coding

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     AI Video Generation Pipeline - Live Monitor                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Monitoring API and Worker logs...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Follow logs with color coding
docker-compose logs -f --tail=50 api worker 2>&1 | while IFS= read -r line; do
    # Phase markers
    if echo "$line" | grep -qi "phase 1\|phase1\|validation"; then
        echo -e "${CYAN}▶ ${line}${NC}"
    elif echo "$line" | grep -qi "phase 2\|phase2\|storyboard"; then
        echo -e "${MAGENTA}▶ ${line}${NC}"
    elif echo "$line" | grep -qi "phase 4\|phase4\|chunk"; then
        echo -e "${BLUE}▶ ${line}${NC}"
    elif echo "$line" | grep -qi "phase 5\|phase5\|refine"; then
        echo -e "${GREEN}▶ ${line}${NC}"
    # Success markers
    elif echo "$line" | grep -qi "✅\|success\|completed\|complete"; then
        echo -e "${GREEN}✓ ${line}${NC}"
    # Error markers
    elif echo "$line" | grep -qi "❌\|error\|exception\|failed\|fail\|ERROR"; then
        echo -e "${RED}✗ ${line}${NC}"
    # Warning markers
    elif echo "$line" | grep -qi "⚠️\|warning\|warn\|WARNING"; then
        echo -e "${YELLOW}⚠ ${line}${NC}"
    # Cost/Progress markers
    elif echo "$line" | grep -qi "💰\|cost\|💵"; then
        echo -e "${YELLOW}💰 ${line}${NC}"
    elif echo "$line" | grep -qi "📊\|progress\|%"; then
        echo -e "${CYAN}📊 ${line}${NC}"
    # Info markers
    elif echo "$line" | grep -qi "🚀\|starting\|INFO"; then
        echo -e "${CYAN}ℹ ${line}${NC}"
    # Default
    else
        echo "$line"
    fi
done
