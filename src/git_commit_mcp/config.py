"""Configuration management for Git Commit MCP Server."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Optional

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


@dataclass
class ServerConfig:
    """Configuration settings for the MCP server.
    
    Supports both local (stdio) and remote (HTTP/SSE) deployment modes with
    comprehensive configuration options for authentication, TLS, repository
    access, and monitoring.
    
    Attributes:
        # Core settings
        default_repo_path: Default path to Git repository
        max_bullet_points: Maximum number of bullet points in commit messages
        max_summary_lines: Maximum number of lines in commit summary
        changelog_file: Name of the changelog file to maintain
        
        # Transport settings
        transport_mode: Communication protocol (stdio or http)
        http_host: Host address for HTTP server
        http_port: Port number for HTTP server
        
        # Authentication settings
        auth_enabled: Whether authentication is required
        auth_token: Bearer token for API authentication
        
        # CORS settings
        cors_enabled: Whether CORS is enabled
        cors_origins: List of allowed CORS origins
        
        # TLS/HTTPS settings
        tls_enabled: Whether TLS/HTTPS is enabled
        tls_cert_path: Path to TLS certificate file
        tls_key_path: Path to TLS private key file
        
        # Repository settings (for remote mode)
        workspace_dir: Directory for cloning remote repositories
        ssh_key_path: Path to SSH private key for Git operations
        git_username: Username for HTTPS Git authentication
        git_token: Token/password for HTTPS Git authentication
        
        # Monitoring settings
        enable_metrics: Whether to expose metrics endpoint
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Core settings
    default_repo_path: str = "."
    max_bullet_points: int = 5
    max_summary_lines: int = 2
    changelog_file: str = "CHANGELOG.md"
    
    # Transport settings
    transport_mode: Literal["stdio", "http"] = "stdio"
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    
    # Authentication settings
    auth_enabled: bool = True
    auth_token: Optional[str] = None
    
    # CORS settings
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # TLS/HTTPS settings
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    
    # Repository settings (for remote mode)
    workspace_dir: str = "/tmp/git-workspaces"
    ssh_key_path: Optional[str] = None
    git_username: Optional[str] = None
    git_token: Optional[str] = None
    
    # Monitoring settings
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "ServerConfig":
        """Load configuration from environment variables.
        
        Optionally loads variables from a .env file first if python-dotenv
        is installed and an env_file path is provided.
        
        Args:
            env_file: Optional path to .env file to load
            
        Returns:
            ServerConfig instance populated from environment variables
            
        Raises:
            ValueError: If configuration validation fails
        """
        # Load .env file if available and requested
        if env_file and DOTENV_AVAILABLE:
            load_dotenv(env_file)
        elif env_file and not DOTENV_AVAILABLE:
            # Warn but don't fail if dotenv is not available
            print(f"Warning: python-dotenv not installed, cannot load {env_file}")
        
        # Parse CORS origins from comma-separated string
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
        
        # Parse boolean values
        def parse_bool(value: str) -> bool:
            return value.lower() in ("true", "1", "yes", "on")
        
        # Create config from environment
        config = cls(
            # Core settings
            default_repo_path=os.getenv("DEFAULT_REPO_PATH", "."),
            max_bullet_points=int(os.getenv("MAX_BULLET_POINTS", "5")),
            max_summary_lines=int(os.getenv("MAX_SUMMARY_LINES", "2")),
            changelog_file=os.getenv("CHANGELOG_FILE", "CHANGELOG.md"),
            
            # Transport settings
            transport_mode=os.getenv("TRANSPORT_MODE", "stdio"),  # type: ignore
            http_host=os.getenv("HTTP_HOST", "0.0.0.0"),
            http_port=int(os.getenv("HTTP_PORT", "8000")),
            
            # Authentication settings
            auth_enabled=parse_bool(os.getenv("AUTH_ENABLED", "true")),
            auth_token=os.getenv("MCP_AUTH_TOKEN"),
            
            # CORS settings
            cors_enabled=parse_bool(os.getenv("CORS_ENABLED", "true")),
            cors_origins=cors_origins,
            
            # TLS/HTTPS settings
            tls_enabled=parse_bool(os.getenv("TLS_ENABLED", "false")),
            tls_cert_path=os.getenv("TLS_CERT_PATH"),
            tls_key_path=os.getenv("TLS_KEY_PATH"),
            
            # Repository settings
            workspace_dir=os.getenv("WORKSPACE_DIR", "/tmp/git-workspaces"),
            ssh_key_path=os.getenv("GIT_SSH_KEY_PATH"),
            git_username=os.getenv("GIT_USERNAME"),
            git_token=os.getenv("GIT_TOKEN"),
            
            # Monitoring settings
            enable_metrics=parse_bool(os.getenv("ENABLE_METRICS", "true")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate transport mode
        if self.transport_mode not in ("stdio", "http"):
            raise ValueError(
                f"Invalid transport_mode: {self.transport_mode}. "
                "Must be 'stdio' or 'http'"
            )
        
        # Validate HTTP port range
        if not (1 <= self.http_port <= 65535):
            raise ValueError(
                f"Invalid http_port: {self.http_port}. "
                "Must be between 1 and 65535"
            )
        
        # Validate max_bullet_points
        if self.max_bullet_points < 1:
            raise ValueError(
                f"Invalid max_bullet_points: {self.max_bullet_points}. "
                "Must be at least 1"
            )
        
        # Validate max_summary_lines
        if self.max_summary_lines < 1:
            raise ValueError(
                f"Invalid max_summary_lines: {self.max_summary_lines}. "
                "Must be at least 1"
            )
        
        # Validate log level
        valid_log_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        if self.log_level not in valid_log_levels:
            raise ValueError(
                f"Invalid log_level: {self.log_level}. "
                f"Must be one of {valid_log_levels}"
            )
        
        # Validate TLS configuration
        if self.tls_enabled:
            if not self.tls_cert_path:
                raise ValueError(
                    "TLS is enabled but tls_cert_path is not set"
                )
            if not self.tls_key_path:
                raise ValueError(
                    "TLS is enabled but tls_key_path is not set"
                )
            
            # Check if certificate files exist
            cert_path = Path(self.tls_cert_path)
            if not cert_path.exists():
                raise ValueError(
                    f"TLS certificate file not found: {self.tls_cert_path}"
                )
            if not cert_path.is_file():
                raise ValueError(
                    f"TLS certificate path is not a file: {self.tls_cert_path}"
                )
            
            key_path = Path(self.tls_key_path)
            if not key_path.exists():
                raise ValueError(
                    f"TLS key file not found: {self.tls_key_path}"
                )
            if not key_path.is_file():
                raise ValueError(
                    f"TLS key path is not a file: {self.tls_key_path}"
                )
        
        # Validate authentication for remote mode
        if self.transport_mode == "http" and self.auth_enabled:
            if not self.auth_token:
                raise ValueError(
                    "Authentication is enabled for HTTP mode but "
                    "MCP_AUTH_TOKEN is not set"
                )
        
        # Validate workspace directory for remote mode
        if self.transport_mode == "http":
            workspace_path = Path(self.workspace_dir)
            # Create workspace directory if it doesn't exist
            try:
                workspace_path.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Cannot create workspace directory {self.workspace_dir}: {e}"
                )
        
        # Validate SSH key path if provided
        if self.ssh_key_path:
            ssh_key = Path(self.ssh_key_path)
            if not ssh_key.exists():
                raise ValueError(
                    f"SSH key file not found: {self.ssh_key_path}"
                )
            if not ssh_key.is_file():
                raise ValueError(
                    f"SSH key path is not a file: {self.ssh_key_path}"
                )
    
    def is_remote_mode(self) -> bool:
        """Check if server is configured for remote (HTTP) mode.
        
        Returns:
            True if transport_mode is 'http', False otherwise
        """
        return self.transport_mode == "http"
    
    def is_local_mode(self) -> bool:
        """Check if server is configured for local (stdio) mode.
        
        Returns:
            True if transport_mode is 'stdio', False otherwise
        """
        return self.transport_mode == "stdio"
