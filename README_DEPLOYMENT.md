# Deployment Guide for Render.com

This guide will help you deploy the Unified Bus Ticket Monitor to Render.com as a background worker that runs 24/7 for free.

## Prerequisites

- A GitHub account
- A Render.com account (free)
- Your Pushbullet API key

---

## Step 1: Prepare Your GitHub Repository

### 1.1 Install Git (if not already installed)
```bash
sudo apt-get update
sudo apt-get install git
```

### 1.2 Initialize Git Repository
Navigate to your project directory and initialize git:
```bash
cd "/home/fahim/Documents/Ticket Monitor"
git init
```

### 1.3 Create .gitignore File
Create a `.gitignore` file to exclude sensitive data:
```bash
cat > .gitignore << 'EOF'
.env
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.venv
venv/
ticket_cache.json
ticket_cache_busbd.json
EOF
```

### 1.4 Add and Commit Files
```bash
git add .
git commit -m "Initial commit: Unified ticket monitor for Render.com"
```

### 1.5 Create GitHub Repository
1. Go to [GitHub](https://github.com)
2. Click the "+" icon in the top right → "New repository"
3. Name it: `ticket-monitor` (or your preferred name)
4. Choose "Public" or "Private"
5. **Do NOT** initialize with README, .gitignore, or license
6. Click "Create repository"

### 1.6 Push to GitHub
Copy the commands from GitHub (they'll look like this):
```bash
git remote add origin https://github.com/YOUR_USERNAME/ticket-monitor.git
git branch -M main
git push -u origin main
```

---

## Step 2: Create Render.com Account

1. Go to [Render.com](https://render.com)
2. Click "Get Started" or "Sign Up"
3. Sign up with GitHub (recommended) or email
4. Verify your email if required

---

## Step 3: Deploy Background Worker on Render

### 3.1 Create New Service
1. From Render dashboard, click "New +" button
2. Select "Background Worker"

### 3.2 Connect GitHub Repository
1. If first time: Click "Connect GitHub" and authorize Render
2. Find and select your `ticket-monitor` repository
3. Click "Connect"

### 3.3 Configure Service Settings

**Basic Settings:**
- **Name**: `ticket-monitor-unified` (or your choice)
- **Region**: Choose closest to you (e.g., Singapore for Bangladesh)
- **Branch**: `main`
- **Runtime**: `Docker`

**Build Settings:**
- **Dockerfile Path**: `./Dockerfile` (auto-detected)

### 3.4 Configure Environment Variables

Click "Advanced" and add these environment variables:

| Key | Value | Note |
|-----|-------|------|
| `PUSHBULLET_API_KEY` | Your API key | Get from pushbullet.com/account |
| `TRAVEL_DATE` | `2026-04-15` | Format: YYYY-MM-DD |
| `RETURN_DATE` | `2026-04-20` | Format: YYYY-MM-DD |
| `SEARCH_ONWORD` | `True` | Set to False to disable onward search |
| `SEARCH_RETURN` | `True` | Set to False to disable return search |
| `CHECK_INTERVAL_MINUTES` | `3` | How often to check (in minutes) |

**Important:** Replace dates with your actual Eid travel dates!

### 3.5 Create Service
1. Review all settings
2. Click "Create Web Service" or "Deploy"
3. Wait for deployment (first build takes 2-5 minutes)

---

## Step 4: Get Your Pushbullet API Key

1. Go to [Pushbullet Account Settings](https://www.pushbullet.com/#settings/account)
2. Scroll to "Access Tokens"
3. Click "Create Access Token"
4. Copy the token
5. Add it to Render environment variables

---

## Step 5: Monitor Your Service

### 5.1 View Logs
1. Go to your service in Render dashboard
2. Click "Logs" tab
3. Watch real-time logs to see ticket checks

### 5.2 Check Service Status
- **Running**: Green indicator = service is active
- **Failed**: Red indicator = check logs for errors
- **Deploying**: Yellow indicator = deployment in progress

### 5.3 Log Output Examples
You should see logs like:
```
[2026-02-27 10:00:00] Unified Bus Ticket Monitor Started
[2026-02-27 10:00:00] Monitoring: BDTickets.com & BusBD.com
[2026-02-27 10:00:01] [BDTickets] Checking Onward tickets for 2026-04-15...
[2026-02-27 10:00:02] [BusBD] Checking Onward tickets for 2026-04-15...
```

---

## Step 6: Update Configuration (When Needed)

### Update Environment Variables:
1. Go to service in Render dashboard
2. Click "Environment" tab
3. Edit any variable (e.g., change dates)
4. Click "Save Changes"
5. Service will automatically restart

### Update Code:
1. Make changes locally
2. Commit and push to GitHub:
   ```bash
   git add .
   git commit -m "Update ticket check logic"
   git push
   ```
3. Render will automatically detect and deploy changes

---

## Troubleshooting

### Service Not Starting
- Check logs for errors
- Verify all environment variables are set
- Ensure `PUSHBULLET_API_KEY` is valid

### Not Receiving Notifications
- Test Pushbullet: Send manual notification from website
- Check if Pushbullet app is installed on your phone
- Verify API key is correct

### Service Stopped
- Free tier has 750 hours/month (enough for 1 service 24/7)
- If it stops, check Render dashboard for errors
- Restart manually from dashboard if needed

### API Errors in Logs
- BDTickets or BusBD API might be down temporarily
- The unified script continues checking the working API
- Wait for next check cycle

### Cache Not Working
- Cache files are created automatically on first run
- On Render, cache resets on each deploy (this is normal)
- First check after deploy may send notifications for all available tickets

---

## Free Tier Limitations

**Render.com Free Tier:**
- ✅ 750 hours/month (31+ days for one service)
- ✅ 512 MB RAM
- ✅ No credit card required
- ✅ Auto-deploys from GitHub
- ✅ HTTPS and environment variables
- ⚠️ Service may restart occasionally (automatic)
- ⚠️ Shared CPU (sufficient for this use case)

---

## Best Practices

1. **Set Reasonable Check Intervals**: 
   - 3-5 minutes is good
   - Too frequent may trigger rate limits

2. **Update Dates After Travel**:
   - Change `TRAVEL_DATE` and `RETURN_DATE` after Eid
   - Or set `SEARCH_ONWORD` and `SEARCH_RETURN` to `False`

3. **Monitor Regularly**:
   - Check logs occasionally
   - Ensure notifications are working

4. **Keep Dependencies Updated**:
   - Update `requirements.txt` occasionally
   - Test locally before pushing

---

## Alternative: Run Locally for Testing

Before deploying, test locally:

```bash
cd "/home/fahim/Documents/Ticket Monitor"

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
PUSHBULLET_API_KEY=your_key_here
TRAVEL_DATE=2026-04-15
RETURN_DATE=2026-04-20
SEARCH_ONWORD=True
SEARCH_RETURN=True
CHECK_INTERVAL_MINUTES=3
EOF

# Run unified monitor
python main_unified.py
```

---

## Support

If you encounter issues:
1. Check Render.com documentation: https://render.com/docs
2. Review logs in Render dashboard
3. Test Pushbullet API separately
4. Verify GitHub repository is connected

---

## Success Checklist

- [ ] Code pushed to GitHub
- [ ] Render.com account created
- [ ] Background worker service created
- [ ] All environment variables set
- [ ] Service is running (green status)
- [ ] Logs show ticket checking
- [ ] Pushbullet notifications received
- [ ] Ready for Eid ticket hunting! 🎉

---

**Last Updated**: February 27, 2026
**Project**: Unified Bus Ticket Monitor
**Platform**: Render.com (Free Tier)

