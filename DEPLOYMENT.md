# SmartResume AI - Fly.io Deployment Guide

This guide provides step-by-step instructions for deploying the SmartResume AI application to Fly.io using a dual-service architecture.

## Quick Start (Automated Deployment)

For automated deployment, use the provided scripts in the `scripts/` directory:

### Windows (PowerShell - Recommended)

```powershell
.\scripts\deploy.ps1
```

### Windows (Command Prompt)

```cmd
scripts\deploy-backend.bat
```

### Unix/Linux/macOS

```bash
chmod +x scripts/*.sh
./scripts/deploy-all.sh
```

See [scripts/README.md](scripts/README.md) for detailed script usage and options.

## Manual Deployment (Step-by-Step)

If you prefer manual deployment or need to customize the process, follow the detailed instructions below.

## Overview

The SmartResume AI application is deployed as two separate services on Fly.io:

- **Backend Service**: Python FastAPI application serving the API
- **Frontend Service**: React application served via nginx

## Prerequisites

1. **Fly.io Account**: Sign up at [fly.io](https://fly.io)
2. **Fly.io CLI**: Install flyctl following the [official guide](https://fly.io/docs/getting-started/installing-flyctl/)
3. **Environment Variables**: Gather all required API keys and database credentials

## Required Environment Variables

### Backend Service Secrets

| Variable               | Description                                | Example                                   |
| ---------------------- | ------------------------------------------ | ----------------------------------------- |
| `DATABASE_URL`         | Supabase PostgreSQL connection string      | `postgresql://user:pass@host:5432/db`     |
| `GOOGLE_API_KEY`       | Google Gemini API key for AI functionality | `AIzaSyC...`                              |
| `JWT_SECRET`           | Secret key for JWT token signing           | `your-secure-random-string`               |
| `SUPABASE_URL`         | Supabase project URL                       | `https://your-project.supabase.co`        |
| `SUPABASE_SERVICE_KEY` | Supabase service role key                  | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |

### Frontend Service Secrets

| Variable                 | Description                     | Example                                    |
| ------------------------ | ------------------------------- | ------------------------------------------ |
| `VITE_SUPABASE_URL`      | Supabase project URL (public)   | `https://your-project.supabase.co`         |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous key (public) | `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`  |
| `VITE_API_URL`           | Backend service URL             | `https://smartresume-backend-prod.fly.dev` |

## Deployment Steps

### Step 1: Setup Fly.io CLI

```bash
# Install Fly.io CLI (if not already installed)
# Visit: https://fly.io/docs/getting-started/installing-flyctl/

# Login to your Fly.io account
fly auth login
```

### Step 2: Deploy Backend Service

1. **Create backend configuration file:**

   ```bash
   cp fly.toml fly-backend.toml
   ```

2. **Edit `fly-backend.toml`:**

   - Update the `app` name to your desired backend app name
   - Keep only the backend configuration section
   - Remove or comment out the frontend configuration

3. **Create the backend app:**

   ```bash
   fly apps create smartresume-backend-[YOUR-SUFFIX]
   ```

4. **Set backend environment secrets:**

   ```bash
   fly secrets set DATABASE_URL="your-supabase-connection-string" -a smartresume-backend-[YOUR-SUFFIX]
   fly secrets set GOOGLE_API_KEY="your-gemini-api-key" -a smartresume-backend-[YOUR-SUFFIX]
   fly secrets set JWT_SECRET="your-jwt-secret" -a smartresume-backend-[YOUR-SUFFIX]
   fly secrets set SUPABASE_URL="your-supabase-url" -a smartresume-backend-[YOUR-SUFFIX]
   fly secrets set SUPABASE_SERVICE_KEY="your-supabase-service-key" -a smartresume-backend-[YOUR-SUFFIX]
   ```

5. **Deploy the backend:**

   ```bash
   fly deploy -c fly-backend.toml
   ```

6. **Verify backend deployment:**

   ```bash
   fly status -a smartresume-backend-[YOUR-SUFFIX]
   fly logs -a smartresume-backend-[YOUR-SUFFIX]

   # Test health endpoint
   curl https://smartresume-backend-[YOUR-SUFFIX].fly.dev/api/v1/health
   ```

### Step 3: Deploy Frontend Service

1. **Create frontend configuration file:**

   ```bash
   cp fly.toml fly-frontend.toml
   ```

2. **Edit `fly-frontend.toml`:**

   - Update the `app` name to your desired frontend app name
   - Uncomment the frontend configuration section
   - Update `VITE_API_URL` to point to your deployed backend service
   - Remove or comment out the backend configuration

3. **Create the frontend app:**

   ```bash
   fly apps create smartresume-frontend-[YOUR-SUFFIX]
   ```

4. **Set frontend environment secrets:**

   ```bash
   fly secrets set VITE_SUPABASE_URL="your-supabase-url" -a smartresume-frontend-[YOUR-SUFFIX]
   fly secrets set VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" -a smartresume-frontend-[YOUR-SUFFIX]
   fly secrets set VITE_API_URL="https://smartresume-backend-[YOUR-SUFFIX].fly.dev" -a smartresume-frontend-[YOUR-SUFFIX]
   ```

5. **Deploy the frontend:**

   ```bash
   fly deploy -c fly-frontend.toml
   ```

6. **Verify frontend deployment:**

   ```bash
   fly status -a smartresume-frontend-[YOUR-SUFFIX]
   fly logs -a smartresume-frontend-[YOUR-SUFFIX]

   # Test frontend
   curl https://smartresume-frontend-[YOUR-SUFFIX].fly.dev
   ```

## Service Communication and Networking

### Internal Communication

- **Frontend to Backend**: The frontend communicates with the backend via HTTPS using the public backend URL
- **Service Discovery**: Services are accessible via their Fly.io app names (e.g., `smartresume-backend-prod.fly.dev`)
- **Load Balancing**: Fly.io automatically handles load balancing and SSL termination

### Network Security

- **HTTPS Enforcement**: Both services enforce HTTPS connections
- **Internal Networking**: Services can communicate via Fly.io's internal network for better performance
- **Health Checks**: Automated health monitoring ensures service availability

### CORS Configuration

The backend is configured to accept requests from the frontend domain. Ensure your backend CORS settings include:

```python
# In your FastAPI app configuration
origins = [
    "https://smartresume-frontend-[YOUR-SUFFIX].fly.dev",
    "https://your-custom-domain.com",  # If using custom domain
]
```

## Custom Domains (Optional)

### Frontend Domain

```bash
# Add custom domain to frontend
fly certs add your-domain.com -a smartresume-frontend-[YOUR-SUFFIX]

# Configure DNS
# Add CNAME record: your-domain.com -> smartresume-frontend-[YOUR-SUFFIX].fly.dev
```

### Backend API Domain

```bash
# Add custom domain to backend
fly certs add api.your-domain.com -a smartresume-backend-[YOUR-SUFFIX]

# Configure DNS
# Add CNAME record: api.your-domain.com -> smartresume-backend-[YOUR-SUFFIX].fly.dev

# Update frontend environment variable
fly secrets set VITE_API_URL="https://api.your-domain.com" -a smartresume-frontend-[YOUR-SUFFIX]
```

## Monitoring and Maintenance

### Health Checks

Both services include automated health checks:

- **Backend**: `GET /api/v1/health` (every 30 seconds)
- **Frontend**: `GET /` (every 30 seconds)

### Viewing Logs

```bash
# Backend logs
fly logs -a smartresume-backend-[YOUR-SUFFIX]

# Frontend logs
fly logs -a smartresume-frontend-[YOUR-SUFFIX]

# Follow logs in real-time
fly logs -f -a smartresume-backend-[YOUR-SUFFIX]
```

### Scaling Services

```bash
# Scale backend (increase memory/CPU)
fly scale memory 1024 -a smartresume-backend-[YOUR-SUFFIX]
fly scale count 2 -a smartresume-backend-[YOUR-SUFFIX]

# Scale frontend
fly scale memory 512 -a smartresume-frontend-[YOUR-SUFFIX]
fly scale count 2 -a smartresume-frontend-[YOUR-SUFFIX]
```

### Updating Deployments

```bash
# Redeploy backend after code changes
fly deploy -c fly-backend.toml

# Redeploy frontend after code changes
fly deploy -c fly-frontend.toml
```

## Troubleshooting

### Common Issues

1. **Build Failures**:

   - Check Dockerfile syntax and paths
   - Verify all dependencies are listed in requirements.txt/package.json
   - Review build logs: `fly logs -a your-app-name`

2. **Service Communication Issues**:

   - Verify VITE_API_URL points to correct backend URL
   - Check CORS configuration in backend
   - Ensure both services are deployed and healthy

3. **Environment Variable Issues**:

   - List current secrets: `fly secrets list -a your-app-name`
   - Update secrets: `fly secrets set KEY=value -a your-app-name`
   - Restart app after secret changes: `fly apps restart your-app-name`

4. **Health Check Failures**:
   - Verify health endpoints are accessible
   - Check application startup logs
   - Adjust health check timeouts if needed

### Getting Help

- **Fly.io Documentation**: [https://fly.io/docs/](https://fly.io/docs/)
- **Fly.io Community**: [https://community.fly.io/](https://community.fly.io/)
- **Application Logs**: Use `fly logs` command for debugging

## Security Best Practices

1. **Secrets Management**: Never commit secrets to version control
2. **Environment Separation**: Use different app names for staging/production
3. **Regular Updates**: Keep dependencies and base images updated
4. **Access Control**: Use Fly.io organizations for team access management
5. **Monitoring**: Set up alerts for service health and performance metrics

## Cost Optimization

1. **Auto-stop Machines**: Enabled by default to reduce costs during low traffic
2. **Resource Allocation**: Start with minimal resources and scale as needed
3. **Monitoring Usage**: Use `fly dashboard` to monitor resource usage and costs
4. **Regional Deployment**: Deploy in regions closest to your users
