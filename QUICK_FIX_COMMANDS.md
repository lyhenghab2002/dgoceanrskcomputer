# 🚨 QUICK FIX - Run These Commands NOW

## Option 1: Automated Fix (Recommended)

```bash
# SSH into your server
ssh root@152.42.227.254

# Download and run the fix script
cd /root
wget https://raw.githubusercontent.com/[your-repo]/emergency_fix.sh
chmod +x emergency_fix.sh
sudo bash emergency_fix.sh
```

## Option 2: Manual Fix (Copy/Paste)

SSH into your server and run these commands one by one:

### Step 1: Check what's wrong
```bash
# Check memory
free -h

# Check disk
df -h

# Check CPU
top -bn1 | head -20
```

### Step 2: Quick restart everything
```bash
# Kill hung processes
sudo pkill -9 python3

# Wait a moment
sleep 3

# Restart MySQL
sudo systemctl restart mysql

# Wait for MySQL
sleep 5

# Restart Gunicorn
sudo systemctl restart gunicorn

# Restart Nginx
sudo systemctl restart nginx
```

### Step 3: Check if services are running
```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
sudo systemctl status mysql
```

### Step 4: Add swap if missing (IMPORTANT)
```bash
# Check if swap exists
sudo swapon --show

# If nothing shows, create swap:
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Step 5: Clear cache
```bash
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

### Step 6: Test your website
Open your website in a browser and check if it loads.

---

## If Still Slow: Optimize Gunicorn

### Update your gunicorn service:
```bash
# Edit the service file
sudo nano /etc/systemd/system/gunicorn.service
```

### Replace with this optimized version:
```ini
[Unit]
Description=Gunicorn for Computer Shop
After=network.target mysql.service

[Service]
User=root
Group=root
WorkingDirectory=/root/dgoceanrskcomputer
Environment="PATH=/root/dgoceanrskcomputer/venv/bin"

ExecStart=/root/dgoceanrskcomputer/venv/bin/gunicorn \
    --workers 2 \
    --threads 2 \
    --timeout 120 \
    --bind unix:/tmp/gunicorn.sock \
    wsgi:application

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Apply changes:
```bash
sudo systemctl daemon-reload
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

---

## Monitoring Commands

### Watch memory in real-time:
```bash
watch -n 2 free -h
```

### Monitor all processes:
```bash
htop
# Press F10 to quit
```

### Check error logs:
```bash
# Gunicorn errors
sudo tail -50 /var/log/gunicorn/error.log

# Nginx errors  
sudo tail -50 /var/log/nginx/error.log

# MySQL errors
sudo tail -50 /var/log/mysql/error.log
```

### Check what's using resources:
```bash
# Top memory consumers
ps aux --sort=-%mem | head -20

# Top CPU consumers
ps aux --sort=-%cpu | head -20
```

---

## Server Size Recommendations

Check your RAM:
```bash
free -h
```

**If you have:**
- **512MB RAM** → Upgrade to 2GB minimum ($12/month)
- **1GB RAM** → Upgrade to 2GB recommended ($12/month)
- **2GB RAM** → Should work, optimize settings
- **4GB+ RAM** → Good, check for other issues

---

## Emergency Contact Info

**DigitalOcean Support:** https://cloud.digitalocean.com/support

**Upgrade Droplet:** Go to your droplet → Resize → Choose larger plan

**Current Server:** 152.42.227.254

---

## After Everything Works

1. ✅ Set up automated backups
2. ✅ Enable DigitalOcean monitoring
3. ✅ Set up alerts for high CPU/memory
4. ✅ Consider using DigitalOcean Managed Database for MySQL
5. ✅ Implement Redis caching for better performance

See `DIGITALOCEAN_SERVER_FIX.md` for complete optimization guide.

