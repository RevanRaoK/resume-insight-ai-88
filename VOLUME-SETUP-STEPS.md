# 📋 EXACT Steps to Create Volume in Fly.io Web Dashboard

## 🎯 Step-by-Step Visual Guide

### Step 1: Access Your App Dashboard

1. Go to: **https://fly.io/dashboard**
2. Look for your app: **`resume-insight-ai-88`**
3. **Click on the app name** to open it

### Step 2: Navigate to Volumes

1. In your app dashboard, look at the **left sidebar**
2. Find and **click "Volumes"** (it has a disk icon 💾)
3. You'll see an empty volumes list

### Step 3: Create New Volume

1. **Click the "Create Volume" button** (usually blue/green)
2. A form will appear with these fields:

### Step 4: Fill Volume Details

```
Name: ml_models_vol
Size: 10 GB
Region: iad (MUST match your app region)
```

### Step 5: Create Volume

1. **Click "Create Volume"** or "Create" button
2. Wait for volume creation (takes ~30 seconds)
3. You should see: ✅ Volume `ml_models_vol` created

### Step 6: Configure Mount Point

1. **Click "Configuration"** tab (in left sidebar)
2. **Scroll down** to find the fly.toml editor
3. **Add this at the bottom**:
   ```toml
   [mounts]
     source = "ml_models_vol"
     destination = "/app/models"
   ```
4. **Click "Save"** or "Update Configuration"

### Step 7: Deploy

1. **Click "Deploy"** button (usually at top of dashboard)
2. **Wait 10-15 minutes** for deployment
3. **Check logs** to see model downloads

## 🚨 CRITICAL POINTS:

- **Volume Name**: MUST be exactly `ml_models_vol`
- **Size**: Minimum 10GB (ML models are ~2-3GB)
- **Region**: MUST be `iad` (same as your app)
- **Mount Path**: MUST be `/app/models`

## ✅ Success Indicators:

1. **Volume shows** in Volumes tab
2. **Mount appears** in Configuration
3. **Deployment succeeds**
4. **Logs show**: "spaCy model already cached" (after first run)

## 🔍 If You Can't Find Something:

- **"Volumes" not visible?** → Look for disk icon 💾 or "Storage"
- **"Create Volume" missing?** → Try refreshing page
- **Region dropdown empty?** → Select "iad" or "US East"

Your ML models will be permanently stored and won't fill up your machine!
