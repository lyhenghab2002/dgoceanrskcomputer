#!/bin/bash
# COMPLETE FRESH START - Wipe Everything and Start Clean
# Run with: sudo bash COMPLETE_FRESH_START.sh

echo "🔥 COMPLETE FRESH START - Cleaning Everything"
echo "=============================================="
echo ""
echo "⚠️  WARNING: This will remove:"
echo "   - All old Gunicorn services"
echo "   - All old Nginx configurations"
echo "   - All old processes"
echo "   - All old logs"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting cleanup..."
echo ""

# Step 1: Stop and disable all old services
echo "1. Stopping all services..."
systemctl stop gunicorn 2>/dev/null
systemctl stop nginx 2>/dev/null
systemctl disable gunicorn 2>/dev/null

# Step 2: Kill all Python/Gunicorn processes
echo "2. Killing all old processes..."
pkill -9 gunicorn
pkill -9 python3
pkill -9 python
sleep 2

# Step 3: Remove old service files
echo "3. Removing old service files..."
rm -f /etc/systemd/system/gunicorn.service
rm -f /etc/systemd/system/gunicorn*.service
systemctl daemon-reload

# Step 4: Remove old Nginx configurations
echo "4. Removing old Nginx configurations..."
rm -f /etc/nginx/sites-enabled/*
rm -f /etc/nginx/sites-available/computershop
rm -f /etc/nginx/sites-available/default

# Step 5: Remove old sockets and temp files
echo "5. Cleaning up old sockets and temp files..."
rm -f /tmp/gunicorn.sock
rm -f /tmp/*.sock

# Step 6: Clean up old logs
echo "6. Cleaning up old logs..."
rm -rf /var/log/gunicorn
mkdir -p /var/log/gunicorn

# Step 7: Remove old app directories (optional - be careful!)
echo ""
echo "⚠️  Do you want to remove the old Computer Shop directory?"
echo "   Location: /var/www/computer-shop"
read -p "Remove old app directory? (yes/no): " remove_app

if [ "$remove_app" = "yes" ]; then
    echo "Removing old app directory..."
    rm -rf /var/www/computer-shop
    rm -rf /var/www/*
fi

# Step 8: Clear cache
echo ""
echo "7. Clearing system cache..."
sync && echo 3 > /proc/sys/vm/drop_caches

# Step 9: Restart Nginx fresh
echo "8. Starting Nginx fresh..."
systemctl start nginx

echo ""
echo "=============================================="
echo "✅ CLEANUP COMPLETE!"
echo ""
echo "Your server is now CLEAN and ready for a new website!"
echo ""
echo "Next steps:"
echo "1. Upload your new website code"
echo "2. Run: sudo bash SETUP_NEW_WEBSITE.sh"
echo ""
echo "Current status:"
systemctl status nginx --no-pager | head -5
echo ""
echo "Free memory:"
free -h
echo "=============================================="

