#!/bin/bash
# Server Health Check Script
# Run with: bash check_server_health.sh

echo "🔍 Computer Shop Server Health Check"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get total RAM in MB
TOTAL_RAM=$(free -m | awk 'NR==2{print $2}')
USED_RAM=$(free -m | awk 'NR==2{print $3}')
RAM_PERCENT=$(awk "BEGIN {printf \"%.0f\", ($USED_RAM/$TOTAL_RAM)*100}")

# Get CPU load
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')

# Get disk usage
DISK_USAGE=$(df -h / | awk 'NR==2{print $5}' | sed 's/%//')

# Get swap usage
SWAP_TOTAL=$(free -m | awk 'NR==3{print $2}')
SWAP_USED=$(free -m | awk 'NR==3{print $3}')

echo "1. MEMORY CHECK"
echo "---------------"
echo "Total RAM: ${TOTAL_RAM}MB"
echo "Used RAM: ${USED_RAM}MB (${RAM_PERCENT}%)"
if [ $RAM_PERCENT -gt 90 ]; then
    echo -e "${RED}⚠️  CRITICAL: Memory usage very high!${NC}"
elif [ $RAM_PERCENT -gt 75 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Memory usage high${NC}"
else
    echo -e "${GREEN}✅ Memory usage OK${NC}"
fi
echo ""

echo "2. SWAP CHECK"
echo "-------------"
if [ $SWAP_TOTAL -eq 0 ]; then
    echo -e "${RED}❌ No swap configured!${NC}"
    echo "Run: sudo bash emergency_fix.sh to add swap"
else
    echo "Swap Total: ${SWAP_TOTAL}MB"
    echo "Swap Used: ${SWAP_USED}MB"
    echo -e "${GREEN}✅ Swap configured${NC}"
fi
echo ""

echo "3. DISK USAGE CHECK"
echo "-------------------"
echo "Disk usage: ${DISK_USAGE}%"
if [ $DISK_USAGE -gt 90 ]; then
    echo -e "${RED}⚠️  CRITICAL: Disk almost full!${NC}"
elif [ $DISK_USAGE -gt 80 ]; then
    echo -e "${YELLOW}⚠️  WARNING: Disk usage high${NC}"
else
    echo -e "${GREEN}✅ Disk usage OK${NC}"
fi
echo ""

echo "4. CPU LOAD CHECK"
echo "-----------------"
echo "Current load: $CPU_LOAD"
# Load average interpretation depends on CPU cores
CORES=$(nproc)
echo "CPU cores: $CORES"
echo ""

echo "5. SERVICE STATUS"
echo "-----------------"
# Check MySQL
if systemctl is-active --quiet mysql; then
    echo -e "${GREEN}✅ MySQL: Running${NC}"
else
    echo -e "${RED}❌ MySQL: Stopped${NC}"
fi

# Check Gunicorn
if systemctl is-active --quiet gunicorn; then
    echo -e "${GREEN}✅ Gunicorn: Running${NC}"
else
    echo -e "${RED}❌ Gunicorn: Stopped${NC}"
fi

# Check Nginx
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx: Running${NC}"
else
    echo -e "${RED}❌ Nginx: Stopped${NC}"
fi
echo ""

echo "6. TOP MEMORY CONSUMERS"
echo "-----------------------"
ps aux --sort=-%mem | head -6 | awk 'NR>1{printf "%-20s %6s%%\n", substr($11,1,20), $4}'
echo ""

echo "7. TOP CPU CONSUMERS"
echo "--------------------"
ps aux --sort=-%cpu | head -6 | awk 'NR>1{printf "%-20s %6s%%\n", substr($11,1,20), $3}'
echo ""

echo "8. NETWORK CHECK"
echo "----------------"
# Check if we can reach the internet
if ping -c 1 8.8.8.8 &> /dev/null; then
    echo -e "${GREEN}✅ Internet connectivity: OK${NC}"
else
    echo -e "${RED}❌ Internet connectivity: Failed${NC}"
fi
echo ""

echo "9. RECENT ERRORS (Last 10)"
echo "---------------------------"
if [ -f /var/log/gunicorn/error.log ]; then
    echo "Gunicorn errors:"
    tail -3 /var/log/gunicorn/error.log 2>/dev/null || echo "No errors"
fi
echo ""

echo "======================================"
echo "RECOMMENDATIONS:"
echo ""

# Provide recommendations based on findings
if [ $TOTAL_RAM -lt 2048 ]; then
    echo -e "${YELLOW}💡 Your server has only ${TOTAL_RAM}MB RAM"
    echo "   Consider upgrading to at least 2GB ($12/month)${NC}"
    echo ""
fi

if [ $SWAP_TOTAL -eq 0 ]; then
    echo -e "${RED}💡 No swap file detected"
    echo "   Run: sudo bash emergency_fix.sh${NC}"
    echo ""
fi

if [ $RAM_PERCENT -gt 75 ]; then
    echo -e "${YELLOW}💡 High memory usage detected"
    echo "   Run: sudo bash emergency_fix.sh${NC}"
    echo ""
fi

# Check if Gunicorn is running with optimal settings
if systemctl is-active --quiet gunicorn; then
    WORKERS=$(ps aux | grep gunicorn | grep -c worker)
    echo "Current Gunicorn workers: $WORKERS"
    RECOMMENDED_WORKERS=$(( (CORES * 2) + 1 ))
    if [ $TOTAL_RAM -lt 2048 ]; then
        RECOMMENDED_WORKERS=2
    fi
    echo "Recommended workers for your server: $RECOMMENDED_WORKERS"
    echo ""
fi

echo "For detailed fixes, see:"
echo "  - QUICK_FIX_COMMANDS.md"
echo "  - DIGITALOCEAN_SERVER_FIX.md"
echo ""
echo "To monitor in real-time: htop"

