# Fly.io Web Platform Setup Guide - WITH VOLUME STORAGE

## 🚨 CRITICAL: You NEED a volume for ML model storage!

ML models are large (~2-3GB) and will fill up your machine storage without persistent volume.

## Step 1: Create Volume Through Web Dashboard

1. **Go to**: https://fly.io/dashboard
2. **Click your app**: `smart-resume`
3. **Click "Volumes"** (left sidebar)
4. **Click "Create Volume"**
5. **Enter details**:
   - **Name**: `ml_models_vol`
   - **Size**: `10 GB`
   - **Region**: `iad`
6. **Click "Create"**

## Step 2: Add Volume Mount to Configuration

1. **Stay in your app dashboard**
2. **Click "Configuration"** tab
3. **Edit fly.toml** and add:
   ```toml
   [mounts]
     source = "ml_models_vol"
     destination = "/app/models"
   ```
4. **Save configuration**

## Step 3: Deploy

1. **Click "Deploy"** in dashboard
2. **Wait 10-15 minutes** for first deployment

## How It Works

### Without Volume (Temporary Storage):

- ✅ Docker image builds under 8GB
- ✅ All ML functionality works
- ⚠️ Models re-download on each restart (~2-3 minutes)

### With Volume (Persistent Storage):

- ✅ Docker image builds under 8GB
- ✅ All ML functionality works
- ✅ Models cached permanently
- ✅ Fast restarts (~30 seconds)

## Expected Behavior

### First Startup:

```
=== Resume Insight AI Starting ===
Checking for ML models...
Downloading spaCy model...
Downloading sentence transformer...
Model initialization complete
Starting services...
```

### Subsequent Startups (with volume):

```
=== Resume Insight AI Starting ===
Checking for ML models...
spaCy model already cached
Sentence transformer already cached
Model initialization complete
Starting services...
```

## Full Functionality Available:

- ✅ Frontend (React app on port 3000)
- ✅ Backend API (FastAPI on port 8000)
- ✅ Document processing (PDF, DOCX, OCR)
- ✅ ML analysis (semantic similarity, NER)
- ✅ AI feedback (Google Gemini + local models)

The application will work perfectly through the web platform!
