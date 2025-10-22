# 🚨 NGINX TIMEOUT FIX - Immediate Solution

## Problem Identified

From your screenshot:
1. ❌ **Gunicorn service doesn't exist** - `Unit gunicorn.service could not be found`
2. ❌ **Nginx is failing** - `start operation timed out` and `Failed to start`

## Root Cause

Your server was never properly set up with systemd services. Nginx is probably trying to connect to a Gunicorn socket that doesn't exist.

---

## ⚡ QUICK FIX - Run These Commands

### Step 1: Stop everything that's broken
```bash
sudo systemctl stop nginx
sudo pkill -9 gunicorn
sudo pkill -9 python3
```

### Step 2: Navigate to your app directory
```bash
cd /root/dgoceanrskcomputer
# Or wherever your app is located
```

### Step 3: Run the setup script
```bash
sudo bash setup_services.sh
```

The script will automatically:
- ✅ Create Gunicorn systemd service
- ✅ Configure Nginx properly
- ✅ Set up logging
- ✅ Start all services
- ✅ Check everything is working

---

## 🔧 Manual Setup (If Script Fails)

### 1. Create Gunicorn Service

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

**Paste this:**
```ini
[Unit]
Description=Gunicorn instance for Computer Shop
After=network.target mysql.service

[Service]
User=root
Group=root
WorkingDirectory=/root/dgoceanrskcomputer
Environment="PATH=/root/dgoceanrskcomputer/venv/bin"

ExecStart=/root/dgoceanrskcomputer/venv/bin/gunicorn \
    --workers 2 \
    --threads 2 \
    --worker-class sync \
    --timeout 120 \
    --bind unix:/tmp/gunicorn.sock \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    --log-level info \
    wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save with: `Ctrl+X`, then `Y`, then `Enter`

### 2. Create Log Directory

```bash
sudo mkdir -p /var/log/gunicorn
sudo chmod 755 /var/log/gunicorn
```

### 3. Fix Nginx Configuration

```bash
# Remove default config
sudo rm /etc/nginx/sites-enabled/default

# Create new config
sudo nano /etc/nginx/sites-available/computershop
```

**Paste this:**
```nginx
server {
    listen 80 default_server;
    server_name _;
    
    client_max_body_size 16M;
    client_body_timeout 120s;
    client_header_timeout 120s;
    keepalive_timeout 65s;
    send_timeout 120s;
    
    # Enable gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript;
    
    # Static files
    location /static/ {
        alias /root/dgoceanrskcomputer/static/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Main app
    location / {
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

Save and enable:
```bash
sudo ln -sf /etc/nginx/sites-available/computershop /etc/nginx/sites-enabled/
sudo nginx -t
```

### 4. Start Services in Order

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable gunicorn
sudo systemctl enable nginx

# Start MySQL first
sudo systemctl start mysql
sleep 3

# Start Gunicorn
sudo systemctl start gunicorn
sleep 3

# Check Gunicorn is running
sudo systemctl status gunicorn

# Verify socket exists
ls -la /tmp/gunicorn.sock

# Start Nginx
sudo systemctl start nginx

# Check Nginx is running
sudo systemctl status nginx
```

---

## ✅ Verify Everything Works

### Check Service Status
```bash
# All should show "active (running)"
sudo systemctl status mysql
sudo systemctl status gunicorn  
sudo systemctl status nginx
```

### Check Gunicorn Socket
```bash
ls -la /tmp/gunicorn.sock
# Should show: srwxrwxrwx 1 root root 0 ... /tmp/gunicorn.sock
```

### Test Nginx Configuration
```bash
sudo nginx -t
# Should show: "syntax is ok" and "test is successful"
```

### View Logs
```bash
# Gunicorn logs
sudo tail -50 /var/log/gunicorn/error.log

# Systemd logs
sudo journalctl -u gunicorn -n 50
sudo journalctl -u nginx -n 50
```

### Test Website
```bash
# From server
curl http://localhost

# From browser
http://152.42.227.254
```

---

## 🔍 Troubleshooting

### If Gunicorn Won't Start

```bash
# Check detailed error
sudo journalctl -u gunicorn -n 100 --no-pager

# Try starting manually to see errors
cd /root/dgoceanrskcomputer
source venv/bin/activate
gunicorn --bind unix:/tmp/gunicorn.sock wsgi:application
```

### If Nginx Shows "502 Bad Gateway"

```bash
# Check if socket exists
ls -la /tmp/gunicorn.sock

# Check Nginx error log
sudo tail -50 /var/log/nginx/error.log

# Check if Gunicorn is actually running
ps aux | grep gunicorn
```

### If Nginx Won't Start

```bash
# Check what's using port 80
sudo netstat -tlnp | grep :80

# Kill any process on port 80
sudo fuser -k 80/tcp

# Test nginx config
sudo nginx -t

# Start nginx in debug mode
sudo nginx -t && sudo systemctl restart nginx
sudo journalctl -u nginx -n 50
```

### If "Permission Denied" on Socket

```bash
# Fix socket permissions
sudo chmod 777 /tmp/gunicorn.sock

# Or update Nginx user
sudo usermod -a -G root www-data
```

---

## 📝 Quick Reference Commands

```bash
# Restart everything
sudo systemctl restart gunicorn && sudo systemctl restart nginx

# View all logs
sudo tail -f /var/log/gunicorn/error.log

# Check what's running
sudo systemctl status gunicorn nginx mysql

# Full reset (if everything is broken)
sudo systemctl stop nginx
sudo pkill -9 gunicorn
sudo rm /tmp/gunicorn.sock
sudo systemctl start gunicorn
sleep 3
sudo systemctl start nginx
```

---

## 🎯 After Setup Works

1. Test your website thoroughly
2. Set up automatic restarts: `sudo systemctl enable gunicorn nginx`
3. Monitor logs: `sudo tail -f /var/log/gunicorn/error.log`
4. Add swap if you haven't: See `START_HERE.md`
5. Consider upgrading server to 2GB+ RAM

---

**Your services should now be properly configured and running! 🚀**

