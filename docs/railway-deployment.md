# Railway Deployment Guide

This guide provides step-by-step instructions for deploying the Git Commit MCP Server to Railway with persistent storage.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Railway Volume Setup](#railway-volume-setup)
- [Environment Variables](#environment-variables)
- [Deployment Steps](#deployment-steps)
- [Custom Domain Configuration](#custom-domain-configuration)
- [Monitoring and Logs](#monitoring-and-logs)
- [Troubleshooting](#troubleshooting)

## Overview

Railway is a modern platform-as-a-service that simplifies deployment with:
- Built-in CI/CD from GitHub
- Persistent volumes for data storage
- Automatic HTTPS
- Environment variable management
- Real-time logs and monitoring

The Git Commit MCP Server is optimized for Railway deployment with:
- Docker containerization
- Persistent workspace for cloned repositories
- Health check endpoints
- Dynamic port binding
- Comprehensive logging

## Prerequisites

Before deploying to Railway, ensure you have:

1. **GitHub Account**: Your code must be in a GitHub repository
2. **Railway Account**: Sign up at [railway.app](https://railway.app)
3. **Railway CLI** (optional): Install with `npm i -g @railway/cli` or `brew install railway`
4. **Git Repository**: Push your code to GitHub

### Railway Plan Requirements

The Git Commit MCP Server works with Railway's Hobby plan:
- **Cost**: $5/month base + usage
- **Includes**: 
  - Persistent volumes (up to 100 GB)
  - Automatic HTTPS
  - Custom domains
  - Environment variables
  - Real-time logs

## Railway Volume Setup

Persistent volumes are essential for storing cloned repositories across deployments.

### Creating a Volume

1. **Navigate to Your Project**
   - Go to your Railway project dashboard
   - Select your service

2. **Add a Volume**
   - Click on the "Variables" tab
   - Scroll to "Volumes" section
   - Click "New Volume"

3. **Configure Volume**
   - **Name**: `git-workspaces` (or any descriptive name)
   - **Mount Path**: `/data`
   - **Size**: 2-5 GB (adjust based on expected repository sizes)

4. **Save Configuration**
   - Click "Add" to create the volume
   - Railway will automatically mount it on next deployment

### Volume Benefits

- **Persistence**: Cloned repositories survive deployments and restarts
- **Performance**: No need to re-clone repositories on each operation
- **Bandwidth**: Reduces data transfer costs
- **Speed**: Faster Git operations after initial clone

### Volume Size Recommendations

| Use Case | Recommended Size | Notes |
|----------|-----------------|-------|
| Small projects (1-5 repos) | 2 GB | Sufficient for most use cases |
| Medium projects (5-20 repos) | 5 GB | Good for multiple repositories |
| Large projects (20+ repos) | 10+ GB | Consider cleanup automation |

## Environment Variables

Configure these environment variables in the Railway dashboard.

### Required Variables

These variables **must** be set for the server to function:

```bash
# Transport mode - must be 'http' for Railway
TRANSPORT_MODE=http

# Authentication token - generate a secure random token
MCP_AUTH_TOKEN=your-secure-token-here

# Workspace directory - must match volume mount path
WORKSPACE_DIR=/data/git-workspaces
```

### Optional Variables

These variables provide additional configuration:

```bash
# HTTP Configuration
HTTP_HOST=0.0.0.0                    # Listen on all interfaces (default)
# Note: Railway automatically sets PORT, no need to configure HTTP_PORT

# CORS Configuration
CORS_ENABLED=true                    # Enable CORS (default: true)
CORS_ORIGINS=*                       # Allowed origins (comma-separated)

# Git Authentication (for private repositories)
GIT_USERNAME=your-github-username    # GitHub username for HTTPS
GIT_TOKEN=ghp_your_github_token      # GitHub personal access token
GIT_SSH_KEY_PATH=/data/ssh/id_rsa    # Path to SSH private key (if using SSH)

# Logging and Monitoring
LOG_LEVEL=INFO                       # Logging level (DEBUG, INFO, WARNING, ERROR)
ENABLE_METRICS=true                  # Enable /metrics endpoint (default: true)

# Workspace Cleanup
MAX_WORKSPACE_SIZE_MB=1000           # Max workspace size in MB (default: 1000)
CLEANUP_ENABLED=true                 # Enable cleanup endpoints (default: true)

# Commit Message Configuration
MAX_BULLET_POINTS=5                  # Max bullet points in commit messages
MAX_SUMMARY_LINES=2                  # Max lines in commit summary
CHANGELOG_FILE=CHANGELOG.md          # Name of changelog file
```

### Generating a Secure Auth Token

Use one of these methods to generate a secure token:

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32

# Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

### Setting Environment Variables

#### Via Railway Dashboard

1. Go to your project in Railway
2. Click on your service
3. Navigate to "Variables" tab
4. Click "New Variable"
5. Enter variable name and value
6. Click "Add"
7. Repeat for all required variables

#### Via Railway CLI

```bash
# Set a single variable
railway variables set MCP_AUTH_TOKEN=your-token-here

# Set multiple variables from .env file
railway variables set --from-file .env
```

## Deployment Steps

### Method 1: Deploy from GitHub (Recommended)

1. **Push Code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Railway deployment"
   git push origin main
   ```

2. **Create Railway Project**
   - Go to [railway.app](https://railway.app)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your GitHub account
   - Select your repository

3. **Configure Volume**
   - Follow steps in [Railway Volume Setup](#railway-volume-setup)
   - Set mount path to `/data`
   - Set size to 2-5 GB

4. **Set Environment Variables**
   - Follow steps in [Environment Variables](#environment-variables)
   - At minimum, set:
     - `TRANSPORT_MODE=http`
     - `MCP_AUTH_TOKEN=<your-secure-token>`
     - `WORKSPACE_DIR=/data/git-workspaces`

5. **Deploy**
   - Railway automatically builds and deploys on push
   - Monitor deployment in the "Deployments" tab
   - Check logs for any errors

6. **Verify Deployment**
   - Once deployed, Railway provides a URL (e.g., `https://your-app.railway.app`)
   - Test health endpoint: `curl https://your-app.railway.app/health`
   - Expected response:
     ```json
     {
       "status": "healthy",
       "version": "1.0.0",
       "transport": "http",
       "auth_enabled": true,
       "metrics_enabled": true
     }
     ```

### Method 2: Deploy via Railway CLI

1. **Install Railway CLI**
   ```bash
   npm i -g @railway/cli
   # or
   brew install railway
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize Project**
   ```bash
   railway init
   ```

4. **Link to Existing Project** (optional)
   ```bash
   railway link
   ```

5. **Set Environment Variables**
   ```bash
   railway variables set TRANSPORT_MODE=http
   railway variables set MCP_AUTH_TOKEN=your-secure-token
   railway variables set WORKSPACE_DIR=/data/git-workspaces
   ```

6. **Deploy**
   ```bash
   railway up
   ```

7. **Open in Browser**
   ```bash
   railway open
   ```

## Custom Domain Configuration

Railway provides automatic HTTPS for custom domains.

### Adding a Custom Domain

1. **Navigate to Settings**
   - Go to your Railway project
   - Click on your service
   - Navigate to "Settings" tab

2. **Add Domain**
   - Scroll to "Domains" section
   - Click "Add Domain"
   - Enter your custom domain (e.g., `mcp.yourdomain.com`)

3. **Configure DNS**
   - Railway provides DNS records to configure
   - Add the CNAME record to your DNS provider:
     ```
     Type: CNAME
     Name: mcp (or your subdomain)
     Value: <provided-by-railway>.railway.app
     ```

4. **Wait for Propagation**
   - DNS changes can take 5-60 minutes
   - Railway automatically provisions SSL certificate
   - Certificate is managed by Railway (auto-renewal)

5. **Verify**
   - Test your custom domain: `curl https://mcp.yourdomain.com/health`

### SSL/TLS Configuration

Railway automatically provides:
- Free SSL certificates via Let's Encrypt
- Automatic certificate renewal
- HTTPS enforcement
- HTTP to HTTPS redirect

No manual SSL configuration is required.

## Workspace Cleanup

The server includes automatic workspace management to prevent disk space exhaustion.

### Cleanup Endpoints

Two endpoints are available for workspace management:

#### 1. Get Workspace Information

```bash
curl -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/workspace/info
```

**Response:**
```json
{
  "workspace_path": "/data/git-workspaces",
  "repository_count": 5,
  "total_size_mb": 245.67,
  "max_size_mb": 1000,
  "usage_percent": 24.57,
  "disk_available_mb": 1854.33,
  "disk_total_mb": 2048.00,
  "cleanup_recommended": false
}
```

#### 2. Clean Up Workspace

```bash
curl -X POST -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/workspace/cleanup
```

**Response:**
```json
{
  "success": true,
  "repositories_cleaned": 5,
  "size_freed_mb": 245.67,
  "message": "Successfully cleaned up 5 repositories"
}
```

### Cleanup Strategy

The cleanup mechanism:
- Removes all cloned repositories from the workspace
- Frees up disk space on the persistent volume
- Repositories will be re-cloned on next use
- Does not affect the Git operations or commit history

### When to Clean Up

Consider cleaning up when:
- `usage_percent` exceeds 80% (cleanup_recommended: true)
- Disk space is running low
- You've finished working with certain repositories
- Before major deployments to start fresh

### Automated Cleanup

For automated cleanup, you can:

1. **Schedule via External Service**: Use a cron job or scheduled task to call the cleanup endpoint periodically
2. **Monitor and Alert**: Set up monitoring to alert when usage exceeds threshold
3. **Manual Cleanup**: Call the endpoint manually when needed

**Example: Scheduled Cleanup with GitHub Actions**

```yaml
name: Cleanup Railway Workspace
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday at midnight
  workflow_dispatch:  # Allow manual trigger

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Clean up workspace
        run: |
          curl -X POST \
            -H "Authorization: Bearer ${{ secrets.MCP_AUTH_TOKEN }}" \
            https://your-app.railway.app/workspace/cleanup
```

### Configuration

Control cleanup behavior with environment variables:

- `MAX_WORKSPACE_SIZE_MB`: Maximum workspace size before cleanup is recommended (default: 1000 MB)
- `CLEANUP_ENABLED`: Enable/disable cleanup endpoints (default: true)

**Example:**
```bash
# Set a 2 GB limit
MAX_WORKSPACE_SIZE_MB=2000

# Disable cleanup endpoints
CLEANUP_ENABLED=false
```

## Monitoring and Logs

### Viewing Logs

#### Via Railway Dashboard

1. Go to your project
2. Click on your service
3. Navigate to "Logs" tab
4. View real-time logs

#### Via Railway CLI

```bash
# View logs
railway logs

# Follow logs in real-time
railway logs --follow
```

### Log Levels

Configure log verbosity with `LOG_LEVEL` environment variable:

- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages (default)
- `WARNING`: Warning messages
- `ERROR`: Error messages only
- `CRITICAL`: Critical errors only

### Health Checks

Railway automatically monitors the `/health` endpoint:

- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 attempts before marking unhealthy

If health checks fail, Railway will:
1. Mark the service as unhealthy
2. Attempt to restart the service
3. Send notifications (if configured)

### Metrics Endpoint

Access Prometheus-compatible metrics at `/metrics`:

```bash
curl https://your-app.railway.app/metrics
```

Metrics include:
- Server health status
- Version information
- Request counts (future)
- Git operation metrics (future)

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

**Symptoms**: Deployment fails, service shows as "crashed"

**Solutions**:
- Check logs for error messages
- Verify all required environment variables are set
- Ensure `TRANSPORT_MODE=http`
- Verify `MCP_AUTH_TOKEN` is set
- Check that volume is properly mounted

**Debug Commands**:
```bash
# View recent logs
railway logs --tail 100

# Check environment variables
railway variables
```

#### 2. Volume Not Persisting

**Symptoms**: Repositories are re-cloned on every deployment

**Solutions**:
- Verify volume is created and mounted to `/data`
- Check `WORKSPACE_DIR=/data/git-workspaces`
- Ensure volume size is sufficient
- Check logs for permission errors

**Verification**:
```bash
# Check if volume is mounted (via logs)
railway logs | grep "workspace"
```

#### 3. Port Binding Errors

**Symptoms**: Server fails to start with port binding error

**Solutions**:
- Do NOT set `HTTP_PORT` environment variable
- Railway automatically sets `PORT` variable
- The server config reads `PORT` first, then falls back to `HTTP_PORT`
- Ensure `HTTP_HOST=0.0.0.0`

**Note**: Railway dynamically assigns ports. The server automatically uses Railway's `PORT` variable.

#### 4. Authentication Failures

**Symptoms**: 401 Unauthorized errors when calling endpoints

**Solutions**:
- Verify `MCP_AUTH_TOKEN` is set correctly
- Ensure client sends `Authorization: Bearer <token>` header
- Check token matches exactly (no extra spaces)
- Verify `AUTH_ENABLED=true` (default)

**Test Authentication**:
```bash
# Test with curl
curl -H "Authorization: Bearer your-token-here" \
  https://your-app.railway.app/health
```

#### 5. Git Operations Fail

**Symptoms**: Cannot clone or push to repositories

**Solutions**:

For HTTPS repositories:
- Set `GIT_USERNAME` to your GitHub username
- Set `GIT_TOKEN` to a GitHub personal access token
- Ensure token has `repo` scope

For SSH repositories:
- Store SSH private key in volume (e.g., `/data/ssh/id_rsa`)
- Set `GIT_SSH_KEY_PATH=/data/ssh/id_rsa`
- Ensure key has correct permissions (600)

**Generate GitHub Token**:
1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo` (full control of private repositories)
4. Copy token and set as `GIT_TOKEN`

#### 6. Disk Space Exhaustion

**Symptoms**: Operations fail with "No space left on device"

**Solutions**:
- Check workspace usage: `curl -H "Authorization: Bearer token" https://your-app.railway.app/workspace/info`
- Clean up workspace: `curl -X POST -H "Authorization: Bearer token" https://your-app.railway.app/workspace/cleanup`
- Increase volume size in Railway settings
- Monitor volume usage in Railway dashboard
- Set up automated cleanup (see Workspace Cleanup section)

**Check Volume Usage**:
```bash
# Get workspace information
curl -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/workspace/info

# View logs for disk space warnings
railway logs | grep -i "space\|disk"
```

**Immediate Fix**:
```bash
# Clean up all repositories to free space
curl -X POST -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/workspace/cleanup
```

#### 7. Health Check Failures

**Symptoms**: Service marked as unhealthy, frequent restarts

**Solutions**:
- Verify `/health` endpoint is accessible
- Check if server is starting successfully
- Review logs for startup errors
- Ensure port binding is correct
- Verify no firewall blocking health checks

**Test Health Endpoint**:
```bash
curl https://your-app.railway.app/health
```

### Getting Help

If you encounter issues not covered here:

1. **Check Railway Status**: [status.railway.app](https://status.railway.app)
2. **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
3. **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
4. **Project Issues**: Open an issue on the GitHub repository

### Debug Checklist

Before seeking help, verify:

- [ ] All required environment variables are set
- [ ] Volume is created and mounted to `/data`
- [ ] `TRANSPORT_MODE=http`
- [ ] `MCP_AUTH_TOKEN` is set
- [ ] Health endpoint returns 200 OK
- [ ] Logs show no critical errors
- [ ] Railway service status is "Active"
- [ ] DNS is configured correctly (if using custom domain)

## Best Practices

### Security

1. **Use Strong Auth Tokens**: Generate cryptographically secure tokens
2. **Rotate Tokens Regularly**: Update `MCP_AUTH_TOKEN` periodically
3. **Restrict CORS Origins**: Set specific domains instead of `*`
4. **Use HTTPS Only**: Railway provides this automatically
5. **Secure Git Credentials**: Use environment variables, never commit tokens

### Performance

1. **Monitor Volume Usage**: Keep volume usage below 80%
2. **Implement Cleanup**: Use cleanup endpoint to remove old repos
3. **Use Appropriate Volume Size**: Start with 2-5 GB, scale as needed
4. **Enable Metrics**: Monitor performance via `/metrics` endpoint

### Reliability

1. **Monitor Health Checks**: Ensure `/health` endpoint is responsive
2. **Review Logs Regularly**: Check for warnings and errors
3. **Set Up Alerts**: Configure Railway notifications
4. **Test After Deployment**: Verify all endpoints work correctly
5. **Keep Dependencies Updated**: Regularly update Python packages

### Cost Optimization

1. **Right-Size Volume**: Don't over-provision storage
2. **Implement Cleanup**: Remove unused repositories
3. **Monitor Usage**: Track Railway usage dashboard
4. **Use Hobby Plan**: Sufficient for most use cases ($5/month)

## Next Steps

After successful deployment:

1. **Configure MCP Client**: Update your MCP client configuration with Railway URL
2. **Test Operations**: Perform test commits and pushes
3. **Set Up Monitoring**: Configure alerts and monitoring
4. **Document URL**: Share Railway URL with team members
5. **Implement Cleanup**: Set up automated workspace cleanup

## Example Client Configuration

After deploying to Railway, configure your MCP client:

```json
{
  "mcpServers": {
    "git-commit-remote": {
      "url": "https://your-app.railway.app",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer your-mcp-auth-token"
      }
    }
  }
}
```

Replace:
- `your-app.railway.app` with your Railway URL
- `your-mcp-auth-token` with your `MCP_AUTH_TOKEN` value

## Conclusion

You now have a fully deployed Git Commit MCP Server on Railway with:
- ✅ Persistent storage for repositories
- ✅ Automatic HTTPS
- ✅ Health monitoring
- ✅ Real-time logs
- ✅ Secure authentication
- ✅ Scalable infrastructure

For additional help, refer to the [Railway documentation](https://docs.railway.app) or open an issue on the project repository.
