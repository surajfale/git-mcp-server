"""HTTP/SSE server implementation for remote Git Commit MCP Server.

This module provides the HTTP transport layer with Server-Sent Events (SSE)
support for remote deployments. It includes authentication, CORS handling,
health checks, and error handling middleware.
"""

import asyncio
import os
import time
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
from git_commit_mcp.repository_manager import RepositoryManager
from git_commit_mcp.metrics import (
    get_metrics_collector,
    record_http_request,
    record_git_commit,
    record_git_push,
    record_git_error,
    record_auth_attempt,
    record_rate_limit_exceeded,
    MetricsTimer
)
from git_commit_mcp.logging_config import (
    get_logger,
    set_request_id,
    clear_request_id,
    log_http_request,
    log_auth_attempt as log_auth_event,
    log_rate_limit_exceeded as log_rate_limit_event,
    log_git_operation,
    log_security_event,
    log_workspace_operation
)

# Get logger for this module
logger = get_logger(__name__)


# Global instances
_config: Optional[ServerConfig] = None
_token_validator: Optional[TokenValidator] = None
_rate_limiter: Optional[RateLimiter] = None
_repository_manager: Optional[RepositoryManager] = None


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


def get_repository_manager() -> RepositoryManager:
    """Get the global repository manager.
    
    Returns:
        RepositoryManager instance
        
    Raises:
        RuntimeError: If repository manager is not initialized
    """
    if _repository_manager is None:
        raise RuntimeError("Repository manager not initialized")
    return _repository_manager


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for the application.
    
    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info(
        "Starting Git Commit MCP HTTP Server",
        extra={
            "version": "1.0.0",
            "transport": "http",
            "auth_enabled": _config.auth_enabled,
            "cors_enabled": _config.cors_enabled,
            "metrics_enabled": _config.enable_metrics,
            "host": _config.http_host,
            "port": _config.http_port,
            "tls_enabled": _config.tls_enabled
        }
    )
    
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
    global _config, _token_validator, _rate_limiter, _repository_manager
    _config = config
    
    # Initialize authentication components
    if config.auth_enabled and config.auth_token:
        _rate_limiter = RateLimiter(capacity=100.0, refill_rate=10.0)
        _token_validator = TokenValidator(
            secret_key=config.auth_token,
            rate_limiter=_rate_limiter
        )
    
    # Initialize repository manager for remote mode
    if config.is_remote_mode():
        _repository_manager = RepositoryManager(workspace_dir=config.workspace_dir)
    
    # Create FastAPI app
    app = FastAPI(
        title="Git Commit MCP Server",
        description="MCP server for automated Git commit workflows",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id_middleware(request: Request, call_next):
        """Middleware to add request ID to each request."""
        # Generate and set request ID
        request_id = set_request_id()
        
        # Add to request state for access in endpoints
        request.state.request_id = request_id
        
        # Process request
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            # Log HTTP request with structured logging
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            
            log_http_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            return response
        finally:
            # Clear request ID from context
            clear_request_id()
    
    # Add CORS middleware
    if config.cors_enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
            expose_headers=["X-Request-ID"],
        )
        logger.info("CORS enabled", extra={"origins": config.cors_origins})
    
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
        start_time = time.time()
        
        try:
            response = {
                "status": "healthy",
                "version": "1.0.0",
                "transport": "http",
                "auth_enabled": config.auth_enabled,
                "metrics_enabled": config.enable_metrics
            }
            
            # Record metrics
            if config.enable_metrics:
                duration = time.time() - start_time
                record_http_request("GET", "/health", 200, duration)
            
            return response
        except Exception as e:
            # Record error metrics
            if config.enable_metrics:
                duration = time.time() - start_time
                record_http_request("GET", "/health", 500, duration)
            raise
    
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
        start_time = time.time()
        response_status = 200
        
        try:
            # Verify authentication if enabled
            if config.auth_enabled:
                validator = get_token_validator()
                valid, payload, error = verify_token(
                    authorization,
                    validator,
                    use_jwt=False,
                    check_rate_limit=True
                )
                
                # Extract client ID for logging
                client_id = "unknown"
                if authorization:
                    token = authorization.replace("Bearer ", "", 1).strip()
                    client_id = token[:8] if token else "unknown"
                
                # Log authentication attempt
                log_auth_event(
                    client_id=client_id,
                    success=valid,
                    method="bearer",
                    reason=error if not valid else None
                )
                
                # Record authentication attempt metrics
                if config.enable_metrics:
                    record_auth_attempt(valid)
                    if not valid and "rate limit" in (error or "").lower():
                        record_rate_limit_exceeded()
                        log_rate_limit_event(client_id=client_id, wait_time=0.0)
                
                if not valid:
                    response_status = 401
                    # Log security event for failed authentication
                    log_security_event(
                        event_type="authentication_failed",
                        severity="medium",
                        description=f"Authentication failed: {error}",
                        details={"client_id": client_id, "endpoint": "/mcp/tools/git_commit_and_push"}
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error or "Authentication failed"
                    )
            
            # Execute the git commit and push operation with timing
            logger.info(
                "Executing git commit and push",
                extra={
                    "repository_path": repository_path,
                    "confirm_push": confirm_push
                }
            )
            
            with MetricsTimer() as commit_timer:
                result = execute_git_commit_and_push(repository_path, confirm_push)
            
            # Log Git operation with structured logging
            log_git_operation(
                operation="commit_and_push",
                repository=repository_path,
                success=result.get("success", False),
                duration=commit_timer.duration,
                details={
                    "files_changed": result.get("files_changed", 0),
                    "pushed": result.get("pushed", False),
                    "commit_hash": result.get("commit_hash"),
                    "changelog_updated": result.get("changelog_updated", False)
                },
                error=result.get("error")
            )
            
            # Record Git operation metrics
            if config.enable_metrics:
                # Record commit metrics
                record_git_commit(result.get("success", False), commit_timer.duration)
                
                # Record push metrics if push was attempted
                if result.get("pushed", False):
                    record_git_push(True, 0.0)  # Duration included in commit timer
                
                # Record errors if operation failed
                if not result.get("success", False) and result.get("error"):
                    error_msg = result.get("error", "")
                    error_type = "unknown"
                    if "authentication" in error_msg.lower():
                        error_type = "authentication"
                    elif "network" in error_msg.lower():
                        error_type = "network"
                    elif "not a git repository" in error_msg.lower():
                        error_type = "invalid_repository"
                    
                    record_git_error("commit_and_push", error_type)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            response_status = 500
            logger.error(f"Error executing git_commit_and_push: {e}", exc_info=True)
            
            # Record error metrics
            if config.enable_metrics:
                record_git_error("commit_and_push", type(e).__name__)
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
        finally:
            # Record HTTP request metrics
            if config.enable_metrics:
                duration = time.time() - start_time
                record_http_request("POST", "/mcp/tools/git_commit_and_push", response_status, duration)
    
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
            
            Exposes metrics in Prometheus text format for monitoring and observability.
            Tracks:
            - HTTP request counts and latencies by method, endpoint, and status
            - Git operation metrics (commits, pushes, failures) with durations
            - Authentication attempts and rate limiting events
            - Server health and information
            
            Returns:
                Metrics in Prometheus text format
            """
            from fastapi.responses import PlainTextResponse
            
            collector = get_metrics_collector()
            metrics_text = collector.generate_prometheus_text()
            
            return PlainTextResponse(content=metrics_text, media_type="text/plain")
    
    # Optional: Add cleanup endpoints if enabled
    if config.cleanup_enabled and config.is_remote_mode():
        @app.get("/workspace/info")
        async def workspace_info_endpoint(authorization: Optional[str] = Header(None)):
            """Get workspace information including size and repository count.
            
            This endpoint provides information about the workspace directory,
            including total size, number of repositories, and available space.
            
            Args:
                authorization: Authorization header with Bearer token
                
            Returns:
                Dictionary containing workspace information
                
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
                    check_rate_limit=False
                )
                
                if not valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error or "Authentication failed"
                    )
            
            try:
                repo_manager = get_repository_manager()
                workspace_path = repo_manager.workspace_dir
                
                # Calculate workspace size
                total_size = 0
                repo_count = 0
                
                if workspace_path.exists():
                    for item in workspace_path.iterdir():
                        if item.is_dir():
                            repo_count += 1
                            # Calculate directory size
                            for dirpath, dirnames, filenames in os.walk(item):
                                for filename in filenames:
                                    filepath = os.path.join(dirpath, filename)
                                    try:
                                        total_size += os.path.getsize(filepath)
                                    except (OSError, FileNotFoundError):
                                        pass
                
                # Convert to MB
                total_size_mb = total_size / (1024 * 1024)
                
                # Get disk usage
                import shutil
                disk_usage = shutil.disk_usage(workspace_path)
                available_mb = disk_usage.free / (1024 * 1024)
                total_disk_mb = disk_usage.total / (1024 * 1024)
                
                return {
                    "workspace_path": str(workspace_path),
                    "repository_count": repo_count,
                    "total_size_mb": round(total_size_mb, 2),
                    "max_size_mb": config.max_workspace_size_mb,
                    "usage_percent": round((total_size_mb / config.max_workspace_size_mb) * 100, 2),
                    "disk_available_mb": round(available_mb, 2),
                    "disk_total_mb": round(total_disk_mb, 2),
                    "cleanup_recommended": total_size_mb > (config.max_workspace_size_mb * 0.8)
                }
            except Exception as e:
                logger.error(f"Error getting workspace info: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
        
        @app.post("/workspace/cleanup")
        async def workspace_cleanup_endpoint(authorization: Optional[str] = Header(None)):
            """Clean up all cloned repositories from the workspace.
            
            This endpoint removes all cloned repositories to free up disk space.
            Use with caution as this will require re-cloning repositories on
            next use.
            
            Args:
                authorization: Authorization header with Bearer token
                
            Returns:
                Dictionary containing cleanup results
                
            Raises:
                HTTPException: If authentication fails or cleanup encounters an error
            """
            # Verify authentication if enabled
            if config.auth_enabled:
                validator = get_token_validator()
                valid, payload, error = verify_token(
                    authorization,
                    validator,
                    use_jwt=False,
                    check_rate_limit=False
                )
                
                if not valid:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error or "Authentication failed"
                    )
            
            try:
                repo_manager = get_repository_manager()
                
                # Get workspace info before cleanup
                workspace_path = repo_manager.workspace_dir
                total_size_before = 0
                
                if workspace_path.exists():
                    for item in workspace_path.iterdir():
                        if item.is_dir():
                            for dirpath, dirnames, filenames in os.walk(item):
                                for filename in filenames:
                                    filepath = os.path.join(dirpath, filename)
                                    try:
                                        total_size_before += os.path.getsize(filepath)
                                    except (OSError, FileNotFoundError):
                                        pass
                
                # Perform cleanup
                repos_cleaned = repo_manager.cleanup_all_workspaces()
                
                # Convert to MB
                size_freed_mb = total_size_before / (1024 * 1024)
                
                # Log workspace operation
                log_workspace_operation(
                    operation="cleanup_all",
                    workspace_path=str(workspace_path),
                    success=True,
                    details={
                        "repositories_cleaned": repos_cleaned,
                        "size_freed_mb": round(size_freed_mb, 2)
                    }
                )
                
                return {
                    "success": True,
                    "repositories_cleaned": repos_cleaned,
                    "size_freed_mb": round(size_freed_mb, 2),
                    "message": f"Successfully cleaned up {repos_cleaned} repositories"
                }
            except Exception as e:
                logger.error(f"Error during workspace cleanup: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
    
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
    
    # Configure structured logging
    from git_commit_mcp.logging_config import setup_logging
    setup_logging(
        log_level=config.log_level,
        use_json=True,  # Use JSON format for cloud deployments
        log_file=None  # Log to stdout for cloud platforms
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
