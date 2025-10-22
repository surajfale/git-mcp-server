"""Configuration management for Git Commit MCP Server."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


@dataclass
class ServerConfig:
    """Configuration settings for the MCP server.
    
    Attributes:
        default_repo_path: Default path to Git repository
        max_bullet_points: Maximum number of bullet points in commit messages
        max_summary_lines: Maximum number of lines in commit summary
        changelog_file: Name of the changelog file to maintain
        workspace_dir: Directory for cloning remote repositories
        ssh_key_path: Path to SSH private key for Git operations
        git_username: Username for HTTPS Git authentication
        git_token: Token/password for HTTPS Git authentication
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Core settings
    default_repo_path: str = "."
    max_bullet_points: int = 5
    max_summary_lines: int = 2
    changelog_file: str = "CHANGELOG.md"
    
    # Repository settings
    workspace_dir: str = "/tmp/git-workspaces"
    ssh_key_path: Optional[str] = None
    git_username: Optional[str] = None
    git_token: Optional[str] = None
    
    # Logging settings
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> "ServerConfig":
        """Load configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file to load
            
        Returns:
            ServerConfig instance populated from environment variables
        """
        # Load .env file if available and requested
        if env_file and DOTENV_AVAILABLE:
            load_dotenv(env_file)
        
        # Create config from environment
        config = cls(
            default_repo_path=os.getenv("DEFAULT_REPO_PATH", "."),
            max_bullet_points=int(os.getenv("MAX_BULLET_POINTS", "5")),
            max_summary_lines=int(os.getenv("MAX_SUMMARY_LINES", "2")),
            changelog_file=os.getenv("CHANGELOG_FILE", "CHANGELOG.md"),
            workspace_dir=os.getenv("WORKSPACE_DIR", "/tmp/git-workspaces"),
            ssh_key_path=os.getenv("GIT_SSH_KEY_PATH"),
            git_username=os.getenv("GIT_USERNAME"),
            git_token=os.getenv("GIT_TOKEN"),
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
