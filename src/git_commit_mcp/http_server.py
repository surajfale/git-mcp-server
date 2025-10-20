"""HTTP/SSE server implementation for remote Git Commit MCP Server.

This module provides the HTTP transport layer with Server-Sent Events (SSE)
support for remote deployments. It includes authentication, CORS handling,
health checks, and error handling middleware.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, Header, HTTPException, Request, status
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from sse_starlette.sse import EventSourceResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from git_commit_mcp.config import ServerConfig
from git_commit_mcp.auth import TokenValidator, RateLimiter, verify_token
from git_commit_mcp.server import execute_git_commit_and_push

# Configure logging
logger = logging.getLogger(__name__)


# Global instances
_config: Optional[ServerConfig] = None
_token_validator: Optional[TokenValidator] = None
_rate_limiter: Optional[RateLimiter] = None


def get_config() -> ServerConfig:
    """Get the global server configuration.
    
    Returns:
        ServerConfig instance
        
    Raises:
        RuntimeError: If configuration is not initialized
    """
    if _config is None:
        raise RuntimeError("Server configuration not initialized")
    return _config


def get_token_validator() -> TokenValidator:
    """Get the global token validator.
    
    Returns:
        TokenValidator instance
        
    Raises:
        RuntimeError: If token validator is not initialized
    """
    if _token_validator is None:
        raise RuntimeError("Token validator not initialized")
    return _token_validator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info("Starting Git Commit MCP HTTP Server")
    logger.info(f"Authentication: {'enabled' if _config.auth_enabled else 'disabled'}")
    logger.info(f"CORS: {'enabled' if _config.cors_enabled else 'disabled'}")
    logger.info(f"Metrics: {'enabled' if _config.enable_metrics else 'disabled'}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Git Commit MCP HTTP Server")


def create_app(config: ServerConfig) -> FastAPI:
    """Create and configure FastAPI application.
    
    Args:
        config: Server configuration
        
    Returns:
        Configured FastAPI application
        
    Raises:
        ImportError: If FastAPI dependencies are not installed
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI dependencies not installed. "
            "Install with: pip install 'git-commit-mcp-server[remote]'"
        )
    
    # Store config globally
    global _config, _token_validator, _rate_limiter
    _config = config
    
    # Initialize authentication components
    if config.auth_enabled and config.auth_token:
        _rate_limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        _token_validator = TokenValidator(
            secret_key=config.auth_token,
            rate_limiter=_rate_limiter
        )
    
    # Create FastAPI app
    app = FastAPI(
        title="Git Commit MCP Server",
        description="MCP server for automated Git commit workflows",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
        logger.info(f"CORS enabled for origins: {config.cors_origins}")
    
    # Add error handling middleware
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for consistent error responses."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": "Internal server error",
                "message": str(exc) if config.log_level == "DEBUG" else "An unexpected error occurred"
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP exception handler for consistent error responses."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "message": exc.detail
            }
        )
    
    return app


def create_http_server(config: ServerConfig) -> FastAPI:
    """Create HTTP server with all endpoints configured.
    
    Args:
        config: Server configuration
        
    Returns:
        Configured FastAPI application with all endpoints
    """
    app = create_app(config)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring.
        
        Returns:
            Health status information including version and configuration
        """
        return {
            "status": "healthy",
            "version": "1.0.0",
            "transport": "http",
            "auth_enabled": config.auth_enabled,
            "metrics_enabled": config.enable_metrics
        }
    
    @app.post("/mcp/tools/git_commit_and_push")
    async def git_commit_and_push_endpoint(
        repository_path: str = ".",
        confirm_push: bool = False,
        authorization: Optional[str] = Header(None)
    ):
        """Execute git commit and push operation.
        
        This endpoint provides the main MCP tool functionality over HTTP.
        It requires authentication if auth is enabled in the configuration.
        
        Args:
            repository_path: Path to the Git repository (default: current directory)
            confirm_push: Whether to push to remote after committing (default: False)
            authorization: Authorization header with Bearer token
            
        Returns:
            Dictionary containing commit result information
            
        Raises:
            HTTPException: If authentication fails or operation encounters an error
        """
        # Verify authentication if enabled
        if config.auth_enabled:
            validator = get_token_validator()
            valid, payload, error = verify_token(
                authorization,
                validator,
                use_jwt=False,
                check_rate_limit=True
            )
            
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error or "Authentication failed"
                )
        
        # Execute the git commit and push operation
        try:
            result = execute_git_commit_and_push(repository_path, confirm_push)
            return result
        except Exception as e:
            logger.error(f"Error executing git_commit_and_push: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    
    @app.get("/mcp/sse")
    async def sse_endpoint(authorization: Optional[str] = Header(None)):
        """Server-Sent Events endpoint for streaming updates.
        
        This endpoint provides real-time streaming of server events to clients.
        It requires authentication if auth is enabled in the configuration.
        
        Args:
            authorization: Authorization header with Bearer token
            
        Returns:
            EventSourceResponse for streaming events
            
        Raises:
            HTTPException: If authentication fails
        """
        # Verify authentication if enabled
        if config.auth_enabled:
            validator = get_token_validator()
            valid, payload, error = verify_token(
                authorization,
                validator,
                use_jwt=False,
                check_rate_limit=False  # Don't rate limit SSE connections
            )
            
            if not valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=error or "Authentication failed"
                )
        
        async def event_generator():
            """Generate server-sent events."""
            # Send initial connection event
            yield {
                "event": "connected",
                "data": "Git Commit MCP Server Ready"
            }
            
            # Keep connection alive with periodic heartbeats
            try:
                while True:
                    await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                    yield {
                        "event": "heartbeat",
                        "data": "alive"
                    }
            except asyncio.CancelledError:
                # Client disconnected
                logger.info("SSE client disconnected")
                return
        
        return EventSourceResponse(event_generator())
    
    # Optional: Add metrics endpoint if enabled
    if config.enable_metrics:
        @app.get("/metrics")
        async def metrics_endpoint():
            """Prometheus-compatible metrics endpoint.
            
            Returns basic metrics about the server. This is a placeholder
            for future implementation of detailed metrics.
            
            Returns:
                Metrics in Prometheus text format
            """
            # Placeholder for metrics implementation
            # In a full implementation, this would track:
            # - Request counts and latencies
            # - Git operation metrics (commits, pushes, failures)
            # - Authentication metrics
            # - Rate limiting metrics
            
            metrics = [
                "# HELP git_commit_mcp_info Server information",
                "# TYPE git_commit_mcp_info gauge",
                'git_commit_mcp_info{version="1.0.0"} 1',
                "",
                "# HELP git_commit_mcp_health Server health status",
                "# TYPE git_commit_mcp_health gauge",
                "git_commit_mcp_health 1",
            ]
            
            return "\n".join(metrics)
    
    return app


def run_http_server(config: ServerConfig) -> None:
    """Run the HTTP server with the given configuration.
    
    This function starts the uvicorn server with the configured settings
    including TLS support if enabled.
    
    Args:
        config: Server configuration
        
    Raises:
        ImportError: If FastAPI dependencies are not installed
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI dependencies not installed. "
            "Install with: pip install 'git-commit-mcp-server[remote]'"
        )
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create app
    app = create_http_server(config)
    
    # Configure uvicorn
    uvicorn_config = {
        "app": app,
        "host": config.http_host,
        "port": config.http_port,
        "log_level": config.log_level.lower(),
    }
    
    # Add TLS configuration if enabled
    if config.tls_enabled:
        uvicorn_config["ssl_certfile"] = config.tls_cert_path
        uvicorn_config["ssl_keyfile"] = config.tls_key_path
        logger.info(f"Starting HTTPS server on {config.http_host}:{config.http_port}")
    else:
        logger.info(f"Starting HTTP server on {config.http_host}:{config.http_port}")
    
    # Run server
    uvicorn.run(**uvicorn_config)
