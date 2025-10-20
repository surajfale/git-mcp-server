"""Authentication and security module for Git Commit MCP Server.

This module provides authentication mechanisms including bearer token validation,
JWT token support with expiration checking, and rate limiting using the token
bucket algorithm.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from threading import Lock

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting.
    
    Implements the token bucket algorithm for rate limiting requests.
    Each bucket has a capacity and refill rate.
    
    Attributes:
        capacity: Maximum number of tokens in the bucket
        tokens: Current number of available tokens
        refill_rate: Number of tokens added per second
        last_refill: Timestamp of last refill operation
    """
    capacity: float
    tokens: float
    refill_rate: float
    last_refill: float = field(default_factory=time.time)
    
    def consume(self, tokens: float = 1.0) -> bool:
        """Attempt to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time and refill rate
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_wait_time(self, tokens: float = 1.0) -> float:
        """Calculate time to wait until enough tokens are available.
        
        Args:
            tokens: Number of tokens needed
            
        Returns:
            Seconds to wait, or 0 if tokens are available now
        """
        self._refill()
        
        if self.tokens >= tokens:
            return 0.0
        
        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """Rate limiter using token bucket algorithm.
    
    Manages rate limits per client identifier (e.g., token, IP address).
    Thread-safe implementation using locks.
    
    Attributes:
        capacity: Maximum requests allowed in bucket
        refill_rate: Requests per second refill rate
        buckets: Dictionary mapping client IDs to their buckets
        lock: Thread lock for concurrent access
    """
    
    def __init__(self, capacity: float = 100.0, refill_rate: float = 10.0):
        """Initialize rate limiter.
        
        Args:
            capacity: Maximum number of requests in bucket (default: 100)
            refill_rate: Requests per second to add to bucket (default: 10)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: Dict[str, RateLimitBucket] = {}
        self.lock = Lock()
    
    def check_rate_limit(self, client_id: str, tokens: float = 1.0) -> Tuple[bool, float]:
        """Check if request is within rate limit.
        
        Args:
            client_id: Unique identifier for the client
            tokens: Number of tokens to consume (default: 1.0)
            
        Returns:
            Tuple of (allowed, wait_time) where:
                - allowed: True if request is allowed
                - wait_time: Seconds to wait if not allowed, 0 if allowed
        """
        with self.lock:
            # Get or create bucket for this client
            if client_id not in self.buckets:
                self.buckets[client_id] = RateLimitBucket(
                    capacity=self.capacity,
                    tokens=self.capacity,
                    refill_rate=self.refill_rate
                )
            
            bucket = self.buckets[client_id]
            
            # Try to consume tokens
            if bucket.consume(tokens):
                return True, 0.0
            else:
                wait_time = bucket.get_wait_time(tokens)
                return False, wait_time
    
    def reset_client(self, client_id: str) -> None:
        """Reset rate limit for a specific client.
        
        Args:
            client_id: Unique identifier for the client
        """
        with self.lock:
            if client_id in self.buckets:
                del self.buckets[client_id]
    
    def cleanup_old_buckets(self, max_age_seconds: float = 3600.0) -> None:
        """Remove buckets that haven't been used recently.
        
        Args:
            max_age_seconds: Maximum age in seconds before cleanup (default: 1 hour)
        """
        now = time.time()
        with self.lock:
            # Find buckets to remove
            to_remove = [
                client_id
                for client_id, bucket in self.buckets.items()
                if now - bucket.last_refill > max_age_seconds
            ]
            
            # Remove old buckets
            for client_id in to_remove:
                del self.buckets[client_id]


class TokenValidator:
    """Validator for bearer tokens and JWT tokens.
    
    Supports both simple bearer token validation and JWT token validation
    with expiration checking.
    
    Attributes:
        secret_key: Secret key for JWT validation
        algorithm: JWT algorithm (default: HS256)
        rate_limiter: Optional rate limiter instance
    """
    
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        rate_limiter: Optional[RateLimiter] = None
    ):
        """Initialize token validator.
        
        Args:
            secret_key: Secret key for JWT validation or bearer token
            algorithm: JWT algorithm to use (default: HS256)
            rate_limiter: Optional rate limiter instance
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.rate_limiter = rate_limiter
    
    def validate_bearer_token(self, token: str) -> bool:
        """Validate a simple bearer token.
        
        Args:
            token: Bearer token to validate
            
        Returns:
            True if token matches secret key, False otherwise
        """
        return token == self.secret_key
    
    def validate_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate a JWT token with expiration checking.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Tuple of (valid, payload, error) where:
                - valid: True if token is valid
                - payload: Decoded token payload if valid, None otherwise
                - error: Error message if invalid, None otherwise
        """
        if not JWT_AVAILABLE:
            return False, None, "JWT library not available"
        
        try:
            # Decode and validate token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check expiration
            if "exp" in payload:
                exp_timestamp = payload["exp"]
                if datetime.now(timezone.utc).timestamp() > exp_timestamp:
                    return False, None, "Token has expired"
            
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, None, f"Token validation error: {str(e)}"
    
    def validate_token(
        self,
        token: str,
        use_jwt: bool = False
    ) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """Validate a token (bearer or JWT).
        
        Args:
            token: Token to validate
            use_jwt: If True, validate as JWT; otherwise as bearer token
            
        Returns:
            Tuple of (valid, payload, error) where:
                - valid: True if token is valid
                - payload: Decoded token payload for JWT, None for bearer
                - error: Error message if invalid, None otherwise
        """
        if use_jwt:
            return self.validate_jwt_token(token)
        else:
            is_valid = self.validate_bearer_token(token)
            if is_valid:
                return True, None, None
            else:
                return False, None, "Invalid bearer token"
    
    def check_rate_limit(self, client_id: str) -> Tuple[bool, float]:
        """Check rate limit for a client.
        
        Args:
            client_id: Unique identifier for the client
            
        Returns:
            Tuple of (allowed, wait_time) where:
                - allowed: True if request is allowed
                - wait_time: Seconds to wait if not allowed, 0 if allowed
        """
        if self.rate_limiter:
            return self.rate_limiter.check_rate_limit(client_id)
        else:
            # No rate limiting configured
            return True, 0.0
    
    @staticmethod
    def generate_jwt_token(
        payload: Dict,
        secret_key: str,
        algorithm: str = "HS256",
        expires_in_seconds: int = 3600
    ) -> Optional[str]:
        """Generate a JWT token with expiration.
        
        Args:
            payload: Data to encode in the token
            secret_key: Secret key for signing
            algorithm: JWT algorithm to use (default: HS256)
            expires_in_seconds: Token expiration time in seconds (default: 1 hour)
            
        Returns:
            Encoded JWT token string, or None if JWT library not available
        """
        if not JWT_AVAILABLE:
            return None
        
        # Add expiration to payload using timezone-aware datetime
        now = datetime.now(timezone.utc)
        exp_time = now + timedelta(seconds=expires_in_seconds)
        payload_with_exp = {
            **payload,
            "exp": exp_time.timestamp(),
            "iat": now.timestamp()
        }
        
        # Encode token
        token = jwt.encode(payload_with_exp, secret_key, algorithm=algorithm)
        return token


def verify_token(
    authorization: Optional[str],
    validator: TokenValidator,
    use_jwt: bool = False,
    check_rate_limit: bool = True
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """Verify authentication token from Authorization header.
    
    This function is designed to be used as a FastAPI dependency for
    protecting endpoints with authentication.
    
    Args:
        authorization: Authorization header value (e.g., "Bearer <token>")
        validator: TokenValidator instance
        use_jwt: If True, validate as JWT; otherwise as bearer token
        check_rate_limit: If True, check rate limits
        
    Returns:
        Tuple of (valid, payload, error) where:
            - valid: True if authentication succeeded
            - payload: Token payload for JWT, None for bearer
            - error: Error message if authentication failed
    """
    # Check if authorization header is present
    if not authorization:
        return False, None, "Missing Authorization header"
    
    # Check if it's a Bearer token
    if not authorization.startswith("Bearer "):
        return False, None, "Invalid Authorization header format. Expected 'Bearer <token>'"
    
    # Extract token
    token = authorization.replace("Bearer ", "", 1).strip()
    
    if not token:
        return False, None, "Empty token"
    
    # Validate token
    valid, payload, error = validator.validate_token(token, use_jwt=use_jwt)
    
    if not valid:
        return False, None, error
    
    # Check rate limit if enabled
    if check_rate_limit:
        # Use token as client ID for rate limiting
        client_id = token[:32]  # Use first 32 chars as identifier
        allowed, wait_time = validator.check_rate_limit(client_id)
        
        if not allowed:
            return False, None, f"Rate limit exceeded. Retry after {wait_time:.1f} seconds"
    
    return True, payload, None
