# 🔥 COMPLETE FRESH START - New Website Setup

## Your server is slow and broken. Let's start completely fresh!

---

## 🚀 QUICK START (3 Easy Steps)

### Step 1: Clean Everything
```bash
ssh root@152.42.227.254
cd ~
sudo bash COMPLETE_FRESH_START.sh
```
This will:
- ✅ Stop all old services
- ✅ Remove all old configurations
- ✅ Kill all old processes
- ✅ Clean up everything

### Step 2: Setup New Website
```bash
sudo bash SETUP_NEW_WEBSITE.sh
```
This will ask you:
- Website name
- Installation directory
- Git repository (or create blank Flask app)
- Number of workers

### Step 3: Visit Your Website
```
http://152.42.227.254
```

**DONE! Your new website is live!** 🎉

---

## 📋 Detailed Instructions

### Option A: Setup with Your Own Code

```bash
# 1. Clean everything
ssh root@152.42.227.254
sudo bash COMPLETE_FRESH_START.sh

# 2. Setup with your Git repository
sudo bash SETUP_NEW_WEBSITE.sh
# When prompted, enter your GitHub repo URL
# Example: https://github.com/yourusername/your-website.git

# 3. Done! Visit http://152.42.227.254
```

### Option B: Setup with Blank Template (Start from Scratch)

```bash
# 1. Clean everything
ssh root@152.42.227.254
sudo bash COMPLETE_FRESH_START.sh

# 2. Setup blank website
sudo bash SETUP_NEW_WEBSITE.sh
# When prompted for Git repo, type: skip
# This creates a basic Flask website

# 3. Visit http://152.42.227.254
# You'll see a welcome page!

# 4. Customize your website
cd /var/www/mywebsite
nano templates/index.html  # Edit your homepage
nano app.py  # Add routes and logic

# 5. Restart to see changes
sudo systemctl restart gunicorn
```

---

## 🔧 What Gets Created

### Your new website will have:
```
/var/www/mywebsite/
├── app.py              # Main Flask application
├── wsgi.py             # WSGI entry point
├── requirements.txt    # Python dependencies
├── venv/               # Virtual environment
├── templates/          # HTML templates
│   └── index.html      # Homepage
└── static/             # CSS, JS, images
    ├── css/
    ├── js/
    └── images/
```

### Services configured:
- ✅ Gunicorn systemd service
- ✅ Nginx web server
- ✅ Automatic restart on crash
- ✅ Logging enabled
- ✅ Compression enabled
- ✅ Static file caching

---

## 📁 Files to Upload to Server

Before running the scripts, upload these files to your server:

```bash
# On your LOCAL computer (Windows PowerShell):
# 1. Commit the new scripts
git add .
git commit -m "Add fresh start scripts"
git push origin main

# 2. SSH to server
ssh root@152.42.227.254

# 3. Download the scripts
cd ~
git clone https://github.com/yourusername/dgoceanrskcomputer.git temp
cp temp/COMPLETE_FRESH_START.sh .
cp temp/SETUP_NEW_WEBSITE.sh .
chmod +x *.sh

# 4. Run the scripts
sudo bash COMPLETE_FRESH_START.sh
sudo bash SETUP_NEW_WEBSITE.sh
```

---

## ⚡ Quick Commands

### After setup, use these commands:

```bash
# Restart your website
sudo systemctl restart gunicorn

# Check if running
sudo systemctl status gunicorn nginx

# View error logs
sudo tail -f /var/log/gunicorn/error.log

# Edit your homepage
cd /var/www/mywebsite
nano templates/index.html
sudo systemctl restart gunicorn

# Update from Git
cd /var/www/mywebsite
git pull
pip install -r requirements.txt
sudo systemctl restart gunicorn
```

---

## 🎨 Customize Your Website

### Edit the homepage:
```bash
cd /var/www/mywebsite
nano templates/index.html
# Make your changes
sudo systemctl restart gunicorn
```

### Add a new page:
```python
# Edit app.py
nano app.py

# Add this:
@app.route('/about')
def about():
    return render_template('about.html')

# Create the template
nano templates/about.html

# Restart
sudo systemctl restart gunicorn
```

### Add static files (CSS/JS):
```bash
cd /var/www/mywebsite/static
# Upload your files here

# In your HTML, reference them:
# <link rel="stylesheet" href="/static/css/style.css">
# <script src="/static/js/app.js"></script>
```

---

## 🔍 Troubleshooting

### Website not loading?
```bash
# Check services
sudo systemctl status gunicorn nginx

# Check logs
sudo journalctl -u gunicorn -n 50
sudo tail -50 /var/log/nginx/error.log

# Restart everything
sudo systemctl restart gunicorn nginx
```

### Need to start over again?
```bash
sudo bash COMPLETE_FRESH_START.sh
sudo bash SETUP_NEW_WEBSITE.sh
```

---

## 💰 Server Recommendations

For best performance:
- ✅ **Minimum**: 2GB RAM ($12/month DigitalOcean)
- ✅ **Recommended**: 4GB RAM ($24/month)
- ✅ **Add Swap**: 2GB (scripts will guide you)

---

## ✅ Success Checklist

- [ ] Ran COMPLETE_FRESH_START.sh
- [ ] Ran SETUP_NEW_WEBSITE.sh  
- [ ] Website loads at http://152.42.227.254
- [ ] Gunicorn is running (green status)
- [ ] Nginx is running (green status)
- [ ] No errors in logs
- [ ] Customized homepage
- [ ] Server has 2GB+ RAM or swap enabled

---

## 🆘 Need Help?

If something goes wrong:

```bash
# Get full diagnostic
sudo systemctl status gunicorn --no-pager
sudo systemctl status nginx --no-pager
sudo journalctl -u gunicorn -n 100 --no-pager
ls -la /tmp/gunicorn.sock
free -h
```

---

**Ready to start fresh? Let's go! 🚀**

