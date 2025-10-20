# Authentication and Security

The Git Commit MCP Server includes a comprehensive authentication and security layer for remote deployments. This document explains how to configure and use authentication features.

## Overview

The authentication module (`src/git_commit_mcp/auth.py`) provides:

1. **Bearer Token Validation**: Simple token-based authentication
2. **JWT Token Support**: JSON Web Token validation with expiration checking
3. **Rate Limiting**: Token bucket algorithm to prevent abuse
4. **FastAPI Integration**: Ready-to-use dependency injection for endpoint protection

## Components

### TokenValidator

The `TokenValidator` class handles token validation for both bearer tokens and JWT tokens.

```python
from git_commit_mcp.auth import TokenValidator

# Create validator with secret key
validator = TokenValidator(
    secret_key="your-secret-key",
    algorithm="HS256",  # For JWT
    rate_limiter=None   # Optional rate limiter
)

# Validate bearer token
is_valid, payload, error = validator.validate_token(
    token="user-provided-token",
    use_jwt=False
)

# Validate JWT token
is_valid, payload, error = validator.validate_token(
    token="jwt-token-string",
    use_jwt=True
)
```

### RateLimiter

The `RateLimiter` class implements the token bucket algorithm for rate limiting.

```python
from git_commit_mcp.auth import RateLimiter

# Create rate limiter
# capacity: max requests in bucket
# refill_rate: requests per second to add
rate_limiter = RateLimiter(
    capacity=100.0,      # 100 requests max
    refill_rate=10.0     # Refill 10 requests/second
)

# Check rate limit for a client
allowed, wait_time = rate_limiter.check_rate_limit(
    client_id="user-123",
    tokens=1.0
)

if not allowed:
    print(f"Rate limited. Wait {wait_time} seconds")
```

### verify_token Function

The `verify_token` function is designed for FastAPI dependency injection.

```python
from git_commit_mcp.auth import verify_token, TokenValidator

validator = TokenValidator(secret_key="api-secret")

# In FastAPI endpoint
def protected_endpoint(authorization: str = Header(None)):
    is_valid, payload, error = verify_token(
        authorization=authorization,
        validator=validator,
        use_jwt=False,
        check_rate_limit=True
    )
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error)
    
    # Process request
    return {"status": "success"}
```

## Configuration

### Environment Variables

Configure authentication using environment variables:

```bash
# Enable authentication (required for HTTP mode)
AUTH_ENABLED=true

# Set authentication token
MCP_AUTH_TOKEN=your-secret-token-here

# Generate secure token:
# openssl rand -hex 32
```

### Bearer Token Authentication

For simple bearer token authentication:

1. Set `MCP_AUTH_TOKEN` environment variable
2. Clients include token in Authorization header:
   ```
   Authorization: Bearer your-secret-token-here
   ```

### JWT Authentication

For JWT token authentication (requires `pyjwt` package):

1. Install JWT support:
   ```bash
   uv pip install "git-commit-mcp-server[remote]"
   ```

2. Generate JWT tokens:
   ```python
   from git_commit_mcp.auth import TokenValidator
   
   token = TokenValidator.generate_jwt_token(
       payload={"user_id": "123", "role": "admin"},
       secret_key="jwt-secret-key",
       algorithm="HS256",
       expires_in_seconds=3600  # 1 hour
   )
   ```

3. Clients include JWT in Authorization header:
   ```
   Authorization: Bearer <jwt-token>
   ```

## Rate Limiting

Rate limiting prevents abuse by limiting requests per client:

```python
from git_commit_mcp.auth import TokenValidator, RateLimiter

# Create rate limiter
rate_limiter = RateLimiter(
    capacity=100.0,      # Max 100 requests
    refill_rate=10.0     # Refill 10/second
)

# Create validator with rate limiting
validator = TokenValidator(
    secret_key="api-secret",
    rate_limiter=rate_limiter
)

# Check rate limit
allowed, wait_time = validator.check_rate_limit("client-id")
```

### Rate Limit Configuration

Adjust rate limits based on your needs:

- **Capacity**: Maximum burst of requests allowed
- **Refill Rate**: Sustained requests per second

Examples:
- `capacity=100, refill_rate=10`: 100 burst, 10/sec sustained
- `capacity=1000, refill_rate=100`: 1000 burst, 100/sec sustained
- `capacity=10, refill_rate=1`: 10 burst, 1/sec sustained (strict)

## Security Best Practices

### Token Generation

Generate secure random tokens:

```bash
# Generate 256-bit token
openssl rand -hex 32

# Generate 512-bit token
openssl rand -hex 64
```

### Token Storage

- **Never commit tokens to version control**
- Store tokens in environment variables or secret managers
- Use different tokens for different environments
- Rotate tokens regularly

### HTTPS/TLS

Always use HTTPS in production:

```bash
TLS_ENABLED=true
TLS_CERT_PATH=/path/to/cert.pem
TLS_KEY_PATH=/path/to/key.pem
```

### CORS Configuration

Restrict CORS origins in production:

```bash
# Development (allow all)
CORS_ORIGINS=*

# Production (specific origins)
CORS_ORIGINS=https://app1.com,https://app2.com
```

### Rate Limiting

Enable rate limiting to prevent abuse:

```python
# Moderate rate limiting
rate_limiter = RateLimiter(capacity=100.0, refill_rate=10.0)

# Strict rate limiting
rate_limiter = RateLimiter(capacity=10.0, refill_rate=1.0)
```

## FastAPI Integration Example

Complete example of protecting FastAPI endpoints:

```python
from fastapi import FastAPI, Header, HTTPException, Depends
from git_commit_mcp.auth import TokenValidator, RateLimiter, verify_token
from git_commit_mcp.config import ServerConfig

app = FastAPI()

# Load configuration
config = ServerConfig.from_env()

# Create rate limiter
rate_limiter = RateLimiter(capacity=100.0, refill_rate=10.0)

# Create validator
validator = TokenValidator(
    secret_key=config.auth_token,
    rate_limiter=rate_limiter
)

# Authentication dependency
async def authenticate(authorization: str = Header(None)):
    is_valid, payload, error = verify_token(
        authorization=authorization,
        validator=validator,
        use_jwt=False,
        check_rate_limit=True
    )
    
    if not is_valid:
        raise HTTPException(status_code=401, detail=error)
    
    return payload

# Protected endpoint
@app.post("/mcp/tools/git_commit_and_push")
async def git_commit_endpoint(
    repository_path: str = ".",
    confirm_push: bool = False,
    auth_payload = Depends(authenticate)
):
    # Process authenticated request
    return {"status": "success"}

# Public health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

## Testing Authentication

Test authentication with curl:

```bash
# Valid token
curl -H "Authorization: Bearer your-secret-token" \
     http://localhost:8000/mcp/tools/git_commit_and_push

# Invalid token
curl -H "Authorization: Bearer wrong-token" \
     http://localhost:8000/mcp/tools/git_commit_and_push

# Missing token
curl http://localhost:8000/mcp/tools/git_commit_and_push
```

## Troubleshooting

### "Missing Authorization header"

Ensure the Authorization header is included:
```
Authorization: Bearer <token>
```

### "Invalid bearer token"

- Check that the token matches `MCP_AUTH_TOKEN`
- Ensure no extra whitespace in the token
- Verify the token hasn't been truncated

### "Rate limit exceeded"

- Wait for the specified time before retrying
- Reduce request frequency
- Increase rate limit capacity/refill rate if needed

### "JWT library not available"

Install JWT support:
```bash
uv pip install "git-commit-mcp-server[remote]"
```

## Additional Resources

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/) - JWT token debugger
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
