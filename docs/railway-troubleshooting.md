# Railway Troubleshooting Guide

This guide helps you diagnose and resolve common issues when deploying and running the Git Commit MCP Server on Railway.

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Volume and Storage Issues](#volume-and-storage-issues)
- [Port Binding Issues](#port-binding-issues)
- [Environment Variable Issues](#environment-variable-issues)
- [Authentication Issues](#authentication-issues)
- [Git Operations Issues](#git-operations-issues)
- [Logging and Monitoring](#logging-and-monitoring)
- [Performance Issues](#performance-issues)
- [Network and Connectivity Issues](#network-and-connectivity-issues)
- [Getting Help](#getting-help)

## Deployment Issues

### Service Won't Start

**Symptoms:**
- Deployment fails with "crashed" status
- Service shows as unhealthy in Railway dashboard
- Logs show startup errors

**Common Causes and Solutions:**

#### 1. Missing Required Environment Variables

**Check:**
```bash
railway variables
```

**Required variables:**
- `TRANSPORT_MODE=http`
- `MCP_AUTH_TOKEN=<your-token>`
- `WORKSPACE_DIR=/data/git-workspaces`

**Fix:**
```bash
railway variables set TRANSPORT_MODE=http
railway variables set MCP_AUTH_TOKEN=your-secure-token
railway variables set WORKSPACE_DIR=/data/git-workspaces
```

#### 2. Docker Build Failures

**Check logs for:**
- `ERROR: failed to solve`
- `pip install` errors
- Missing system dependencies

**Solutions:**
- Verify Dockerfile syntax is correct
- Check that all dependencies are listed in `pyproject.toml`
- Ensure base image is accessible
- Try rebuilding: `railway up --detach`

#### 3. Python Version Mismatch

**Check Dockerfile:**
```dockerfile
FROM python:3.11-slim
```

**Ensure:**
- Python version matches `pyproject.toml` requirements (>=3.10)
- All dependencies support the Python version

### Build Succeeds but Service Crashes

**Symptoms:**
- Build completes successfully
- Service starts then immediately crashes
- Logs show runtime errors

**Check:**

1. **Import Errors:**
   ```bash
   railway logs | grep "ImportError\|ModuleNotFoundError"
   ```
   
   **Fix:** Ensure all dependencies are installed in Dockerfile

2. **Permission Errors:**
   ```bash
   railway logs | grep "Permission denied"
   ```
   
   **Fix:** Check file permissions in Dockerfile, ensure non-root user has access

3. **Configuration Errors:**
   ```bash
   railway logs | grep "ConfigError\|ValueError"
   ```
   
   **Fix:** Verify environment variables are set correctly

### Deployment Hangs or Times Out

**Symptoms:**
- Deployment process never completes
- Build step takes extremely long
- No error messages in logs

**Solutions:**

1. **Check Railway Status:**
   - Visit [status.railway.app](https://status.railway.app)
   - Verify no ongoing incidents

2. **Optimize Docker Build:**
   - Use multi-stage builds
   - Leverage Docker layer caching
   - Minimize image size

3. **Check Network:**
   - Ensure GitHub repository is accessible
   - Verify no firewall blocking Railway

## Volume and Storage Issues

### Volume Not Persisting Data

**Symptoms:**
- Repositories are re-cloned on every deployment
- Data disappears after restart
- Workspace appears empty

**Diagnosis:**

1. **Check Volume Configuration:**
   - Go to Railway dashboard → Your service → Variables → Volumes
   - Verify volume exists and mount path is `/data`

2. **Check Environment Variable:**
   ```bash
   railway variables | grep WORKSPACE_DIR
   ```
   Should show: `WORKSPACE_DIR=/data/git-workspaces`

3. **Check Logs:**
   ```bash
   railway logs | grep "workspace\|volume\|/data"
   ```

**Solutions:**

1. **Create Volume if Missing:**
   - Railway dashboard → Variables → Volumes → New Volume
   - Mount path: `/data`
   - Size: 2-5 GB

2. **Verify Mount Path:**
   - Ensure `WORKSPACE_DIR` matches volume mount path
   - Default: `/data/git-workspaces` (subdirectory of `/data` mount)

3. **Check Permissions:**
   - Ensure Docker user has write access to `/data`
   - Dockerfile should set proper ownership:
     ```dockerfile
     RUN mkdir -p /data/git-workspaces && chown -R mcpuser:mcpuser /data
     ```

### Disk Space Exhausted

**Symptoms:**
- Operations fail with "No space left on device"
- Service becomes unresponsive
- Cannot clone new repositories

**Check Volume Usage:**

```bash
# Get workspace information
curl -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/workspace/info
```

**Response shows:**
```json
{
  "usage_percent": 95.5,
  "cleanup_recommended": true,
  "total_size_mb": 4775.23,
  "max_size_mb": 5000
}
```

**Solutions:**

1. **Clean Up Workspace:**
   ```bash
   curl -X POST -H "Authorization: Bearer your-token" \
     https://your-app.railway.app/workspace/cleanup
   ```

2. **Increase Volume Size:**
   - Railway dashboard → Variables → Volumes
   - Click on your volume → Increase size
   - Recommended: 5-10 GB for active use

3. **Monitor Usage:**
   - Set up automated cleanup (see Railway Deployment Guide)
   - Monitor usage regularly via `/workspace/info` endpoint

4. **Configure Cleanup Threshold:**
   ```bash
   railway variables set MAX_WORKSPACE_SIZE_MB=4000
   ```

### Volume Mount Fails

**Symptoms:**
- Logs show "failed to mount volume"
- Service won't start after adding volume
- Permission denied errors on `/data`

**Solutions:**

1. **Verify Volume Configuration:**
   - Check mount path is exactly `/data` (no trailing slash)
   - Ensure volume is attached to correct service

2. **Redeploy Service:**
   ```bash
   railway up --detach
   ```

3. **Check Railway Limits:**
   - Verify your plan supports volumes
   - Hobby plan required for persistent volumes

## Port Binding Issues

### Port Binding Errors

**Symptoms:**
- Logs show "Address already in use"
- "Failed to bind to port" errors
- Service won't start

**Common Causes:**

1. **Manually Setting HTTP_PORT:**
   - Railway automatically sets `PORT` environment variable
   - Do NOT set `HTTP_PORT` manually

**Fix:**
```bash
# Remove HTTP_PORT if set
railway variables delete HTTP_PORT

# Verify PORT is not set manually
railway variables | grep PORT
```

2. **Wrong Host Configuration:**
   - Must bind to `0.0.0.0` not `localhost` or `127.0.0.1`

**Fix:**
```bash
railway variables set HTTP_HOST=0.0.0.0
```

### Health Check Failures

**Symptoms:**
- Service marked as unhealthy
- Frequent restarts
- "Health check failed" in logs

**Diagnosis:**

1. **Test Health Endpoint:**
   ```bash
   curl https://your-app.railway.app/health
   ```
   
   **Expected response:**
   ```json
   {
     "status": "healthy",
     "version": "1.0.0",
     "transport": "http"
   }
   ```

2. **Check Response Time:**
   - Health checks timeout after 10 seconds
   - Ensure server responds quickly

**Solutions:**

1. **Verify Server is Running:**
   ```bash
   railway logs | grep "Uvicorn running"
   ```

2. **Check Port Configuration:**
   - Ensure server binds to Railway's PORT
   - Verify HTTP_HOST=0.0.0.0

3. **Review Startup Time:**
   - If server takes >30 seconds to start, optimize initialization
   - Consider lazy loading of heavy dependencies

## Environment Variable Issues

### Variables Not Loading

**Symptoms:**
- Server uses default values instead of configured values
- Configuration errors on startup
- Features not working as expected

**Diagnosis:**

1. **List All Variables:**
   ```bash
   railway variables
   ```

2. **Check Logs for Variable Values:**
   ```bash
   railway logs | grep "Config loaded"
   ```

**Solutions:**

1. **Verify Variable Names:**
   - Check for typos (case-sensitive)
   - Ensure no extra spaces in names or values

2. **Redeploy After Setting Variables:**
   ```bash
   railway up --detach
   ```

3. **Check Variable Precedence:**
   - Railway variables override .env file
   - Ensure no conflicting values

### Invalid Variable Values

**Symptoms:**
- Validation errors on startup
- Type conversion errors
- Configuration warnings

**Common Issues:**

1. **Boolean Values:**
   ```bash
   # Wrong
   AUTH_ENABLED=True
   
   # Correct
   AUTH_ENABLED=true
   ```

2. **Numeric Values:**
   ```bash
   # Wrong
   MAX_WORKSPACE_SIZE_MB="1000"
   
   # Correct
   MAX_WORKSPACE_SIZE_MB=1000
   ```

3. **List Values:**
   ```bash
   # Comma-separated, no spaces
   CORS_ORIGINS=https://app1.com,https://app2.com
   ```

### Missing Required Variables

**Symptoms:**
- Server fails to start
- "Missing required configuration" errors

**Required Variables Checklist:**

- [ ] `TRANSPORT_MODE=http`
- [ ] `MCP_AUTH_TOKEN=<secure-token>`
- [ ] `WORKSPACE_DIR=/data/git-workspaces`

**Quick Fix:**
```bash
railway variables set TRANSPORT_MODE=http
railway variables set MCP_AUTH_TOKEN=$(openssl rand -base64 32)
railway variables set WORKSPACE_DIR=/data/git-workspaces
```

## Authentication Issues

### 401 Unauthorized Errors

**Symptoms:**
- All API requests return 401
- "Invalid token" or "Missing token" errors
- Cannot access any endpoints

**Diagnosis:**

1. **Check Token is Set:**
   ```bash
   railway variables | grep MCP_AUTH_TOKEN
   ```

2. **Test with Curl:**
   ```bash
   # Without token (should fail)
   curl https://your-app.railway.app/health
   
   # With token (should succeed)
   curl -H "Authorization: Bearer your-token" \
     https://your-app.railway.app/health
   ```

**Solutions:**

1. **Verify Token Format:**
   - Must include "Bearer " prefix in Authorization header
   - Format: `Authorization: Bearer <token>`
   - No extra spaces or quotes

2. **Check Token Matches:**
   ```bash
   # Get token from Railway
   railway variables | grep MCP_AUTH_TOKEN
   
   # Ensure client uses exact same token
   ```

3. **Regenerate Token:**
   ```bash
   # Generate new token
   NEW_TOKEN=$(openssl rand -base64 32)
   
   # Set in Railway
   railway variables set MCP_AUTH_TOKEN=$NEW_TOKEN
   
   # Update client configuration
   ```

### Authentication Disabled Unexpectedly

**Symptoms:**
- Endpoints accessible without token
- Security warnings in logs

**Check:**
```bash
railway variables | grep AUTH_ENABLED
```

**Fix:**
```bash
# Enable authentication (default)
railway variables set AUTH_ENABLED=true

# Or remove variable to use default
railway variables delete AUTH_ENABLED
```

### Token Rotation Issues

**Symptoms:**
- Old token still works after rotation
- New token not recognized

**Solution:**

1. **Update Token:**
   ```bash
   railway variables set MCP_AUTH_TOKEN=new-token-here
   ```

2. **Trigger Redeploy:**
   ```bash
   railway up --detach
   ```

3. **Wait for Deployment:**
   - Old instances may serve requests briefly
   - Wait 1-2 minutes for full rollout

4. **Update All Clients:**
   - Update MCP client configurations
   - Restart MCP clients to load new token

## Git Operations Issues

### Cannot Clone Repositories

**Symptoms:**
- "Authentication failed" when cloning
- "Repository not found" errors
- Timeout errors during clone

**For HTTPS Repositories:**

1. **Set Git Credentials:**
   ```bash
   railway variables set GIT_USERNAME=your-github-username
   railway variables set GIT_TOKEN=ghp_your_github_token
   ```

2. **Generate GitHub Token:**
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate new token (classic)
   - Select scope: `repo` (full control)
   - Copy token and set as `GIT_TOKEN`

3. **Test Token:**
   ```bash
   # Test with curl
   curl -H "Authorization: token ghp_your_token" \
     https://api.github.com/user
   ```

**For SSH Repositories:**

1. **Generate SSH Key:**
   ```bash
   ssh-keygen -t ed25519 -C "railway-mcp-server" -f railway_key
   ```

2. **Add to GitHub:**
   - Copy public key: `cat railway_key.pub`
   - Add to GitHub Settings → SSH keys

3. **Store Private Key:**
   - Base64 encode: `cat railway_key | base64`
   - Set as environment variable:
     ```bash
     railway variables set GIT_SSH_KEY_BASE64=<base64-encoded-key>
     ```

4. **Update Dockerfile to Decode:**
   ```dockerfile
   RUN echo "$GIT_SSH_KEY_BASE64" | base64 -d > /data/ssh/id_rsa && \
       chmod 600 /data/ssh/id_rsa
   ```

### Push Operations Fail

**Symptoms:**
- Commits succeed but push fails
- "Permission denied" on push
- "Remote rejected" errors

**Solutions:**

1. **Verify Push Permissions:**
   - Ensure GitHub token has `repo` scope
   - Check repository permissions (write access required)

2. **Check Branch Protection:**
   - Verify branch allows direct pushes
   - Check if pull requests are required

3. **Test Push Manually:**
   ```bash
   # In a test repository
   git push origin main
   ```

### Repository Access Timeout

**Symptoms:**
- Clone or fetch operations timeout
- "Connection timed out" errors
- Operations hang indefinitely

**Solutions:**

1. **Check Network Connectivity:**
   ```bash
   railway logs | grep "timeout\|connection"
   ```

2. **Increase Timeout:**
   ```bash
   railway variables set GIT_OPERATION_TIMEOUT=300
   ```

3. **Use HTTPS Instead of SSH:**
   - HTTPS generally more reliable in containerized environments
   - Less firewall issues

4. **Check Repository Size:**
   - Very large repositories may timeout
   - Consider shallow clones for large repos

## Logging and Monitoring

### Cannot See Logs

**Symptoms:**
- Railway dashboard shows no logs
- Logs appear empty or incomplete

**Solutions:**

1. **Check Log Level:**
   ```bash
   railway variables set LOG_LEVEL=INFO
   ```

2. **Ensure Logging to Stdout:**
   - Server must log to stdout/stderr
   - Railway captures console output

3. **View Recent Logs:**
   ```bash
   # Via CLI
   railway logs --tail 100
   
   # Follow in real-time
   railway logs --follow
   ```

### Missing Log Entries

**Symptoms:**
- Some operations not logged
- Gaps in log timeline
- Expected messages don't appear

**Solutions:**

1. **Increase Log Level:**
   ```bash
   railway variables set LOG_LEVEL=DEBUG
   ```

2. **Check Log Buffering:**
   - Python may buffer logs
   - Ensure `PYTHONUNBUFFERED=1` is set

3. **Verify Logging Configuration:**
   ```python
   # In code, ensure logging is configured
   import logging
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

### Monitoring Health Status

**Check Health Endpoint:**
```bash
# Basic health check
curl https://your-app.railway.app/health

# With authentication
curl -H "Authorization: Bearer your-token" \
  https://your-app.railway.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "transport": "http",
  "auth_enabled": true,
  "metrics_enabled": true,
  "workspace_path": "/data/git-workspaces"
}
```

**Monitor Metrics:**
```bash
curl https://your-app.railway.app/metrics
```

### Setting Up Alerts

**Railway Notifications:**

1. **Go to Project Settings:**
   - Railway dashboard → Project → Settings

2. **Configure Notifications:**
   - Email notifications for deployments
   - Webhook notifications for events
   - Slack/Discord integrations

3. **Set Up External Monitoring:**
   - Use UptimeRobot or similar
   - Monitor `/health` endpoint
   - Alert on downtime or errors

## Performance Issues

### Slow Response Times

**Symptoms:**
- API requests take >5 seconds
- Operations timeout
- Poor user experience

**Diagnosis:**

1. **Check Server Logs:**
   ```bash
   railway logs | grep "duration\|time\|slow"
   ```

2. **Monitor Resource Usage:**
   - Railway dashboard → Metrics
   - Check CPU and memory usage

**Solutions:**

1. **Optimize Git Operations:**
   - Use shallow clones: `git clone --depth 1`
   - Cache cloned repositories
   - Implement repository cleanup

2. **Increase Resources:**
   - Upgrade Railway plan if needed
   - Check if hitting resource limits

3. **Enable Caching:**
   - Cache frequently accessed repositories
   - Implement TTL-based eviction

### High Memory Usage

**Symptoms:**
- Service crashes with OOM errors
- Memory usage constantly high
- Slow performance over time

**Solutions:**

1. **Check for Memory Leaks:**
   ```bash
   railway logs | grep "memory\|OOM"
   ```

2. **Optimize Repository Handling:**
   - Clean up after operations
   - Limit concurrent operations
   - Implement workspace cleanup

3. **Configure Memory Limits:**
   ```bash
   railway variables set MAX_CONCURRENT_OPERATIONS=3
   ```

### Slow Startup Time

**Symptoms:**
- Service takes >30 seconds to start
- Health checks fail during startup
- Frequent restarts

**Solutions:**

1. **Optimize Docker Image:**
   - Use smaller base image
   - Minimize layers
   - Remove unnecessary dependencies

2. **Lazy Load Dependencies:**
   - Import heavy libraries only when needed
   - Defer initialization of optional features

3. **Reduce Startup Tasks:**
   - Move non-critical initialization to background
   - Use async initialization where possible

## Network and Connectivity Issues

### Cannot Access Railway URL

**Symptoms:**
- Railway URL returns connection refused
- Timeout when accessing service
- DNS resolution fails

**Solutions:**

1. **Verify Service is Running:**
   ```bash
   railway status
   ```

2. **Check Railway URL:**
   - Railway dashboard → Service → Settings → Domains
   - Verify URL is correct

3. **Test DNS Resolution:**
   ```bash
   nslookup your-app.railway.app
   ```

4. **Check Firewall:**
   - Ensure no firewall blocking Railway domains
   - Try from different network

### Custom Domain Not Working

**Symptoms:**
- Custom domain returns 404 or connection error
- SSL certificate errors
- DNS not resolving

**Solutions:**

1. **Verify DNS Configuration:**
   ```bash
   nslookup mcp.yourdomain.com
   ```
   
   Should return Railway's CNAME target

2. **Check CNAME Record:**
   - Type: CNAME
   - Name: mcp (or your subdomain)
   - Value: your-app.railway.app

3. **Wait for DNS Propagation:**
   - Can take 5-60 minutes
   - Check with: `dig mcp.yourdomain.com`

4. **Verify SSL Certificate:**
   - Railway auto-provisions SSL
   - May take a few minutes after DNS propagates
   - Check: `curl -v https://mcp.yourdomain.com`

### CORS Errors

**Symptoms:**
- Browser shows CORS errors
- "Access-Control-Allow-Origin" errors
- Requests blocked by browser

**Solutions:**

1. **Configure CORS Origins:**
   ```bash
   railway variables set CORS_ORIGINS=https://yourapp.com,https://app.yourapp.com
   ```

2. **Enable CORS:**
   ```bash
   railway variables set CORS_ENABLED=true
   ```

3. **Allow All Origins (Development Only):**
   ```bash
   railway variables set CORS_ORIGINS=*
   ```
   
   **Warning:** Only use `*` for development, not production

4. **Check Preflight Requests:**
   - Ensure OPTIONS requests are handled
   - Verify CORS headers in response

## Getting Help

### Before Asking for Help

Complete this checklist:

- [ ] Checked Railway status page: [status.railway.app](https://status.railway.app)
- [ ] Reviewed all environment variables
- [ ] Verified volume is mounted correctly
- [ ] Checked recent logs for errors
- [ ] Tested health endpoint
- [ ] Verified authentication token
- [ ] Tried redeploying the service
- [ ] Checked Railway documentation

### Gathering Debug Information

When reporting issues, include:

1. **Environment Variables** (redact sensitive values):
   ```bash
   railway variables | sed 's/=.*/=***/'
   ```

2. **Recent Logs**:
   ```bash
   railway logs --tail 100 > logs.txt
   ```

3. **Service Status**:
   ```bash
   railway status
   ```

4. **Health Check Response**:
   ```bash
   curl -v https://your-app.railway.app/health
   ```

5. **Railway Configuration**:
   - Plan type (Hobby, Pro, etc.)
   - Volume size and mount path
   - Custom domain configuration (if applicable)

### Where to Get Help

1. **Railway Documentation**:
   - [docs.railway.app](https://docs.railway.app)
   - Comprehensive guides and references

2. **Railway Discord**:
   - [discord.gg/railway](https://discord.gg/railway)
   - Active community and Railway team

3. **Railway Support**:
   - help@railway.app
   - For account and billing issues

4. **Project Repository**:
   - GitHub Issues
   - For server-specific problems

5. **Railway Status**:
   - [status.railway.app](https://status.railway.app)
   - Check for ongoing incidents

### Common Error Messages

| Error Message | Likely Cause | Solution |
|--------------|--------------|----------|
| "Address already in use" | Port binding issue | Remove HTTP_PORT variable |
| "No space left on device" | Volume full | Run workspace cleanup |
| "Authentication failed" | Invalid token | Verify MCP_AUTH_TOKEN |
| "Not a git repository" | Invalid repo path | Check repository URL |
| "Permission denied" | File permissions | Check Dockerfile user permissions |
| "Connection refused" | Service not running | Check logs, redeploy |
| "Health check failed" | Slow startup | Optimize initialization |
| "Module not found" | Missing dependency | Check pyproject.toml |

## Best Practices

### Preventive Measures

1. **Regular Monitoring**:
   - Check logs daily
   - Monitor volume usage weekly
   - Review metrics regularly

2. **Automated Cleanup**:
   - Set up scheduled workspace cleanup
   - Monitor disk space proactively

3. **Security**:
   - Rotate auth tokens monthly
   - Use strong, random tokens
   - Restrict CORS origins in production

4. **Documentation**:
   - Document your configuration
   - Keep track of environment variables
   - Note any custom modifications

5. **Testing**:
   - Test after each deployment
   - Verify all endpoints work
   - Check Git operations

### Maintenance Checklist

**Weekly:**
- [ ] Check service health
- [ ] Review logs for errors
- [ ] Monitor volume usage
- [ ] Verify Git operations work

**Monthly:**
- [ ] Rotate authentication token
- [ ] Clean up workspace
- [ ] Review and update dependencies
- [ ] Check Railway billing

**Quarterly:**
- [ ] Review security configuration
- [ ] Audit environment variables
- [ ] Update documentation
- [ ] Test disaster recovery

## Quick Reference

### Essential Commands

```bash
# View logs
railway logs --tail 100
railway logs --follow

# Check variables
railway variables

# Set variable
railway variables set KEY=value

# Redeploy
railway up --detach

# Check status
railway status

# Open dashboard
railway open
```

### Essential Endpoints

```bash
# Health check
curl https://your-app.railway.app/health

# Workspace info
curl -H "Authorization: Bearer token" \
  https://your-app.railway.app/workspace/info

# Cleanup
curl -X POST -H "Authorization: Bearer token" \
  https://your-app.railway.app/workspace/cleanup

# Metrics
curl https://your-app.railway.app/metrics
```

### Essential Variables

```bash
# Required
TRANSPORT_MODE=http
MCP_AUTH_TOKEN=<secure-token>
WORKSPACE_DIR=/data/git-workspaces

# Common
LOG_LEVEL=INFO
CORS_ORIGINS=*
GIT_USERNAME=<username>
GIT_TOKEN=<token>
```

## Conclusion

This troubleshooting guide covers the most common issues encountered when deploying and running the Git Commit MCP Server on Railway. For additional help, refer to the [Railway Deployment Guide](railway-deployment.md) or reach out to the community.

Remember:
- Check logs first
- Verify environment variables
- Test endpoints manually
- Monitor resource usage
- Keep documentation updated

Happy deploying! 🚀
