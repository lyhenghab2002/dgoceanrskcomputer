#!/bin/bash
# Emergency Server Fix Script for DigitalOcean
# Run this with: sudo bash emergency_fix.sh

echo "🚨 Emergency Server Fix Starting..."
echo "=================================="

# Step 1: Check current status
echo ""
echo "Step 1: Checking system status..."
echo "Free memory:"
free -h
echo ""
echo "Disk space:"
df -h
echo ""
echo "System load:"
uptime
echo ""

# Step 2: Kill hung processes
echo "Step 2: Stopping hung Python processes..."
pkill -9 python3
sleep 2

# Step 3: Restart services
echo ""
echo "Step 3: Restarting MySQL..."
systemctl restart mysql
sleep 5

echo "Restarting Gunicorn..."
systemctl restart gunicorn
sleep 3

echo "Restarting Nginx..."
systemctl restart nginx
sleep 2

# Step 4: Clear cache
echo ""
echo "Step 4: Clearing system cache..."
sync && echo 3 > /proc/sys/vm/drop_caches

# Step 5: Check if swap exists, if not create it
echo ""
echo "Step 5: Checking swap..."
if [ $(swapon --show | wc -l) -eq 0 ]; then
    echo "No swap found. Creating 2GB swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap created successfully"
else
    echo "✅ Swap already exists"
    swapon --show
fi

# Step 6: Check service status
echo ""
echo "Step 6: Checking service status..."
echo ""
echo "MySQL Status:"
systemctl status mysql --no-pager | head -10
echo ""
echo "Gunicorn Status:"
systemctl status gunicorn --no-pager | head -10
echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager | head -10

# Step 7: Final system check
echo ""
echo "Step 7: Final system check..."
echo "Memory usage:"
free -h
echo ""
echo "Top processes by memory:"
ps aux --sort=-%mem | head -10

echo ""
echo "=================================="
echo "✅ Emergency fix completed!"
echo ""
echo "Next steps:"
echo "1. Test your website in a browser"
echo "2. Check logs: sudo tail -f /var/log/gunicorn/error.log"
echo "3. Monitor with: htop"
echo "4. If still slow, consider upgrading your droplet"
echo ""
echo "For detailed instructions, see DIGITALOCEAN_SERVER_FIX.md"

