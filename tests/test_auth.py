"""Unit tests for authentication and security module."""

import time
from datetime import datetime, timedelta

import pytest

from git_commit_mcp.auth import (
    RateLimitBucket,
    RateLimiter,
    TokenValidator,
    verify_token,
)

# Check if JWT is available
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False


class TestRateLimitBucket:
    """Tests for RateLimitBucket token bucket implementation."""
    
    def test_bucket_initialization(self):
        """Test that bucket initializes with correct values."""
        bucket = RateLimitBucket(capacity=100.0, tokens=100.0, refill_rate=10.0)
        
        assert bucket.capacity == 100.0
        assert bucket.tokens == 100.0
        assert bucket.refill_rate == 10.0
        assert bucket.last_refill > 0
    
    def test_consume_tokens_success(self):
        """Test consuming tokens when sufficient tokens available."""
        bucket = RateLimitBucket(capacity=100.0, tokens=100.0, refill_rate=10.0)
        
        result = bucket.consume(10.0)
        
        assert result is True
        assert bucket.tokens == 90.0
    
    def test_consume_tokens_failure(self):
        """Test consuming tokens when insufficient tokens available."""
        bucket = RateLimitBucket(capacity=100.0, tokens=5.0, refill_rate=10.0)
        
        result = bucket.consume(10.0)
        
        assert result is False
        # Tokens may have slightly increased due to refill during consume
        assert bucket.tokens < 10.0  # Still insufficient
    
    def test_consume_exact_tokens(self):
        """Test consuming exact number of available tokens."""
        bucket = RateLimitBucket(capacity=100.0, tokens=10.0, refill_rate=10.0)
        
        result = bucket.consume(10.0)
        
        assert result is True
        # Tokens may have slightly increased due to refill, but should be close to 0
        assert bucket.tokens < 1.0
    
    def test_refill_tokens_over_time(self):
        """Test that tokens refill based on elapsed time."""
        bucket = RateLimitBucket(capacity=100.0, tokens=50.0, refill_rate=10.0)
        initial_time = bucket.last_refill
        
        # Simulate 2 seconds passing
        time.sleep(0.2)  # Sleep for 0.2 seconds
        bucket._refill()
        
        # Should have added approximately 2 tokens (0.2 seconds * 10 tokens/sec)
        assert bucket.tokens > 50.0
        assert bucket.tokens <= 53.0  # Allow some tolerance for timing variations
        assert bucket.last_refill > initial_time
    
    def test_refill_does_not_exceed_capacity(self):
        """Test that refill does not exceed bucket capacity."""
        bucket = RateLimitBucket(capacity=100.0, tokens=95.0, refill_rate=10.0)
        
        # Simulate 10 seconds passing (would add 100 tokens)
        time.sleep(0.1)
        bucket._refill()
        
        # Should not exceed capacity
        assert bucket.tokens <= 100.0
    
    def test_get_wait_time_tokens_available(self):
        """Test wait time calculation when tokens are available."""
        bucket = RateLimitBucket(capacity=100.0, tokens=50.0, refill_rate=10.0)
        
        wait_time = bucket.get_wait_time(10.0)
        
        assert wait_time == 0.0
    
    def test_get_wait_time_tokens_needed(self):
        """Test wait time calculation when tokens are needed."""
        bucket = RateLimitBucket(capacity=100.0, tokens=5.0, refill_rate=10.0)
        
        wait_time = bucket.get_wait_time(15.0)
        
        # Need 10 more tokens, at 10 tokens/sec = 1 second
        assert wait_time == pytest.approx(1.0, rel=0.1)


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test that rate limiter initializes correctly."""
        limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        
        assert limiter.capacity == 100.0
        assert limiter.refill_rate == 10.0
        assert len(limiter.buckets) == 0
    
    def test_check_rate_limit_first_request(self):
        """Test rate limit check for first request from client."""
        limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        
        allowed, wait_time = limiter.check_rate_limit("client1")
        
        assert allowed is True
        assert wait_time == 0.0
        assert "client1" in limiter.buckets
    
    def test_check_rate_limit_multiple_requests(self):
        """Test rate limit check for multiple requests."""
        limiter = RateLimiter(capacity=10.0, refill_rate=1.0)
        
        # Make 10 requests (should all succeed)
        for i in range(10):
            allowed, wait_time = limiter.check_rate_limit("client1")
            assert allowed is True
            assert wait_time == 0.0
        
        # 11th request should fail
        allowed, wait_time = limiter.check_rate_limit("client1")
        assert allowed is False
        assert wait_time > 0.0
    
    def test_check_rate_limit_different_clients(self):
        """Test that different clients have separate rate limits."""
        limiter = RateLimiter(capacity=5.0, refill_rate=1.0)
        
        # Client 1 uses all tokens
        for i in range(5):
            allowed, _ = limiter.check_rate_limit("client1")
            assert allowed is True
        
        # Client 1 should be rate limited
        allowed, _ = limiter.check_rate_limit("client1")
        assert allowed is False
        
        # Client 2 should still have tokens
        allowed, _ = limiter.check_rate_limit("client2")
        assert allowed is True
    
    def test_reset_client(self):
        """Test resetting rate limit for a client."""
        limiter = RateLimiter(capacity=5.0, refill_rate=1.0)
        
        # Use all tokens
        for i in range(5):
            limiter.check_rate_limit("client1")
        
        # Should be rate limited
        allowed, _ = limiter.check_rate_limit("client1")
        assert allowed is False
        
        # Reset client
        limiter.reset_client("client1")
        
        # Should have full tokens again
        allowed, _ = limiter.check_rate_limit("client1")
        assert allowed is True
    
    def test_cleanup_old_buckets(self):
        """Test cleanup of old unused buckets."""
        limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        
        # Create buckets for multiple clients
        limiter.check_rate_limit("client1")
        limiter.check_rate_limit("client2")
        limiter.check_rate_limit("client3")
        
        assert len(limiter.buckets) == 3
        
        # Manually age one bucket
        limiter.buckets["client1"].last_refill = time.time() - 7200  # 2 hours ago
        
        # Cleanup buckets older than 1 hour
        limiter.cleanup_old_buckets(max_age_seconds=3600.0)
        
        assert len(limiter.buckets) == 2
        assert "client1" not in limiter.buckets
        assert "client2" in limiter.buckets
        assert "client3" in limiter.buckets
    
    def test_thread_safety(self):
        """Test that rate limiter is thread-safe."""
        import threading
        
        limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        results = []
        
        def make_requests():
            for _ in range(10):
                allowed, _ = limiter.check_rate_limit("client1")
                results.append(allowed)
        
        # Create multiple threads
        threads = [threading.Thread(target=make_requests) for _ in range(5)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All 50 requests should have been processed
        assert len(results) == 50


class TestTokenValidator:
    """Tests for TokenValidator class."""
    
    def test_validator_initialization(self):
        """Test that validator initializes correctly."""
        validator = TokenValidator(secret_key="test-secret")
        
        assert validator.secret_key == "test-secret"
        assert validator.algorithm == "HS256"
        assert validator.rate_limiter is None
    
    def test_validator_with_rate_limiter(self):
        """Test validator initialization with rate limiter."""
        limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        validator = TokenValidator(secret_key="test-secret", rate_limiter=limiter)
        
        assert validator.rate_limiter is limiter
    
    def test_validate_bearer_token_success(self):
        """Test bearer token validation with correct token."""
        validator = TokenValidator(secret_key="my-secret-token")
        
        result = validator.validate_bearer_token("my-secret-token")
        
        assert result is True
    
    def test_validate_bearer_token_failure(self):
        """Test bearer token validation with incorrect token."""
        validator = TokenValidator(secret_key="my-secret-token")
        
        result = validator.validate_bearer_token("wrong-token")
        
        assert result is False
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_validate_jwt_token_success(self):
        """Test JWT token validation with valid token."""
        secret = "test-secret"
        validator = TokenValidator(secret_key=secret)
        
        # Generate a valid token
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key=secret,
            expires_in_seconds=3600
        )
        
        valid, payload, error = validator.validate_jwt_token(token)
        
        assert valid is True
        assert payload is not None
        assert payload["user"] == "test"
        assert error is None
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_validate_jwt_token_expired(self):
        """Test JWT token validation with expired token."""
        secret = "test-secret"
        validator = TokenValidator(secret_key=secret)
        
        # Generate an expired token
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key=secret,
            expires_in_seconds=-1  # Already expired
        )
        
        valid, payload, error = validator.validate_jwt_token(token)
        
        assert valid is False
        assert payload is None
        assert "expired" in error.lower()
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_validate_jwt_token_invalid_signature(self):
        """Test JWT token validation with invalid signature."""
        validator = TokenValidator(secret_key="correct-secret")
        
        # Generate token with different secret
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key="wrong-secret",
            expires_in_seconds=3600
        )
        
        valid, payload, error = validator.validate_jwt_token(token)
        
        assert valid is False
        assert payload is None
        assert error is not None
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_validate_jwt_token_malformed(self):
        """Test JWT token validation with malformed token."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = validator.validate_jwt_token("not-a-valid-jwt")
        
        assert valid is False
        assert payload is None
        assert error is not None
    
    @pytest.mark.skipif(JWT_AVAILABLE, reason="Test for when JWT is not available")
    def test_validate_jwt_token_no_jwt_library(self):
        """Test JWT validation when JWT library is not available."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = validator.validate_jwt_token("any-token")
        
        assert valid is False
        assert payload is None
        assert "not available" in error.lower()
    
    def test_validate_token_bearer_mode(self):
        """Test validate_token in bearer mode."""
        validator = TokenValidator(secret_key="my-secret")
        
        valid, payload, error = validator.validate_token("my-secret", use_jwt=False)
        
        assert valid is True
        assert payload is None
        assert error is None
    
    def test_validate_token_bearer_mode_failure(self):
        """Test validate_token in bearer mode with wrong token."""
        validator = TokenValidator(secret_key="my-secret")
        
        valid, payload, error = validator.validate_token("wrong-token", use_jwt=False)
        
        assert valid is False
        assert payload is None
        assert "Invalid bearer token" in error
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_validate_token_jwt_mode(self):
        """Test validate_token in JWT mode."""
        secret = "test-secret"
        validator = TokenValidator(secret_key=secret)
        
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key=secret,
            expires_in_seconds=3600
        )
        
        valid, payload, error = validator.validate_token(token, use_jwt=True)
        
        assert valid is True
        assert payload is not None
        assert error is None
    
    def test_check_rate_limit_no_limiter(self):
        """Test rate limit check when no limiter is configured."""
        validator = TokenValidator(secret_key="test-secret")
        
        allowed, wait_time = validator.check_rate_limit("client1")
        
        assert allowed is True
        assert wait_time == 0.0
    
    def test_check_rate_limit_with_limiter(self):
        """Test rate limit check with configured limiter."""
        limiter = RateLimiter(capacity=5.0, refill_rate=1.0)
        validator = TokenValidator(secret_key="test-secret", rate_limiter=limiter)
        
        # Make 5 requests (should succeed)
        for _ in range(5):
            allowed, wait_time = validator.check_rate_limit("client1")
            assert allowed is True
        
        # 6th request should fail
        allowed, wait_time = validator.check_rate_limit("client1")
        assert allowed is False
        assert wait_time > 0.0
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_generate_jwt_token(self):
        """Test JWT token generation."""
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test", "role": "admin"},
            secret_key="test-secret",
            expires_in_seconds=3600
        )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        decoded = jwt.decode(token, "test-secret", algorithms=["HS256"])
        assert decoded["user"] == "test"
        assert decoded["role"] == "admin"
        assert "exp" in decoded
        assert "iat" in decoded
    
    @pytest.mark.skipif(JWT_AVAILABLE, reason="Test for when JWT is not available")
    def test_generate_jwt_token_no_library(self):
        """Test JWT token generation when library not available."""
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key="test-secret"
        )
        
        assert token is None


class TestVerifyToken:
    """Tests for verify_token function."""
    
    def test_verify_token_missing_header(self):
        """Test token verification with missing Authorization header."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = verify_token(None, validator)
        
        assert valid is False
        assert payload is None
        assert "Missing Authorization header" in error
    
    def test_verify_token_invalid_format(self):
        """Test token verification with invalid header format."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = verify_token("InvalidFormat", validator)
        
        assert valid is False
        assert payload is None
        assert "Invalid Authorization header format" in error
    
    def test_verify_token_empty_token(self):
        """Test token verification with empty token."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = verify_token("Bearer ", validator)
        
        assert valid is False
        assert payload is None
        assert "Empty token" in error
    
    def test_verify_token_bearer_success(self):
        """Test successful bearer token verification."""
        validator = TokenValidator(secret_key="my-secret-token")
        
        valid, payload, error = verify_token(
            "Bearer my-secret-token",
            validator,
            use_jwt=False
        )
        
        assert valid is True
        assert payload is None
        assert error is None
    
    def test_verify_token_bearer_failure(self):
        """Test failed bearer token verification."""
        validator = TokenValidator(secret_key="my-secret-token")
        
        valid, payload, error = verify_token(
            "Bearer wrong-token",
            validator,
            use_jwt=False
        )
        
        assert valid is False
        assert payload is None
        assert error is not None
    
    @pytest.mark.skipif(not JWT_AVAILABLE, reason="JWT library not available")
    def test_verify_token_jwt_success(self):
        """Test successful JWT token verification."""
        secret = "test-secret"
        validator = TokenValidator(secret_key=secret)
        
        token = TokenValidator.generate_jwt_token(
            payload={"user": "test"},
            secret_key=secret,
            expires_in_seconds=3600
        )
        
        valid, payload, error = verify_token(
            f"Bearer {token}",
            validator,
            use_jwt=True
        )
        
        assert valid is True
        assert payload is not None
        assert payload["user"] == "test"
        assert error is None
    
    def test_verify_token_with_rate_limit_allowed(self):
        """Test token verification with rate limiting (allowed)."""
        limiter = RateLimiter(capacity=10.0, refill_rate=1.0)
        validator = TokenValidator(secret_key="test-secret", rate_limiter=limiter)
        
        valid, payload, error = verify_token(
            "Bearer test-secret",
            validator,
            use_jwt=False,
            check_rate_limit=True
        )
        
        assert valid is True
        assert error is None
    
    def test_verify_token_with_rate_limit_exceeded(self):
        """Test token verification with rate limiting (exceeded)."""
        limiter = RateLimiter(capacity=2.0, refill_rate=1.0)
        validator = TokenValidator(secret_key="test-secret", rate_limiter=limiter)
        
        # Use up the rate limit
        for _ in range(2):
            verify_token("Bearer test-secret", validator, check_rate_limit=True)
        
        # Next request should be rate limited
        valid, payload, error = verify_token(
            "Bearer test-secret",
            validator,
            use_jwt=False,
            check_rate_limit=True
        )
        
        assert valid is False
        assert payload is None
        assert "Rate limit exceeded" in error
    
    def test_verify_token_skip_rate_limit(self):
        """Test token verification with rate limiting disabled."""
        limiter = RateLimiter(capacity=1.0, refill_rate=0.1)
        validator = TokenValidator(secret_key="test-secret", rate_limiter=limiter)
        
        # Use up the rate limit
        verify_token("Bearer test-secret", validator, check_rate_limit=True)
        
        # Should still succeed with rate limit check disabled
        valid, payload, error = verify_token(
            "Bearer test-secret",
            validator,
            use_jwt=False,
            check_rate_limit=False
        )
        
        assert valid is True
        assert error is None
    
    def test_verify_token_with_whitespace(self):
        """Test token verification with extra whitespace."""
        validator = TokenValidator(secret_key="test-secret")
        
        valid, payload, error = verify_token(
            "Bearer   test-secret   ",
            validator,
            use_jwt=False
        )
        
        assert valid is True
        assert error is None
