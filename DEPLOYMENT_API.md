# Ticket Monitor API - Deployment Guide

## Overview
This guide explains how to deploy the Ticket Monitor as a **Flask API on Render's free web service** and trigger it with a **free cron job service**.

### Why This Approach?
✅ **Free**: Render's web service is free (unlike background workers)  
✅ **Flexible**: Can be triggered on-demand or via cron  
✅ **Simple**: No complex setup required  
✅ **Scalable**: Easy to monitor and debug via web interface

---

## Architecture

```
Free Cron Service (cron-job.org) 
    ↓ (triggers every X minutes)
Your Flask API on Render
    ↓ (checks tickets)
BDTickets & BusBD APIs
    ↓ (sends notifications)
Pushbullet
```

---

## Step 1: Prepare Your Code

### Files Needed
- `app.py` - Flask API (✅ Already created)
- `requirements.txt` - Dependencies (✅ Already updated)
- `.env` - Environment variables (for local testing only)
- `Dockerfile` - Docker configuration (optional, use render.yaml instead)

---

## Step 2: Deploy to Render

### Option A: Deploy as Web Service (Recommended)

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Add Flask API for ticket monitor"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Create a new Web Service on Render**
   - Go to [render.com](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: `ticket-monitor-api`
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Plan**: `Free`

3. **Add Environment Variables**
   In Render dashboard, add these environment variables:
   - `PUSHBULLET_API_KEY` = `your_pushbullet_api_key`
   - `PORT` = `10000` (Render sets this automatically)

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete
   - Note your API URL: `https://ticket-monitor-api.onrender.com`

### Option B: Deploy with render.yaml

Create a new `render_api.yaml` file:

```yaml
services:
  - type: web
    name: ticket-monitor-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    plan: free
    envVars:
      - key: PUSHBULLET_API_KEY
        sync: false
      - key: PORT
        value: "10000"
```

Then:
1. Push to GitHub
2. In Render, click "New +" → "Blueprint"
3. Select your repository
4. Render will auto-detect `render_api.yaml`

---

## Step 3: Test Your API

### Test Locally First
```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

### Test Endpoints

**Health Check:**
```bash
curl http://localhost:5000/health
```

**Check Tickets:**
```bash
curl -X POST http://localhost:5000/check \
  -H "Content-Type: application/json" \
  -d '{
    "TRAVEL_DATE": "2026-03-08",
    "RETURN_DATE": "2026-03-28",
    "SEARCH_ONWARD": true,
    "SEARCH_RETURN": false
  }'
```

### Test on Render
Replace `localhost:5000` with your Render URL:
```bash
curl https://ticket-monitor-api.onrender.com/health

curl -X POST https://ticket-monitor-api.onrender.com/check \
  -H "Content-Type: application/json" \
  -d '{
    "TRAVEL_DATE": "2026-03-08",
    "RETURN_DATE": "2026-03-28",
    "SEARCH_ONWARD": true,
    "SEARCH_RETURN": false
  }'
```

---

## Step 4: Set Up Free Cron Job Service

### Option A: cron-job.org (Recommended)

1. **Sign up** at [cron-job.org](https://cron-job.org)
2. **Create a new cron job**:
   - **Title**: Ticket Monitor
   - **URL**: `https://ticket-monitor-api.onrender.com/check`
   - **Request Method**: `POST`
   - **Request Body**:
     ```json
     {
       "TRAVEL_DATE": "2026-03-08",
       "RETURN_DATE": "2026-03-28",
       "SEARCH_ONWARD": true,
       "SEARCH_RETURN": false
     }
     ```
   - **Headers**: 
     - `Content-Type: application/json`
   - **Schedule**: Every 3 minutes (or as needed)
   - **Execution schedule**: `*/3 * * * *` (every 3 minutes)

3. **Save and Enable** the cron job

### Option B: EasyCron

1. Sign up at [easycron.com](https://www.easycron.com)
2. Create new cron job with URL method
3. Set POST request with JSON payload
4. Schedule every 3 minutes

### Option C: GitHub Actions (Free with GitHub)

Create `.github/workflows/ticket-check.yml`:
```yaml
name: Check Tickets

on:
  schedule:
    - cron: '*/3 * * * *'  # Every 3 minutes
  workflow_dispatch:  # Manual trigger

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Call API
        run: |
          curl -X POST https://ticket-monitor-api.onrender.com/check \
            -H "Content-Type: application/json" \
            -d '{
              "TRAVEL_DATE": "2026-03-08",
              "RETURN_DATE": "2026-03-28",
              "SEARCH_ONWARD": true,
              "SEARCH_RETURN": false
            }'
```

---

## Step 5: Monitor Your Application

### Render Dashboard
- View logs in real-time
- Monitor service health
- Check request metrics

### API Endpoints for Monitoring
- `GET /` - Service info
- `GET /health` - Health check

---

## Important Notes

### ⚠️ Render Free Tier Limitations
- **Spins down after 15 minutes of inactivity**
- **First request after spin-down takes ~30 seconds** (cold start)
- **750 hours/month** (enough for 24/7 if you have only one service)

### 💡 Solutions for Cold Starts
1. **Use cron-job.org**: It will keep your service warm
2. **Add a health check cron**: Hit `/health` every 10 minutes to keep service alive
3. **Upgrade to paid plan**: $7/month for always-on service

### 🔒 Security (Optional)
Add API key authentication to prevent unauthorized access:

```python
# Add to app.py
API_KEY = os.getenv("API_KEY", "your-secret-key")

@app.before_request
def check_api_key():
    if request.endpoint not in ['home', 'health']:
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
```

Then add to Render env vars and cron job headers:
- Header: `X-API-Key: your-secret-key`

---

## Troubleshooting

### Issue: API returns 500 error
- Check Render logs for detailed error messages
- Verify environment variables are set correctly

### Issue: No notifications received
- Verify `PUSHBULLET_API_KEY` is set correctly
- Check if new tickets were found (cache system prevents duplicate notifications)
- Clear cache by deleting `ticket_cache_api.json` if needed

### Issue: Timeout errors
- Increase timeout in cron job service (default 30s may not be enough for cold start)
- Consider using multiple smaller requests instead of one large one

---

## API Response Format

**Success Response:**
```json
{
  "status": "success",
  "message": "Ticket check completed",
  "timestamp": "2026-03-01T10:30:00"
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "TRAVEL_DATE is required",
  "timestamp": "2026-03-01T10:30:00"
}
```

**Notifications:**
- Separate Pushbullet notifications are sent for each source (BDTickets, BusBD) when new tickets are found
- Notification format: "🚌 [Onward/Return] Bus Availability - [Source]"
- Contains: Number of buses, companies, and routes

---

## Cost Comparison

| Service | Cost | Pros | Cons |
|---------|------|------|------|
| Render Web Service | **FREE** | Easy setup, logs, scaling | Cold starts |
| Render Background Worker | **$7/month** | Always on, no cold starts | Not free |
| Heroku | **$7/month** | Popular, reliable | No free tier anymore |
| Railway | **FREE** ($5 credit) | Fast, modern | Limited free tier |

---

## Summary

✅ **You've created a Flask API** that checks tickets on-demand  
✅ **Deploy it for FREE on Render** as a web service  
✅ **Trigger it with FREE cron-job.org** every 3 minutes  
✅ **Get notifications via Pushbullet** when tickets are available  

**Total Cost: $0/month** 🎉

---

## Next Steps

1. ✅ Test API locally
2. ✅ Push to GitHub
3. ✅ Deploy to Render
4. ✅ Set up cron job
5. ✅ Monitor and enjoy!

Need help? Check the Render logs or API response for debugging information.

