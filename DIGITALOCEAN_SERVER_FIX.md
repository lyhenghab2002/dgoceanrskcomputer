# DigitalOcean Server Performance Emergency Fix

## 🚨 Your server is experiencing resource exhaustion

### Step 1: Diagnose the Problem (Run these via SSH)

```bash
# Check CPU and Memory usage
top -bn1 | head -20

# Check disk space
df -h

# Check memory details
free -h

# Check running processes sorted by memory
ps aux --sort=-%mem | head -20

# Check running processes sorted by CPU
ps aux --sort=-%cpu | head -20

# Check swap usage
swapon --show

# Check for MySQL processes
ps aux | grep mysql

# Check for Python processes
ps aux | grep python

# Check system load
uptime
```

### Step 2: Quick Emergency Fixes

#### A. Kill Resource-Heavy Processes
```bash
# Stop any hung Python processes
sudo pkill -9 python3

# Restart MySQL if it's consuming too much memory
sudo systemctl restart mysql

# Restart Gunicorn
sudo systemctl restart gunicorn

# Restart Nginx
sudo systemctl restart nginx
```

#### B. Free Up Memory
```bash
# Clear cache (safe operation)
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Check if swap is enabled, if not add it
sudo swapon --show
# If no swap, create one:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# Make it permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Step 3: Optimize Gunicorn Configuration

Create or edit: `/etc/systemd/system/gunicorn.service`

```ini
[Unit]
Description=Gunicorn instance for Computer Shop
After=network.target mysql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
Environment="PATH=/path/to/your/venv/bin"

# Optimized Gunicorn with proper worker configuration
ExecStart=/path/to/your/venv/bin/gunicorn \
    --workers 2 \
    --worker-class sync \
    --threads 2 \
    --worker-connections 100 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --timeout 120 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --bind unix:/tmp/gunicorn.sock \
    --log-level info \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    wsgi:application

Restart=always
RestartSec=10
StandardOutput=append:/var/log/gunicorn/output.log
StandardError=append:/var/log/gunicorn/error.log

[Install]
WantedBy=multi-user.target
```

### Step 4: Optimize Nginx Configuration

Edit: `/etc/nginx/sites-available/computershop`

```nginx
server {
    listen 80;
    server_name your_domain.com;
    
    # Increase timeouts
    client_body_timeout 120s;
    client_header_timeout 120s;
    keepalive_timeout 65s;
    send_timeout 120s;
    
    # Optimize buffer sizes
    client_body_buffer_size 128k;
    client_max_body_size 16M;
    client_header_buffer_size 1k;
    large_client_header_buffers 4 16k;
    
    # Enable compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
    gzip_disable "msie6";
    
    # Static files with aggressive caching
    location /static/ {
        alias /path/to/your/app/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Uploads
    location /static/uploads/ {
        alias /path/to/your/app/static/uploads/;
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:/tmp/gunicorn.sock;
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
}
```

### Step 5: Optimize MySQL

Edit: `/etc/mysql/mysql.conf.d/mysqld.cnf`

Add these optimizations for small servers:

```ini
[mysqld]
# Memory optimization for 1-2GB RAM servers
max_connections = 50
wait_timeout = 600
interactive_timeout = 600
connect_timeout = 10

# InnoDB settings
innodb_buffer_pool_size = 256M
innodb_log_file_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Query cache (if using MySQL 5.7)
query_cache_type = 1
query_cache_size = 32M
query_cache_limit = 2M

# Table cache
table_open_cache = 400
table_definition_cache = 400

# Temp tables
tmp_table_size = 32M
max_heap_table_size = 32M

# Log slow queries for debugging
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 2
```

Then restart MySQL:
```bash
sudo systemctl restart mysql
```

### Step 6: Apply All Changes

```bash
# Create log directories
sudo mkdir -p /var/log/gunicorn
sudo chown www-data:www-data /var/log/gunicorn

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn
sudo systemctl restart nginx

# Check status
sudo systemctl status gunicorn
sudo systemctl status nginx
sudo systemctl status mysql
```

### Step 7: Monitor Server Health

```bash
# Real-time monitoring
watch -n 2 'free -h && echo "" && df -h && echo "" && uptime'

# Check logs
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/mysql/error.log
```

### Step 8: Long-term Solutions

#### Upgrade Your DigitalOcean Droplet
If you're on the $4-6/month plan:
- Upgrade to at least $12/month (2GB RAM) or $24/month (4GB RAM)
- Your application needs more resources

#### Enable Monitoring
```bash
# Install htop for better monitoring
sudo apt install htop

# Use htop to monitor
htop
```

### Common Issues & Solutions

#### Issue: "Too many connections" MySQL error
```bash
mysql -u root -p
SET GLOBAL max_connections = 100;
FLUSH PRIVILEGES;
```

#### Issue: Nginx 502 Bad Gateway
```bash
# Check if Gunicorn socket exists
ls -la /tmp/gunicorn.sock

# Check Gunicorn logs
sudo journalctl -u gunicorn -n 50
```

#### Issue: Server runs out of memory
```bash
# Add more swap (if you have less than 2GB)
sudo fallocate -l 4G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
```

### Emergency One-Liner to Restore Service

If everything is down, run this:

```bash
sudo pkill -9 python3 && sudo systemctl restart mysql && sleep 5 && sudo systemctl restart gunicorn && sudo systemctl restart nginx && sleep 3 && sudo systemctl status gunicorn
```

### Check Your Droplet Size

```bash
# Check RAM
free -h

# Check CPU cores
nproc

# If you have:
# - 512MB RAM = Too small, upgrade immediately
# - 1GB RAM = Minimum, add swap and optimize
# - 2GB RAM = Good, optimize settings
# - 4GB+ RAM = Excellent
```

---

**After applying these fixes, your site should be back online within 5-10 minutes.**

