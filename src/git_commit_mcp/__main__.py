"""Entry point for running the Git Commit MCP Server.

This module provides the entry point for the MCP server with stdio transport.
It handles:
- Configuration loading from environment variables
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
    2. Sets up logging
    3. Runs the stdio MCP server
    4. Handles errors and provides clear error messages
    
    Exit codes:
    - 0: Successful execution
    - 1: Configuration error
    - 2: Server startup error
    """
    try:
        # Load configuration from environment
        config = ServerConfig.from_env()
        
        # Setup logging (plain text for stdio to avoid interfering with MCP protocol)
        # IMPORTANT: Use stderr for logs so stdout is reserved for MCP protocol JSON
        setup_logging(
            log_level=config.log_level,
            use_json=False,
            log_file=None,
            stream="stderr"
        )
        
        logger.info(
            "Starting Git Commit MCP Server",
            extra={"version": "1.0.0", "transport": "stdio"}
        )
        
        # Run stdio server
        run_stdio_server()
            
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
