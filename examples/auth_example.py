"""Example usage of the authentication module.

This example demonstrates how to use the TokenValidator and RateLimiter
classes for authentication and rate limiting in the Git Commit MCP Server.
"""

from git_commit_mcp.auth import TokenValidator, RateLimiter, verify_token

# Example 1: Simple bearer token validation
print("=== Example 1: Bearer Token Validation ===")
validator = TokenValidator(secret_key="my-secret-token-123")

# Valid token
is_valid, payload, error = validator.validate_token("my-secret-token-123", use_jwt=False)
print(f"Valid token: {is_valid}, Error: {error}")

# Invalid token
is_valid, payload, error = validator.validate_token("wrong-token", use_jwt=False)
print(f"Invalid token: {is_valid}, Error: {error}")

# Example 2: JWT token validation (requires PyJWT)
print("\n=== Example 2: JWT Token Validation ===")
try:
    # Generate a JWT token
    jwt_token = TokenValidator.generate_jwt_token(
        payload={"user_id": "123", "role": "admin"},
        secret_key="jwt-secret-key",
        expires_in_seconds=3600  # 1 hour
    )
    
    if jwt_token:
        print(f"Generated JWT: {jwt_token[:50]}...")
        
        # Validate the JWT token
        jwt_validator = TokenValidator(secret_key="jwt-secret-key")
        is_valid, payload, error = jwt_validator.validate_jwt_token(jwt_token)
        print(f"Valid JWT: {is_valid}, Payload: {payload}, Error: {error}")
    else:
        print("JWT library not available")
except Exception as e:
    print(f"JWT example failed: {e}")

# Example 3: Rate limiting
print("\n=== Example 3: Rate Limiting ===")
rate_limiter = RateLimiter(capacity=5.0, refill_rate=1.0)  # 5 requests, refill 1/sec
validator_with_rate_limit = TokenValidator(
    secret_key="my-secret-token-123",
    rate_limiter=rate_limiter
)

# Simulate multiple requests from the same client
client_id = "client-123"
for i in range(7):
    allowed, wait_time = validator_with_rate_limit.check_rate_limit(client_id)
    if allowed:
        print(f"Request {i+1}: Allowed")
    else:
        print(f"Request {i+1}: Rate limited (wait {wait_time:.2f}s)")

# Example 4: Using verify_token function (for FastAPI integration)
print("\n=== Example 4: verify_token Function ===")
validator = TokenValidator(secret_key="api-token-456")

# Valid authorization header
auth_header = "Bearer api-token-456"
is_valid, payload, error = verify_token(auth_header, validator, use_jwt=False, check_rate_limit=False)
print(f"Valid auth header: {is_valid}, Error: {error}")

# Missing authorization header
is_valid, payload, error = verify_token(None, validator, use_jwt=False, check_rate_limit=False)
print(f"Missing auth header: {is_valid}, Error: {error}")

# Invalid format
auth_header = "InvalidFormat token"
is_valid, payload, error = verify_token(auth_header, validator, use_jwt=False, check_rate_limit=False)
print(f"Invalid format: {is_valid}, Error: {error}")

print("\n=== Examples Complete ===")
