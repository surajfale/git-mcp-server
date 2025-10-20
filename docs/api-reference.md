# API Reference

This document provides comprehensive API documentation for the Git Commit MCP Server when deployed in remote mode (HTTP/SSE transport). Use this reference when integrating with the server from remote clients.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Health Check](#health-check)
  - [Git Commit and Push](#git-commit-and-push)
  - [Server-Sent Events (SSE)](#server-sent-events-sse)
  - [Workspace Information](#workspace-information)
  - [Workspace Cleanup](#workspace-cleanup)
  - [Metrics](#metrics)
- [Error Responses](#error-responses)
- [Rate Limiting](#rate-limiting)
- [Railway Deployment](#railway-deployment)
- [Client Examples](#client-examples)

## Base URL

The base URL depends on your deployment:

### Railway Deployment

**Default Railway URL:**
```
https://your-app-name.up.railway.app
```

**Custom Domain:**
```
https://mcp.yourdomain.com
```

### Self-Hosted

```
http://your-server-ip:8000
```

Or with HTTPS:
```
https://your-server-domain:8000
```

## Authentication

All API endpoints (except `/health` and `/metrics`) require authentication when `AUTH_ENABLED=true` (default for remote mode).

### Authentication Header Format

Include the authentication token in the `Authorization` header using the Bearer scheme:

```
Authorization: Bearer <your-auth-token>
```

### Example

```bash
curl -H "Authorization: Bearer abc123xyz789" \
  https://your-app.railway.app/mcp/tools/git_commit_and_push
```

### Generating Auth Tokens

Generate a secure token for `MCP_AUTH_TOKEN`:

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -base64 32

# Using Node.js
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

### Railway Configuration

Set the token in Railway environment variables:

1. Go to your Railway project
2. Navigate to Variables tab
3. Add variable: `MCP_AUTH_TOKEN=<your-generated-token>`
4. Redeploy if necessary

## Endpoints

### Health Check

Check server health and configuration status.

**Endpoint:** `GET /health`

**Authentication:** Not required

**Request:**

```bash
curl https://your-app.railway.app/health
```

**Response:**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "transport": "http",
  "auth_enabled": true,
  "metrics_enabled": true
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Server health status (`healthy` or `unhealthy`) |
| `version` | string | Server version number |
| `transport` | string | Transport mode (`http` or `stdio`) |
| `auth_enabled` | boolean | Whether authentication is enabled |
| `metrics_enabled` | boolean | Whether metrics endpoint is available |

**Use Cases:**

- Load balancer health checks
- Monitoring and alerting systems
- Deployment verification
- Railway health monitoring

---

### Git Commit and Push

Execute Git commit and optionally push to remote repository.

**Endpoint:** `POST /mcp/tools/git_commit_and_push`

**Authentication:** Required

**Request Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repository_path` | string | No | `"."` | Path to Git repository or repository URL |
| `confirm_push` | boolean | No | `false` | Whether to push to remote after committing |

**Request Headers:**

```
Authorization: Bearer <your-auth-token>
Content-Type: application/json
```

**Request Example (JSON Body):**

```bash
curl -X POST \
  -H "Authorization: Bearer abc123xyz789" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_path": ".",
    "confirm_push": true
  }' \
  https://your-app.railway.app/mcp/tools/git_commit_and_push
```

**Request Example (Query Parameters):**

```bash
curl -X POST \
  -H "Authorization: Bearer abc123xyz789" \
  "https://your-app.railway.app/mcp/tools/git_commit_and_push?repository_path=.&confirm_push=true"
```

**Success Response:**

```json
{
  "success": true,
  "commit_hash": "a1b2c3d4",
  "commit_message": "feat(api): Add user authentication\n\n- Add JWT token validation\n- Implement rate limiting\n- Add authentication middleware",
  "files_changed": 5,
  "pushed": true,
  "changelog_updated": true,
  "message": "Successfully committed and pushed 5 files"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the operation succeeded |
| `commit_hash` | string | Short commit hash (8 characters) |
| `commit_message` | string | Generated conventional commit message |
| `files_changed` | integer | Number of files included in the commit |
| `pushed` | boolean | Whether changes were pushed to remote |
| `changelog_updated` | boolean | Whether CHANGELOG.md was updated |
| `message` | string | Human-readable status message |
| `error` | string | Error message (only present if `success: false`) |

**Error Response (No Changes):**

```json
{
  "success": false,
  "commit_hash": null,
  "commit_message": null,
  "files_changed": 0,
  "pushed": false,
  "changelog_updated": false,
  "message": "No changes to commit"
}
```

**Error Response (Authentication Failed):**

```json
{
  "success": false,
  "error": "Invalid bearer token",
  "message": "Invalid bearer token"
}
```

**HTTP Status Codes:**

| Code | Description |
|------|-------------|
| `200` | Success (operation completed) |
| `401` | Unauthorized (invalid or missing auth token) |
| `429` | Too Many Requests (rate limit exceeded) |
| `500` | Internal Server Error (operation failed) |

---

### Server-Sent Events (SSE)

Establish a Server-Sent Events connection for real-time updates.

**Endpoint:** `GET /mcp/sse`

**Authentication:** Required

**Request:**

```bash
curl -H "Authorization: Bearer abc123xyz789" \
  -H "Accept: text/event-stream" \
  https://your-app.railway.app/mcp/sse
```

**Response Stream:**

```
event: connected
data: Git Commit MCP Server Ready

event: heartbeat
data: alive

event: heartbeat
data: alive
```

**Event Types:**

| Event | Description |
|-------|-------------|
| `connected` | Initial connection established |
| `heartbeat` | Periodic keepalive (every 30 seconds) |

**Use Cases:**

- Real-time server status monitoring
- Long-lived connections for streaming updates
- Future: Real-time Git operation progress

**Client Example (JavaScript):**

```javascript
const eventSource = new EventSource(
  'https://your-app.railway.app/mcp/sse',
  {
    headers: {
      'Authorization': 'Bearer abc123xyz789'
    }
  }
);

eventSource.addEventListener('connected', (event) => {
  console.log('Connected:', event.data);
});

eventSource.addEventListener('heartbeat', (event) => {
  console.log('Heartbeat:', event.data);
});

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

---

### Workspace Information

Get information about the workspace directory including size and repository count.

**Endpoint:** `GET /workspace/info`

**Authentication:** Required

**Availability:** Only available when `CLEANUP_ENABLED=true` (default) and server is in remote mode

**Request:**

```bash
curl -H "Authorization: Bearer abc123xyz789" \
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `workspace_path` | string | Absolute path to workspace directory |
| `repository_count` | integer | Number of cloned repositories |
| `total_size_mb` | float | Total size of all repositories in MB |
| `max_size_mb` | integer | Configured maximum workspace size |
| `usage_percent` | float | Percentage of max size used |
| `disk_available_mb` | float | Available disk space in MB |
| `disk_total_mb` | float | Total disk space in MB |
| `cleanup_recommended` | boolean | Whether cleanup is recommended (>80% usage) |

**Use Cases:**

- Monitor workspace disk usage
- Determine when cleanup is needed
- Track repository count
- Railway volume monitoring

---

### Workspace Cleanup

Remove all cloned repositories from the workspace to free disk space.

**Endpoint:** `POST /workspace/cleanup`

**Authentication:** Required

**Availability:** Only available when `CLEANUP_ENABLED=true` (default) and server is in remote mode

**Warning:** This operation removes all cloned repositories. They will be re-cloned on next use.

**Request:**

```bash
curl -X POST \
  -H "Authorization: Bearer abc123xyz789" \
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

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether cleanup succeeded |
| `repositories_cleaned` | integer | Number of repositories removed |
| `size_freed_mb` | float | Disk space freed in MB |
| `message` | string | Human-readable status message |

**Use Cases:**

- Free up disk space when volume is full
- Clean up after working with large repositories
- Periodic maintenance to prevent disk exhaustion
- Prepare for new deployments

**Best Practices:**

- Check `/workspace/info` before cleanup to see current usage
- Run cleanup when `cleanup_recommended: true`
- Schedule periodic cleanup (e.g., weekly via cron job)
- Monitor Railway volume usage in dashboard

---

### Metrics

Get Prometheus-compatible metrics for monitoring and observability.

**Endpoint:** `GET /metrics`

**Authentication:** Not required

**Availability:** Only available when `ENABLE_METRICS=true` (default)

**Request:**

```bash
curl https://your-app.railway.app/metrics
```

**Response Format:** Prometheus text format

**Example Response:**

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/health",method="GET",status="200"} 42.0
http_requests_total{endpoint="/mcp/tools/git_commit_and_push",method="POST",status="200"} 15.0
http_requests_total{endpoint="/mcp/tools/git_commit_and_push",method="POST",status="401"} 2.0

# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/health",method="GET",le="0.005"} 40
http_request_duration_seconds_bucket{endpoint="/health",method="GET",le="0.01"} 42
http_request_duration_seconds_bucket{endpoint="/health",method="GET",le="+Inf"} 42
http_request_duration_seconds_sum{endpoint="/health",method="GET"} 0.21
http_request_duration_seconds_count{endpoint="/health",method="GET"} 42

# HELP git_commits_total Total number of Git commits created
# TYPE git_commits_total counter
git_commits_total{status="success"} 12.0
git_commits_total{status="failure"} 1.0

# HELP git_pushes_total Total number of Git pushes attempted
# TYPE git_pushes_total counter
git_pushes_total{status="success"} 10.0
git_pushes_total{status="failure"} 2.0

# HELP git_operations_errors_total Total number of Git operation errors
# TYPE git_operations_errors_total counter
git_operations_errors_total{error_type="authentication",operation="commit_and_push"} 1.0
git_operations_errors_total{error_type="network",operation="commit_and_push"} 1.0

# HELP git_operation_duration_seconds Git operation duration in seconds
# TYPE git_operation_duration_seconds histogram
git_operation_duration_seconds_bucket{operation="commit",le="0.5"} 8
git_operation_duration_seconds_bucket{operation="commit",le="1.0"} 11
git_operation_duration_seconds_bucket{operation="commit",le="+Inf"} 12
git_operation_duration_seconds_sum{operation="commit"} 8.5
git_operation_duration_seconds_count{operation="commit"} 12

# HELP auth_attempts_total Total number of authentication attempts
# TYPE auth_attempts_total counter
auth_attempts_total{status="success"} 15.0
auth_attempts_total{status="failure"} 2.0

# HELP rate_limit_exceeded_total Total number of rate limit exceeded events
# TYPE rate_limit_exceeded_total counter
rate_limit_exceeded_total 1.0

# HELP server_info Server information
# TYPE server_info gauge
server_info{version="1.0.0"} 1.0

# HELP server_health Server health status (1 = healthy, 0 = unhealthy)
# TYPE server_health gauge
server_health 1.0
```

**Available Metrics:**

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `http_requests_total` | Counter | `method`, `endpoint`, `status` | Total HTTP requests by method, endpoint, and status code |
| `http_request_duration_seconds` | Histogram | `method`, `endpoint` | HTTP request latency distribution |
| `git_commits_total` | Counter | `status` | Total Git commits (success/failure) |
| `git_pushes_total` | Counter | `status` | Total Git pushes (success/failure) |
| `git_operations_errors_total` | Counter | `operation`, `error_type` | Git operation errors by type |
| `git_operation_duration_seconds` | Histogram | `operation` | Git operation duration distribution |
| `auth_attempts_total` | Counter | `status` | Authentication attempts (success/failure) |
| `rate_limit_exceeded_total` | Counter | - | Rate limit exceeded events |
| `server_info` | Gauge | `version` | Server version information |
| `server_health` | Gauge | - | Server health status (1=healthy, 0=unhealthy) |

**Use Cases:**

- **Prometheus Integration:** Scrape metrics for time-series monitoring
- **Grafana Dashboards:** Visualize server performance and Git operations
- **Alerting:** Set up alerts for error rates, latencies, or failures
- **Performance Tracking:** Monitor request durations and operation times
- **Capacity Planning:** Track request volumes and resource usage

**Prometheus Configuration:**

Add to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'git-commit-mcp'
    scrape_interval: 30s
    static_configs:
      - targets: ['your-app.railway.app:443']
    scheme: https
    metrics_path: /metrics
```

**Grafana Dashboard Example:**

```json
{
  "dashboard": {
    "title": "Git Commit MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Request Latency (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Git Commit Success Rate",
        "targets": [
          {
            "expr": "rate(git_commits_total{status=\"success\"}[5m]) / rate(git_commits_total[5m])"
          }
        ]
      }
    ]
  }
}
```

**Monitoring Best Practices:**

1. **Scrape Interval:** Set to 30-60 seconds for most use cases
2. **Retention:** Keep metrics for at least 30 days
3. **Alerting Rules:**
   - Alert on high error rates (>5% of requests)
   - Alert on high latencies (p95 > 5 seconds)
   - Alert on authentication failures (>10% of attempts)
   - Alert on rate limit events
4. **Dashboard Panels:**
   - Request rate and error rate over time
   - Latency percentiles (p50, p95, p99)
   - Git operation success/failure rates
   - Authentication success rate
   - Active connections (for SSE)

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "success": false,
  "error": "Error type or message",
  "message": "Human-readable error description"
}
```

### Common Error Codes

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Missing or invalid authentication token |
| `403` | Forbidden | Valid token but insufficient permissions |
| `404` | Not Found | Endpoint does not exist |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side error during operation |
| `503` | Service Unavailable | Server is temporarily unavailable |

### Authentication Errors

**Missing Authorization Header:**

```json
{
  "success": false,
  "error": "Missing Authorization header",
  "message": "Missing Authorization header"
}
```

**Invalid Token Format:**

```json
{
  "success": false,
  "error": "Invalid Authorization header format. Expected: Bearer <token>",
  "message": "Invalid Authorization header format. Expected: Bearer <token>"
}
```

**Invalid Token:**

```json
{
  "success": false,
  "error": "Invalid bearer token",
  "message": "Invalid bearer token"
}
```

### Rate Limiting Errors

**Rate Limit Exceeded:**

```json
{
  "success": false,
  "error": "Rate limit exceeded. Try again in 5.2 seconds",
  "message": "Rate limit exceeded. Try again in 5.2 seconds"
}
```

### Git Operation Errors

**Not a Git Repository:**

```json
{
  "success": false,
  "error": "Not a git repository",
  "message": "The specified path is not a valid Git repository"
}
```

**Push Failed (No Remote):**

```json
{
  "success": true,
  "commit_hash": "a1b2c3d4",
  "commit_message": "feat: Add new feature",
  "files_changed": 3,
  "pushed": false,
  "changelog_updated": true,
  "message": "Committed successfully but no remote configured for push"
}
```

**Push Failed (Authentication):**

```json
{
  "success": false,
  "error": "Git authentication failed",
  "message": "Failed to push: Authentication required. Configure GIT_USERNAME and GIT_TOKEN"
}
```

---

## Rate Limiting

The server implements token bucket rate limiting to prevent abuse.

### Default Limits

- **Capacity:** 100 requests (burst)
- **Refill Rate:** 10 requests per second (sustained)

### Rate Limit Headers

Future implementation will include rate limit headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1634567890
```

### Handling Rate Limits

When rate limited, wait for the specified time before retrying:

```python
import time
import requests

response = requests.post(url, headers=headers, json=data)

if response.status_code == 429:
    error_data = response.json()
    # Extract wait time from error message
    # "Rate limit exceeded. Try again in 5.2 seconds"
    wait_time = 5.2  # Parse from message
    time.sleep(wait_time)
    # Retry request
    response = requests.post(url, headers=headers, json=data)
```

### Adjusting Rate Limits

Rate limits can be configured in the server code by modifying the `RateLimiter` initialization in `http_server.py`.

---

## Railway Deployment

### Railway URL Format

Railway provides automatic URLs in the format:

```
https://<service-name>-production-<random-id>.up.railway.app
```

Example:
```
https://git-commit-mcp-production-a1b2.up.railway.app
```

### Custom Domain Setup

1. **Add Domain in Railway:**
   - Go to your Railway project
   - Navigate to Settings → Domains
   - Click "Add Domain"
   - Enter your domain (e.g., `mcp.yourdomain.com`)

2. **Configure DNS:**
   - Add CNAME record to your DNS provider:
     ```
     Type: CNAME
     Name: mcp
     Value: <your-app>.up.railway.app
     ```

3. **Wait for SSL:**
   - Railway automatically provisions SSL certificate
   - Usually takes 5-15 minutes
   - Certificate auto-renews

4. **Verify:**
   ```bash
   curl https://mcp.yourdomain.com/health
   ```

### Railway Environment Variables

Configure these in Railway dashboard:

**Required:**
```bash
TRANSPORT_MODE=http
MCP_AUTH_TOKEN=<your-secure-token>
WORKSPACE_DIR=/data/git-workspaces
```

**Optional:**
```bash
# Git authentication
GIT_USERNAME=<github-username>
GIT_TOKEN=<github-token>

# CORS configuration
CORS_ORIGINS=https://app1.com,https://app2.com

# Logging
LOG_LEVEL=INFO

# Workspace limits
MAX_WORKSPACE_SIZE_MB=1000
CLEANUP_ENABLED=true
```

### Railway Health Checks

Railway monitors the `/health` endpoint:

- **Interval:** Every 30 seconds
- **Timeout:** 10 seconds
- **Retries:** 3 attempts before marking unhealthy

If health checks fail, Railway will:
1. Mark service as unhealthy
2. Attempt automatic restart
3. Send notifications (if configured)

### Railway Volume Configuration

For persistent storage:

1. **Create Volume:**
   - Name: `git-workspaces`
   - Mount Path: `/data`
   - Size: 2-5 GB

2. **Set Environment Variable:**
   ```bash
   WORKSPACE_DIR=/data/git-workspaces
   ```

3. **Monitor Usage:**
   ```bash
   curl -H "Authorization: Bearer <token>" \
     https://your-app.railway.app/workspace/info
   ```

---

## Client Examples

### Python

```python
import requests

class GitCommitMCPClient:
    def __init__(self, base_url: str, auth_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    
    def health_check(self):
        """Check server health."""
        response = requests.get(f'{self.base_url}/health')
        return response.json()
    
    def commit_and_push(self, repository_path: str = ".", confirm_push: bool = False):
        """Execute git commit and optionally push."""
        data = {
            'repository_path': repository_path,
            'confirm_push': confirm_push
        }
        response = requests.post(
            f'{self.base_url}/mcp/tools/git_commit_and_push',
            headers=self.headers,
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def workspace_info(self):
        """Get workspace information."""
        response = requests.get(
            f'{self.base_url}/workspace/info',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def workspace_cleanup(self):
        """Clean up workspace."""
        response = requests.post(
            f'{self.base_url}/workspace/cleanup',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = GitCommitMCPClient(
    base_url='https://your-app.railway.app',
    auth_token='your-auth-token'
)

# Check health
health = client.health_check()
print(f"Server status: {health['status']}")

# Commit and push
result = client.commit_and_push(confirm_push=True)
if result['success']:
    print(f"Committed: {result['commit_hash']}")
    print(f"Files changed: {result['files_changed']}")
    print(f"Pushed: {result['pushed']}")
else:
    print(f"Error: {result['message']}")

# Check workspace
info = client.workspace_info()
print(f"Repositories: {info['repository_count']}")
print(f"Usage: {info['usage_percent']}%")

# Cleanup if needed
if info['cleanup_recommended']:
    cleanup_result = client.workspace_cleanup()
    print(f"Cleaned up: {cleanup_result['size_freed_mb']} MB")
```

### JavaScript/TypeScript

```typescript
class GitCommitMCPClient {
  private baseUrl: string;
  private authToken: string;

  constructor(baseUrl: string, authToken: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.authToken = authToken;
  }

  private async request(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.authToken}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Request failed');
    }

    return response.json();
  }

  async healthCheck() {
    const response = await fetch(`${this.baseUrl}/health`);
    return response.json();
  }

  async commitAndPush(
    repositoryPath: string = '.',
    confirmPush: boolean = false
  ) {
    return this.request('/mcp/tools/git_commit_and_push', {
      method: 'POST',
      body: JSON.stringify({
        repository_path: repositoryPath,
        confirm_push: confirmPush,
      }),
    });
  }

  async workspaceInfo() {
    return this.request('/workspace/info');
  }

  async workspaceCleanup() {
    return this.request('/workspace/cleanup', { method: 'POST' });
  }
}

// Usage
const client = new GitCommitMCPClient(
  'https://your-app.railway.app',
  'your-auth-token'
);

// Check health
const health = await client.healthCheck();
console.log(`Server status: ${health.status}`);

// Commit and push
const result = await client.commitAndPush('.', true);
if (result.success) {
  console.log(`Committed: ${result.commit_hash}`);
  console.log(`Files changed: ${result.files_changed}`);
  console.log(`Pushed: ${result.pushed}`);
} else {
  console.error(`Error: ${result.message}`);
}

// Check workspace
const info = await client.workspaceInfo();
console.log(`Repositories: ${info.repository_count}`);
console.log(`Usage: ${info.usage_percent}%`);

// Cleanup if needed
if (info.cleanup_recommended) {
  const cleanupResult = await client.workspaceCleanup();
  console.log(`Cleaned up: ${cleanupResult.size_freed_mb} MB`);
}
```

### cURL

```bash
#!/bin/bash

# Configuration
BASE_URL="https://your-app.railway.app"
AUTH_TOKEN="your-auth-token"

# Health check
echo "Checking server health..."
curl -s "${BASE_URL}/health" | jq

# Commit and push
echo -e "\nCommitting and pushing changes..."
curl -s -X POST \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"repository_path": ".", "confirm_push": true}' \
  "${BASE_URL}/mcp/tools/git_commit_and_push" | jq

# Workspace info
echo -e "\nChecking workspace info..."
curl -s \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  "${BASE_URL}/workspace/info" | jq

# Cleanup (if needed)
echo -e "\nCleaning up workspace..."
curl -s -X POST \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  "${BASE_URL}/workspace/cleanup" | jq
```

### MCP Client Configuration

For MCP-compatible clients (e.g., Claude Desktop, Cline):

```json
{
  "mcpServers": {
    "git-commit-remote": {
      "url": "https://your-app.railway.app",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer your-auth-token"
      }
    }
  }
}
```

---

## Best Practices

### Security

1. **Use HTTPS:** Always use HTTPS in production (Railway provides this automatically)
2. **Secure Tokens:** Generate cryptographically secure tokens (32+ bytes)
3. **Rotate Tokens:** Periodically update `MCP_AUTH_TOKEN`
4. **Restrict CORS:** Set specific origins instead of `*` in production
5. **Monitor Access:** Review logs for unauthorized access attempts

### Performance

1. **Monitor Workspace:** Check `/workspace/info` regularly
2. **Cleanup Regularly:** Run cleanup when usage exceeds 80%
3. **Use Appropriate Volume Size:** Start with 2-5 GB, scale as needed
4. **Cache Repositories:** Persistent volumes cache cloned repos for faster operations

### Reliability

1. **Monitor Health:** Set up alerts for `/health` endpoint failures
2. **Handle Rate Limits:** Implement exponential backoff for retries
3. **Check Responses:** Always verify `success` field in responses
4. **Log Operations:** Log all API calls for debugging and auditing

### Cost Optimization

1. **Right-Size Volume:** Don't over-provision storage
2. **Implement Cleanup:** Remove unused repositories to save space
3. **Monitor Usage:** Track Railway usage dashboard
4. **Use Hobby Plan:** Sufficient for most use cases ($5/month)

---

## Troubleshooting

### Authentication Issues

**Problem:** 401 Unauthorized errors

**Solutions:**
- Verify `MCP_AUTH_TOKEN` is set in Railway
- Check Authorization header format: `Bearer <token>`
- Ensure token matches exactly (no extra spaces)
- Verify `AUTH_ENABLED=true` in configuration

### Connection Issues

**Problem:** Cannot connect to server

**Solutions:**
- Verify Railway service is running (check dashboard)
- Test health endpoint: `curl https://your-app.railway.app/health`
- Check Railway logs for errors
- Verify DNS configuration (if using custom domain)

### Workspace Issues

**Problem:** Disk space errors

**Solutions:**
- Check workspace usage: `GET /workspace/info`
- Run cleanup: `POST /workspace/cleanup`
- Increase Railway volume size
- Monitor volume usage in Railway dashboard

### Rate Limiting

**Problem:** 429 Too Many Requests

**Solutions:**
- Implement exponential backoff
- Reduce request frequency
- Wait for time specified in error message
- Consider increasing rate limits in server configuration

---

## Additional Resources

- [Railway Deployment Guide](./railway-deployment.md)
- [Railway Troubleshooting](./railway-troubleshooting.md)
- [Authentication Documentation](./authentication.md)
- [Railway Documentation](https://docs.railway.app)
- [FastAPI Documentation](https://fastapi.tiangolo.com)

---

## Support

For issues and questions:

1. Check [Railway Troubleshooting Guide](./railway-troubleshooting.md)
2. Review Railway logs: `railway logs`
3. Test health endpoint: `curl https://your-app.railway.app/health`
4. Open an issue on the GitHub repository

---

**Last Updated:** 2025-10-20  
**API Version:** 1.0.0
