#!/bin/bash
# Fix Nginx 404 Error - Connect Nginx to Gunicorn
# Run with: sudo bash fix_nginx_404.sh

echo "🔧 Fixing Nginx 404 Error..."
echo "=============================="

# Detect app directory
if [ -d "/var/www/computer-shop" ]; then
    APP_DIR="/var/www/computer-shop"
elif [ -d "/root/dgoceanrskcomputer" ]; then
    APP_DIR="/root/dgoceanrskcomputer"
else
    APP_DIR="/var/www/computer-shop"
fi

echo "App directory: $APP_DIR"
echo ""

# Check if Gunicorn socket exists
echo "Checking Gunicorn socket..."
if [ -S /tmp/gunicorn.sock ]; then
    echo "✅ Gunicorn socket exists"
    ls -la /tmp/gunicorn.sock
else
    echo "❌ Gunicorn socket not found!"
    echo "Creating it by restarting Gunicorn..."
    systemctl restart gunicorn
    sleep 3
fi
echo ""

# Backup existing nginx config
echo "Backing up existing Nginx config..."
cp /etc/nginx/sites-available/computershop /etc/nginx/sites-available/computershop.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true

# Create new working Nginx config
echo "Creating new Nginx configuration..."
cat > /etc/nginx/sites-available/computershop << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    # Timeouts
    client_body_timeout 120s;
    client_header_timeout 120s;
    keepalive_timeout 65s;
    send_timeout 120s;
    
    # Upload size
    client_max_body_size 16M;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
    
    # Static files
    location /static/ {
        alias $APP_DIR/static/;
        expires 7d;
        add_header Cache-Control "public";
        access_log off;
    }
    
    # Root location - proxy to Gunicorn
    location / {
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
EOF

echo "✅ Nginx config created"
echo ""

# Remove default site
echo "Removing default Nginx site..."
rm -f /etc/nginx/sites-enabled/default

# Enable our site
echo "Enabling Computer Shop site..."
ln -sf /etc/nginx/sites-available/computershop /etc/nginx/sites-enabled/

# Test Nginx configuration
echo ""
echo "Testing Nginx configuration..."
nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx configuration is valid"
    echo ""
    
    # Restart Nginx
    echo "Restarting Nginx..."
    systemctl restart nginx
    sleep 2
    
    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx restarted successfully"
    else
        echo "❌ Nginx failed to start"
        systemctl status nginx --no-pager
    fi
else
    echo "❌ Nginx configuration has errors!"
    echo "Please check the configuration manually"
    exit 1
fi

echo ""
echo "=============================="
echo "Testing connection..."
echo ""

# Test if socket is responsive
if [ -S /tmp/gunicorn.sock ]; then
    echo "Testing Gunicorn socket response..."
    curl --unix-socket /tmp/gunicorn.sock http://localhost/ -I 2>/dev/null | head -5
fi

echo ""
echo "Testing HTTP response..."
curl -I http://localhost 2>/dev/null | head -10

echo ""
echo "=============================="
echo "✅ Fix applied!"
echo ""
echo "Now test in your browser:"
echo "  http://152.42.227.254"
echo ""
echo "If still showing 404, check:"
echo "  sudo tail -50 /var/log/nginx/error.log"
echo "  sudo journalctl -u gunicorn -n 50"
echo "=============================="

