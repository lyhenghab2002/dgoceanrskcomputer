#!/bin/bash
# SETUP NEW WEBSITE - Complete Fresh Installation
# Run with: sudo bash SETUP_NEW_WEBSITE.sh

echo "🚀 SETUP NEW WEBSITE - Fresh Installation"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get configuration from user
echo "Let's set up your new website!"
echo ""

read -p "Enter your website name (e.g., mywebsite): " SITE_NAME
SITE_NAME=${SITE_NAME:-mywebsite}

read -p "Enter installation directory (default: /var/www/$SITE_NAME): " INSTALL_DIR
INSTALL_DIR=${INSTALL_DIR:-/var/www/$SITE_NAME}

read -p "Enter Git repository URL (or 'skip' to create blank): " GIT_REPO

read -p "Number of Gunicorn workers (default: 2): " WORKERS
WORKERS=${WORKERS:-2}

echo ""
echo "Configuration:"
echo "  Site name: $SITE_NAME"
echo "  Directory: $INSTALL_DIR"
echo "  Git repo: $GIT_REPO"
echo "  Workers: $WORKERS"
echo ""
read -p "Continue with this configuration? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "Starting installation..."
echo ""

# Step 1: Create directory structure
echo "1. Creating directory structure..."
mkdir -p $INSTALL_DIR
mkdir -p /var/log/gunicorn
cd $INSTALL_DIR

# Step 2: Get the code
if [ "$GIT_REPO" != "skip" ]; then
    echo "2. Cloning repository..."
    git clone $GIT_REPO .
else
    echo "2. Creating blank Flask application..."
    
    # Create basic Flask app
    cat > app.py << 'EOF'
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
EOF

    # Create wsgi.py
    cat > wsgi.py << 'EOF'
from app import app

application = app

if __name__ == "__main__":
    application.run()
EOF

    # Create requirements.txt
    cat > requirements.txt << 'EOF'
flask
gunicorn
werkzeug
EOF

    # Create templates directory
    mkdir -p templates
    cat > templates/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Welcome!</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }
        h1 { color: #2563eb; }
        .success { color: #16a34a; font-size: 24px; }
    </style>
</head>
<body>
    <h1>🎉 Your Website is Live!</h1>
    <p class="success">✅ Server is running successfully!</p>
    <p>Server IP: 152.42.227.254</p>
    <p>Edit <code>templates/index.html</code> to customize this page.</p>
</body>
</html>
EOF

    # Create static directory
    mkdir -p static/css static/js static/images
fi

# Step 3: Create virtual environment
echo "3. Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Step 4: Install dependencies
echo "4. Installing dependencies..."
if [ -f requirements.txt ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
else
    pip install flask gunicorn
fi

# Step 5: Create Gunicorn service
echo "5. Creating Gunicorn service..."
cat > /etc/systemd/system/gunicorn.service << EOF
[Unit]
Description=Gunicorn for $SITE_NAME
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"

ExecStart=$INSTALL_DIR/venv/bin/gunicorn \\
    --workers $WORKERS \\
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

# Step 6: Create Nginx configuration
echo "6. Creating Nginx configuration..."
cat > /etc/nginx/sites-available/$SITE_NAME << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    
    client_max_body_size 16M;
    client_body_timeout 120s;
    client_header_timeout 120s;
    
    # Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;
    
    # Static files
    location /static/ {
        alias $INSTALL_DIR/static/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Main application
    location / {
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/$SITE_NAME /etc/nginx/sites-enabled/

# Step 7: Test and start services
echo "7. Testing configurations..."
nginx -t

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Nginx configuration error!${NC}"
    exit 1
fi

# Step 8: Enable and start services
echo "8. Starting services..."
systemctl daemon-reload
systemctl enable gunicorn
systemctl enable nginx

systemctl start gunicorn
sleep 3
systemctl start nginx
sleep 2

# Step 9: Check status
echo ""
echo "=========================================="
echo "INSTALLATION COMPLETE!"
echo "=========================================="
echo ""

# Check services
echo "Service Status:"
echo ""
if systemctl is-active --quiet gunicorn; then
    echo -e "${GREEN}✅ Gunicorn: Running${NC}"
else
    echo -e "${RED}❌ Gunicorn: Failed${NC}"
    journalctl -u gunicorn -n 10 --no-pager
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx: Running${NC}"
else
    echo -e "${RED}❌ Nginx: Failed${NC}"
fi

echo ""
echo "Your website is now live at:"
echo ""
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}  🌐 http://$SERVER_IP${NC}"
echo -e "${GREEN}  🌐 http://152.42.227.254${NC}"
echo ""
echo "Website directory: $INSTALL_DIR"
echo "Edit files in: $INSTALL_DIR/"
echo ""
echo "Useful commands:"
echo "  sudo systemctl restart gunicorn  # Restart app"
echo "  sudo systemctl status gunicorn   # Check status"
echo "  sudo tail -f /var/log/gunicorn/error.log  # View logs"
echo ""
echo "=========================================="

