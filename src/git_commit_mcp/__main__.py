"""Entry point for running the Git Commit MCP Server.

This module provides the unified entry point that supports both stdio and HTTP
transport modes based on configuration. It handles:
- Configuration loading from environment variables
- Mode selection (stdio vs http)
- Logging setup
- Error handling and graceful shutdown
"""

import sys

from git_commit_mcp.config import ServerConfig
from git_commit_mcp.server import run_stdio_server
from git_commit_mcp.logging_config import setup_logging, get_logger

# Get logger for this module
logger = get_logger(__name__)


def main():
    """Main entry point for the MCP server.
    
    This function:
    1. Loads configuration from environment variables
    2. Sets up logging based on configuration
    3. Selects and runs the appropriate server mode (stdio or http)
    4. Handles errors and provides clear error messages
    
    The server mode is determined by the TRANSPORT_MODE environment variable:
    - "stdio" (default): Run in local mode with stdio transport
    - "http": Run in remote mode with HTTP/SSE transport
    
    Exit codes:
    - 0: Successful execution
    - 1: Configuration error or invalid transport mode
    - 2: Server startup error
    """
    try:
        # Load configuration from environment
        config = ServerConfig.from_env()
        
        # Setup structured logging
        # For stdio mode, use plain text to avoid interfering with MCP protocol
        # For HTTP mode, use JSON format for cloud deployments
        use_json = config.transport_mode == "http"
        setup_logging(
            log_level=config.log_level,
            use_json=use_json,
            log_file=None  # Always log to stdout/stderr
        )
        
        logger.info(
            "Starting Git Commit MCP Server",
            extra={
                "transport_mode": config.transport_mode,
                "version": "1.0.0"
            }
        )
        
        # Select and run appropriate server based on transport mode
        if config.transport_mode == "stdio":
            logger.info(
                "Running in stdio mode",
                extra={"mode": "local", "transport": "stdio"}
            )
            run_stdio_server()
        elif config.transport_mode == "http":
            logger.info(
                "Running in HTTP mode",
                extra={
                    "mode": "remote",
                    "transport": "http",
                    "host": config.http_host,
                    "port": config.http_port,
                    "tls_enabled": config.tls_enabled
                }
            )
            # Import here to avoid loading FastAPI dependencies in stdio mode
            try:
                from git_commit_mcp.http_server import run_http_server
                run_http_server(config)
            except ImportError as e:
                logger.error(
                    "Failed to import HTTP server dependencies",
                    extra={"error": str(e)}
                )
                sys.exit(2)
        else:
            logger.error(
                "Unknown transport mode",
                extra={"transport_mode": config.transport_mode, "valid_modes": ["stdio", "http"]}
            )
            sys.exit(1)
            
    except ValueError as e:
        # Configuration validation error
        logger.error("Configuration error", extra={"error": str(e)})
        sys.exit(1)
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("Received interrupt signal, shutting down")
        sys.exit(0)
    except Exception as e:
        # Unexpected error during startup
        logger.exception("Failed to start server", extra={"error": str(e)})
        sys.exit(2)


if __name__ == "__main__":
    main()
