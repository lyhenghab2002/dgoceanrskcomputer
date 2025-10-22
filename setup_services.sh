#!/bin/bash
# Setup Gunicorn and Nginx services for Computer Shop
# Run with: sudo bash setup_services.sh

echo "🔧 Setting up Computer Shop services..."
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get current directory
CURRENT_DIR=$(pwd)
echo "Current directory: $CURRENT_DIR"
echo ""

# Detect app directory - try common locations
if [ -d "/root/dgoceanrskcomputer" ]; then
    APP_DIR="/root/dgoceanrskcomputer"
elif [ -d "/home/*/dgoceanrskcomputer" ]; then
    APP_DIR=$(ls -d /home/*/dgoceanrskcomputer | head -1)
elif [ -f "app.py" ]; then
    APP_DIR=$CURRENT_DIR
else
    echo -e "${RED}Cannot find app directory!${NC}"
    read -p "Enter full path to your app directory: " APP_DIR
fi

echo "App directory: $APP_DIR"
echo ""

# Detect virtual environment
if [ -d "$APP_DIR/venv" ]; then
    VENV_PATH="$APP_DIR/venv"
elif [ -d "$APP_DIR/.venv" ]; then
    VENV_PATH="$APP_DIR/.venv"
else
    echo -e "${YELLOW}No virtual environment found. Creating one...${NC}"
    cd $APP_DIR
    python3 -m venv venv
    VENV_PATH="$APP_DIR/venv"
    source venv/bin/activate
    pip install -r requirements.txt
fi

echo "Virtual environment: $VENV_PATH"
echo ""

# Detect user (root or other)
if [ "$EUID" -eq 0 ]; then
    APP_USER="root"
    APP_GROUP="root"
else
    APP_USER=$(whoami)
    APP_GROUP=$(id -gn)
fi

echo "Running as: $APP_USER:$APP_GROUP"
echo ""

# Step 1: Create Gunicorn service file
echo "Step 1: Creating Gunicorn service..."
cat > /etc/systemd/system/gunicorn.service << EOF
[Unit]
Description=Gunicorn instance for Computer Shop
After=network.target mysql.service

[Service]
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"

ExecStart=$VENV_PATH/bin/gunicorn \\
    --workers 2 \\
    --threads 2 \\
    --worker-class sync \\
    --timeout 120 \\
    --bind unix:/tmp/gunicorn.sock \\
    --access-logfile /var/log/gunicorn/access.log \\
    --error-logfile /var/log/gunicorn/error.log \\
    --log-level info \\
    wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ Gunicorn service file created${NC}"
echo ""

# Step 2: Create log directory
echo "Step 2: Creating log directories..."
mkdir -p /var/log/gunicorn
chown -R $APP_USER:$APP_GROUP /var/log/gunicorn
echo -e "${GREEN}✅ Log directories created${NC}"
echo ""

# Step 3: Create Nginx configuration
echo "Step 3: Creating Nginx configuration..."

# Remove default site if it exists
rm -f /etc/nginx/sites-enabled/default

# Create our site configuration
cat > /etc/nginx/sites-available/computershop << 'EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 16M;
    client_body_timeout 120s;
    client_header_timeout 120s;
    keepalive_timeout 65s;
    send_timeout 120s;
    
    # Enable gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
    
    # Static files
    location /static/ {
        alias APP_DIR_PLACEHOLDER/static/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Main application
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
}
EOF

# Replace APP_DIR placeholder
sed -i "s|APP_DIR_PLACEHOLDER|$APP_DIR|g" /etc/nginx/sites-available/computershop

# Enable the site
ln -sf /etc/nginx/sites-available/computershop /etc/nginx/sites-enabled/

echo -e "${GREEN}✅ Nginx configuration created${NC}"
echo ""

# Step 4: Test Nginx configuration
echo "Step 4: Testing Nginx configuration..."
nginx -t
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Nginx configuration is valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration has errors!${NC}"
    echo "Please check the configuration manually"
fi
echo ""

# Step 5: Enable and start services
echo "Step 5: Enabling and starting services..."

# Reload systemd
systemctl daemon-reload

# Enable services
systemctl enable gunicorn
systemctl enable nginx

# Stop any existing processes
echo "Stopping old processes..."
pkill -9 gunicorn
pkill -9 python3
sleep 2

# Remove old socket if it exists
rm -f /tmp/gunicorn.sock

# Start MySQL first
echo "Starting MySQL..."
systemctl start mysql
sleep 3

# Start Gunicorn
echo "Starting Gunicorn..."
systemctl start gunicorn
sleep 3

# Check Gunicorn status
if systemctl is-active --quiet gunicorn; then
    echo -e "${GREEN}✅ Gunicorn started successfully${NC}"
else
    echo -e "${RED}❌ Gunicorn failed to start${NC}"
    echo "Checking logs..."
    journalctl -u gunicorn -n 20 --no-pager
fi
echo ""

# Start Nginx
echo "Starting Nginx..."
systemctl start nginx
sleep 2

# Check Nginx status
if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx started successfully${NC}"
else
    echo -e "${RED}❌ Nginx failed to start${NC}"
    echo "Checking logs..."
    journalctl -u nginx -n 20 --no-pager
fi
echo ""

# Step 6: Final status check
echo "======================================"
echo "FINAL STATUS CHECK"
echo "======================================"
echo ""

echo "MySQL:"
systemctl status mysql --no-pager | head -3
echo ""

echo "Gunicorn:"
systemctl status gunicorn --no-pager | head -3
echo ""

echo "Nginx:"
systemctl status nginx --no-pager | head -3
echo ""

# Check if socket exists
if [ -S /tmp/gunicorn.sock ]; then
    echo -e "${GREEN}✅ Gunicorn socket exists${NC}"
    ls -la /tmp/gunicorn.sock
else
    echo -e "${RED}❌ Gunicorn socket not found${NC}"
fi
echo ""

# Show server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "======================================"
echo -e "${GREEN}Setup complete!${NC}"
echo ""
echo "Your website should be accessible at:"
echo "  http://$SERVER_IP"
echo "  http://152.42.227.254"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status gunicorn"
echo "  sudo systemctl status nginx"
echo "  sudo systemctl restart gunicorn"
echo "  sudo tail -f /var/log/gunicorn/error.log"
echo ""
echo "If you see errors, check logs with:"
echo "  sudo journalctl -u gunicorn -n 50"
echo "  sudo journalctl -u nginx -n 50"
echo "======================================"

