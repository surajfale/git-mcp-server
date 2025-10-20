"""Entry point for running the Git Commit MCP Server.

This module provides the unified entry point that supports both stdio and HTTP
transport modes based on configuration. It handles:
- Configuration loading from environment variables
- Mode selection (stdio vs http)
- Logging setup
- Error handling and graceful shutdown
"""

import sys
import logging

from git_commit_mcp.config import ServerConfig
from git_commit_mcp.server import run_stdio_server

# Configure logging
logger = logging.getLogger(__name__)


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
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, config.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            stream=sys.stderr  # Log to stderr to avoid interfering with stdio transport
        )
        
        logger.info(f"Starting Git Commit MCP Server in {config.transport_mode} mode")
        
        # Select and run appropriate server based on transport mode
        if config.transport_mode == "stdio":
            logger.info("Running in stdio mode for local MCP client communication")
            run_stdio_server()
        elif config.transport_mode == "http":
            logger.info("Running in HTTP mode for remote client communication")
            # Import here to avoid loading FastAPI dependencies in stdio mode
            try:
                from git_commit_mcp.http_server import run_http_server
                run_http_server(config)
            except ImportError as e:
                logger.error(
                    "Failed to import HTTP server dependencies. "
                    "Install with: pip install 'git-commit-mcp-server[remote]'"
                )
                logger.error(f"Error: {e}")
                sys.exit(2)
        else:
            logger.error(f"Unknown transport mode: {config.transport_mode}")
            logger.error("Valid modes are: 'stdio' or 'http'")
            sys.exit(1)
            
    except ValueError as e:
        # Configuration validation error
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("Received interrupt signal, shutting down...")
        sys.exit(0)
    except Exception as e:
        # Unexpected error during startup
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
