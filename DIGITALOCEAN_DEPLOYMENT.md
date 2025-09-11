# DigitalOcean Deployment Guide

This guide will help you deploy your Computer Shop E-commerce system to DigitalOcean App Platform.

## Prerequisites

- DigitalOcean account
- GitHub repository with your code
- MySQL database (can be DigitalOcean Managed Database)

## Step 1: Prepare Your Repository

1. **Ensure all files are committed to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for DigitalOcean deployment"
   git push origin main
   ```

2. **Verify these files exist in your repository:**
   - `requirements.txt`
   - `Procfile` (or create one)
   - `.env.example`
   - `README.md`

## Step 2: Create DigitalOcean App

1. **Log into DigitalOcean**
   - Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)

2. **Create New App**
   - Click "Create App"
   - Choose "GitHub" as source
   - Connect your GitHub account
   - Select your repository
   - Choose the branch (usually `main`)

## Step 3: Configure App Settings

### Basic Configuration
- **Name**: `computer-shop-ecommerce` (or your preferred name)
- **Region**: Choose closest to your users
- **Source Directory**: Leave empty (root directory)

### Build Settings
- **Build Command**: Leave empty (Flask auto-detects)
- **Run Command**: `gunicorn app:app`
- **Environment**: `Python`

### Environment Variables
Add these in the App Platform interface:

```env
SECRET_KEY=your-production-secret-key
MYSQL_HOST=your-database-host
MYSQL_USER=your-database-user
MYSQL_PASSWORD=your-database-password
MYSQL_DB=your-database-name
MYSQL_PORT=3306
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
BAKONG_ACCOUNT_ID=your-bakong-account
BAKONG_ACCOUNT_NAME=your-account-name
FLASK_ENV=production
```

## Step 4: Set Up Database

### Option A: DigitalOcean Managed Database
1. **Create Database**
   - Go to "Databases" in DigitalOcean
   - Create new MySQL database
   - Choose appropriate size
   - Note the connection details

2. **Configure Connection**
   - Use the provided connection string
   - Update environment variables with database details

### Option B: External Database
- Use any MySQL-compatible database
- Update environment variables accordingly

## Step 5: Configure Static Files

1. **Static File Serving**
   - DigitalOcean App Platform serves static files automatically
   - Ensure your static files are in the `static/` directory
   - No additional configuration needed

2. **File Uploads**
   - For production, consider using DigitalOcean Spaces for file storage
   - Update upload configuration in your app

## Step 6: Deploy

1. **Review Configuration**
   - Double-check all environment variables
   - Verify build and run commands

2. **Deploy**
   - Click "Create Resources"
   - Wait for deployment to complete
   - Note the generated URL

## Step 7: Post-Deployment Setup

1. **Database Migration**
   - Access your app's console
   - Run database migrations if needed
   - Create initial admin user

2. **Test Application**
   - Visit your app URL
   - Test key functionality
   - Verify database connections

## Step 8: Custom Domain (Optional)

1. **Add Domain**
   - Go to your app settings
   - Add custom domain
   - Configure DNS records

2. **SSL Certificate**
   - DigitalOcean provides free SSL certificates
   - Automatically configured for custom domains

## Environment-Specific Configuration

### Production Environment Variables
```env
FLASK_ENV=production
FLASK_DEBUG=False
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
```

### Development vs Production
- Use different database instances
- Configure appropriate logging levels
- Set up monitoring and alerts

## Monitoring and Maintenance

1. **App Metrics**
   - Monitor CPU, memory, and request metrics
   - Set up alerts for high usage

2. **Logs**
   - View application logs in DigitalOcean dashboard
   - Set up log forwarding if needed

3. **Updates**
   - Push changes to GitHub
   - DigitalOcean automatically redeploys
   - Monitor deployment status

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check `requirements.txt` for all dependencies
   - Verify Python version compatibility
   - Check build logs for specific errors

2. **Database Connection Issues**
   - Verify database credentials
   - Check network connectivity
   - Ensure database is accessible from App Platform

3. **Static File Issues**
   - Verify file paths in templates
   - Check static file configuration
   - Ensure files are committed to repository

### Getting Help
- Check DigitalOcean App Platform documentation
- Review application logs
- Test locally with production environment variables

## Cost Optimization

1. **App Sizing**
   - Start with Basic plan ($5/month)
   - Scale up based on usage
   - Monitor resource utilization

2. **Database Sizing**
   - Choose appropriate database size
   - Monitor database performance
   - Scale as needed

## Security Considerations

1. **Environment Variables**
   - Never commit sensitive data to repository
   - Use strong, unique passwords
   - Rotate secrets regularly

2. **Database Security**
   - Use strong database passwords
   - Enable SSL connections
   - Restrict database access

3. **Application Security**
   - Keep dependencies updated
   - Use HTTPS in production
   - Implement proper error handling

---

**Your Computer Shop E-commerce system is now live on DigitalOcean! 🚀**
