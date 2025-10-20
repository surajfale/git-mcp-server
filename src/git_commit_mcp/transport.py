"""Transport layer abstraction for Git Commit MCP Server.

This module provides a unified interface for different transport protocols,
allowing the server to operate in both local (stdio) and remote (HTTP/SSE) modes.
"""

import sys
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from git_commit_mcp.config import ServerConfig

logger = logging.getLogger(__name__)


class TransportHandler(ABC):
    """Base class for transport protocol handlers.
    
    This abstract class defines the interface that all transport implementations
    must follow. It provides a consistent way to handle different communication
    protocols (stdio, HTTP, WebSocket, etc.).
    
    Attributes:
        config: Server configuration
    """
    
    def __init__(self, config: ServerConfig):
        """Initialize transport handler.
        
        Args:
            config: Server configuration
        """
        self.config = config
    
    @abstractmethod
    def start(self) -> None:
        """Start the transport handler.
        
        This method should initialize and start the transport layer,
        making the server ready to accept connections and handle requests.
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the transport handler.
        
        This method should gracefully shut down the transport layer,
        closing all connections and cleaning up resources.
        """
        pass
    
    @abstractmethod
    def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through the transport.
        
        Args:
            message: Message data to send
        """
        pass
    
    @abstractmethod
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive a message from the transport.
        
        Returns:
            Received message data, or None if no message available
        """
        pass


class StdioTransport(TransportHandler):
    """Standard input/output transport for local mode.
    
    This transport implementation uses stdin/stdout for communication,
    which is the standard protocol for MCP servers running locally.
    It integrates with the FastMCP framework which handles the actual
    stdio protocol implementation.
    
    Attributes:
        config: Server configuration
        _running: Flag indicating if transport is running
    """
    
    def __init__(self, config: ServerConfig):
        """Initialize stdio transport.
        
        Args:
            config: Server configuration
        """
        super().__init__(config)
        self._running = False
        logger.info("Initialized stdio transport")
    
    def start(self) -> None:
        """Start the stdio transport.
        
        For stdio transport, this delegates to the FastMCP framework
        which handles the actual protocol implementation.
        """
        if self._running:
            logger.warning("Stdio transport already running")
            return
        
        self._running = True
        logger.info("Starting stdio transport")
        
        # Import and run FastMCP server
        try:
            from git_commit_mcp.server import mcp
            mcp.run()
        except Exception as e:
            logger.error(f"Failed to start stdio transport: {e}", exc_info=True)
            self._running = False
            raise
    
    def stop(self) -> None:
        """Stop the stdio transport.
        
        For stdio transport, this is typically handled by the FastMCP
        framework when the process terminates.
        """
        if not self._running:
            logger.warning("Stdio transport not running")
            return
        
        self._running = False
        logger.info("Stopping stdio transport")
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through stdio.
        
        Note: For stdio transport with FastMCP, message sending is handled
        by the framework's response mechanism.
        
        Args:
            message: Message data to send
        """
        # FastMCP handles message sending through its response mechanism
        logger.debug(f"Message sent via stdio: {message}")
    
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive a message from stdio.
        
        Note: For stdio transport with FastMCP, message receiving is handled
        by the framework's request handling mechanism.
        
        Returns:
            None (FastMCP handles message receiving internally)
        """
        # FastMCP handles message receiving through its request mechanism
        return None


class HttpTransport(TransportHandler):
    """HTTP/SSE transport for remote mode.
    
    This transport implementation uses HTTP for requests and Server-Sent
    Events (SSE) for streaming responses. It provides authentication,
    CORS support, and other features needed for remote deployments.
    
    Attributes:
        config: Server configuration
        _running: Flag indicating if transport is running
        _server: Optional reference to the HTTP server instance
    """
    
    def __init__(self, config: ServerConfig):
        """Initialize HTTP transport.
        
        Args:
            config: Server configuration
        """
        super().__init__(config)
        self._running = False
        self._server = None
        logger.info("Initialized HTTP transport")
    
    def start(self) -> None:
        """Start the HTTP transport.
        
        This starts the FastAPI/uvicorn server with the configured settings.
        """
        if self._running:
            logger.warning("HTTP transport already running")
            return
        
        self._running = True
        logger.info("Starting HTTP transport")
        
        # Import and run HTTP server
        try:
            from git_commit_mcp.http_server import run_http_server
            run_http_server(self.config)
        except ImportError as e:
            logger.error(
                "Failed to import HTTP server dependencies. "
                "Install with: pip install 'git-commit-mcp-server[remote]'"
            )
            self._running = False
            raise
        except Exception as e:
            logger.error(f"Failed to start HTTP transport: {e}", exc_info=True)
            self._running = False
            raise
    
    def stop(self) -> None:
        """Stop the HTTP transport.
        
        This gracefully shuts down the HTTP server.
        """
        if not self._running:
            logger.warning("HTTP transport not running")
            return
        
        self._running = False
        logger.info("Stopping HTTP transport")
        
        # Server shutdown is handled by uvicorn's signal handlers
        if self._server:
            self._server = None
    
    def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through HTTP.
        
        Note: For HTTP transport, message sending is handled by FastAPI's
        response mechanism.
        
        Args:
            message: Message data to send
        """
        # FastAPI handles message sending through its response mechanism
        logger.debug(f"Message sent via HTTP: {message}")
    
    def receive_message(self) -> Optional[Dict[str, Any]]:
        """Receive a message from HTTP.
        
        Note: For HTTP transport, message receiving is handled by FastAPI's
        request handling mechanism.
        
        Returns:
            None (FastAPI handles message receiving internally)
        """
        # FastAPI handles message receiving through its request mechanism
        return None


def create_transport(config: ServerConfig) -> TransportHandler:
    """Factory function to create the appropriate transport handler.
    
    This function selects and instantiates the correct transport handler
    based on the server configuration.
    
    Args:
        config: Server configuration
        
    Returns:
        Appropriate TransportHandler instance for the configured mode
        
    Raises:
        ValueError: If transport mode is not supported
    """
    if config.transport_mode == "stdio":
        logger.info("Creating stdio transport")
        return StdioTransport(config)
    elif config.transport_mode == "http":
        logger.info("Creating HTTP transport")
        return HttpTransport(config)
    else:
        raise ValueError(
            f"Unsupported transport mode: {config.transport_mode}. "
            "Supported modes: 'stdio', 'http'"
        )


def run_transport(config: ServerConfig) -> None:
    """Run the transport layer with the given configuration.
    
    This is a convenience function that creates and starts the appropriate
    transport handler based on the configuration.
    
    Args:
        config: Server configuration
        
    Raises:
        ValueError: If transport mode is not supported
        Exception: If transport fails to start
    """
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info(f"Starting Git Commit MCP Server in {config.transport_mode} mode")
    
    # Create and start transport
    transport = create_transport(config)
    
    try:
        transport.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        transport.stop()
    except Exception as e:
        logger.error(f"Transport failed: {e}", exc_info=True)
        transport.stop()
        raise
