# Deployment Scripts

This directory contains automated deployment scripts for the SmartResume AI application on Fly.io.

## Available Scripts

### Cross-Platform Scripts

- **`deploy.ps1`** - PowerShell script for Windows users (recommended for Windows)
- **`deploy-all.sh`** - Bash script for Unix/Linux/macOS users

### Individual Service Scripts

- **`deploy-backend.sh`** - Deploy only the backend service (Unix/Linux/macOS)
- **`deploy-frontend.sh`** - Deploy only the frontend service (Unix/Linux/macOS)
- **`deploy-backend.bat`** - Deploy only the backend service (Windows batch)

## Quick Start

### Windows Users (PowerShell - Recommended)

```powershell
# Deploy both services
.\scripts\deploy.ps1

# Deploy with custom suffix
.\scripts\deploy.ps1 -AppSuffix staging

# Deploy only backend
.\scripts\deploy.ps1 -BackendOnly

# Deploy only frontend
.\scripts\deploy.ps1 -FrontendOnly

# Get help
.\scripts\deploy.ps1 -Help
```

### Windows Users (Command Prompt)

```cmd
# Deploy backend only
scripts\deploy-backend.bat

# Deploy with custom suffix
scripts\deploy-backend.bat staging
```

### Unix/Linux/macOS Users

```bash
# Make scripts executable (first time only)
chmod +x scripts/*.sh

# Deploy both services
./scripts/deploy-all.sh

# Deploy with custom suffix
./scripts/deploy-all.sh staging

# Deploy only backend
./scripts/deploy-all.sh --backend-only

# Deploy only frontend
./scripts/deploy-all.sh --frontend-only

# Individual service deployment
./scripts/deploy-backend.sh
./scripts/deploy-frontend.sh
```

## Prerequisites

1. **Fly.io CLI installed**: [Installation Guide](https://fly.io/docs/getting-started/installing-flyctl/)
2. **Fly.io account**: Sign up at [fly.io](https://fly.io)
3. **Authenticated with Fly.io**: Run `fly auth login`
4. **Environment variables ready**: Gather all required API keys and database credentials

## Required Environment Variables

### Backend Service

| Variable               | Description                                         | Required |
| ---------------------- | --------------------------------------------------- | -------- |
| `DATABASE_URL`         | Supabase PostgreSQL connection string               | Yes      |
| `GOOGLE_API_KEY`       | Google Gemini API key                               | Yes      |
| `JWT_SECRET`           | JWT signing secret (auto-generated if not provided) | Yes      |
| `SUPABASE_URL`         | Supabase project URL                                | Yes      |
| `SUPABASE_SERVICE_KEY` | Supabase service role key                           | Yes      |

### Frontend Service

| Variable                 | Description                                             | Required |
| ------------------------ | ------------------------------------------------------- | -------- |
| `VITE_API_URL`           | Backend service URL (auto-detected if backend deployed) | Yes      |
| `VITE_SUPABASE_URL`      | Supabase project URL                                    | Yes      |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key                                  | Yes      |

## Script Features

### Automated Features

- ✅ **Prerequisites checking** - Verifies Fly.io CLI and authentication
- ✅ **App creation** - Creates Fly.io apps if they don't exist
- ✅ **Configuration generation** - Creates optimized fly.toml files
- ✅ **Secret management** - Securely sets environment variables
- ✅ **Health checking** - Verifies deployments are working
- ✅ **Error handling** - Provides clear error messages and recovery steps

### Safety Features

- ✅ **Existing app detection** - Won't overwrite existing apps
- ✅ **Secret preservation** - Skips setting secrets that already exist
- ✅ **Rollback information** - Provides commands for troubleshooting
- ✅ **Validation** - Checks URLs and configuration before deployment

## App Naming Convention

The scripts use a consistent naming convention:

- Backend: `smartresume-backend-{suffix}`
- Frontend: `smartresume-frontend-{suffix}`

Default suffix is `prod`, but you can specify custom suffixes for different environments:

- Production: `smartresume-backend-prod`, `smartresume-frontend-prod`
- Staging: `smartresume-backend-staging`, `smartresume-frontend-staging`
- Development: `smartresume-backend-dev`, `smartresume-frontend-dev`

## Deployment Order

The scripts automatically handle the correct deployment order:

1. **Backend first** - Deploys the API service
2. **Frontend second** - Deploys the web interface with backend URL

This ensures the frontend can properly connect to the backend service.

## Troubleshooting

### Common Issues

1. **"fly command not found"**

   - Install Fly.io CLI: https://fly.io/docs/getting-started/installing-flyctl/

2. **"Not logged in to Fly.io"**

   - Run: `fly auth login`

3. **"Dockerfile not found"**

   - Ensure you're running the script from the project root directory
   - Verify `Dockerfile.backend` and `Dockerfile.frontend` exist

4. **"App name already exists"**

   - Use a different suffix: `./deploy.ps1 -AppSuffix myname`

5. **"Health check failed"**
   - Check logs: `fly logs -a your-app-name`
   - Wait a few minutes for the app to fully start
   - Verify environment variables are set correctly

### Getting Help

- **Script help**: Add `-h` or `--help` flag to any script
- **Fly.io docs**: https://fly.io/docs/
- **Application logs**: `fly logs -a your-app-name`
- **App status**: `fly status -a your-app-name`

## Manual Deployment

If you prefer manual deployment, see the main [DEPLOYMENT.md](../DEPLOYMENT.md) guide for step-by-step instructions.

## Security Notes

- ✅ Scripts never log or display sensitive environment variables
- ✅ Secrets are set using Fly.io's secure secret management
- ✅ Generated JWT secrets use cryptographically secure random generation
- ✅ All connections use HTTPS with proper certificate validation

## Contributing

When modifying these scripts:

1. Test on both Windows and Unix systems
2. Maintain backward compatibility
3. Update this README with any new features
4. Follow the existing error handling patterns
5. Ensure scripts are idempotent (safe to run multiple times)
