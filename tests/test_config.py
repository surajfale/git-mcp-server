"""Unit tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest

from git_commit_mcp.config import ServerConfig


class TestServerConfigDefaults:
    """Tests for ServerConfig default values."""
    
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = ServerConfig()
        
        # Core settings
        assert config.default_repo_path == "."
        assert config.max_bullet_points == 5
        assert config.max_summary_lines == 2
        assert config.changelog_file == "CHANGELOG.md"
        
        # Transport settings
        assert config.transport_mode == "stdio"
        assert config.http_host == "0.0.0.0"
        assert config.http_port == 8000
        
        # Authentication settings
        assert config.auth_enabled is True
        assert config.auth_token is None
        
        # CORS settings
        assert config.cors_enabled is True
        assert config.cors_origins == ["*"]
        
        # TLS settings
        assert config.tls_enabled is False
        assert config.tls_cert_path is None
        assert config.tls_key_path is None
        
        # Repository settings
        assert config.workspace_dir == "/tmp/git-workspaces"
        assert config.ssh_key_path is None
        assert config.git_username is None
        assert config.git_token is None
        
        # Monitoring settings
        assert config.enable_metrics is True
        assert config.log_level == "INFO"


class TestServerConfigFromEnv:
    """Tests for loading configuration from environment variables."""
    
    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading config from environment with no variables set."""
        # Clear all relevant environment variables
        for key in os.environ.copy():
            if key.startswith(("TRANSPORT_", "HTTP_", "AUTH_", "CORS_", "TLS_", 
                              "GIT_", "WORKSPACE_", "ENABLE_", "LOG_", "MCP_",
                              "DEFAULT_", "MAX_", "CHANGELOG_")):
                monkeypatch.delenv(key, raising=False)
        
        config = ServerConfig.from_env()
        
        # Should use default values
        assert config.transport_mode == "stdio"
        assert config.http_port == 8000
        assert config.log_level == "INFO"
    
    def test_from_env_with_custom_values(self, monkeypatch):
        """Test loading config from environment with custom values."""
        monkeypatch.setenv("TRANSPORT_MODE", "http")
        monkeypatch.setenv("HTTP_HOST", "127.0.0.1")
        monkeypatch.setenv("HTTP_PORT", "9000")
        monkeypatch.setenv("AUTH_ENABLED", "false")
        monkeypatch.setenv("MCP_AUTH_TOKEN", "test-token-123")
        monkeypatch.setenv("CORS_ENABLED", "false")
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com,https://test.com")
        monkeypatch.setenv("LOG_LEVEL", "debug")
        monkeypatch.setenv("MAX_BULLET_POINTS", "10")
        monkeypatch.setenv("MAX_SUMMARY_LINES", "3")
        
        config = ServerConfig.from_env()
        
        assert config.transport_mode == "http"
        assert config.http_host == "127.0.0.1"
        assert config.http_port == 9000
        assert config.auth_enabled is False
        assert config.auth_token == "test-token-123"
        assert config.cors_enabled is False
        assert config.cors_origins == ["https://example.com", "https://test.com"]
        assert config.log_level == "DEBUG"
        assert config.max_bullet_points == 10
        assert config.max_summary_lines == 3
    
    def test_from_env_boolean_parsing(self, monkeypatch):
        """Test that boolean environment variables are parsed correctly."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ]
        
        for value, expected in test_cases:
            monkeypatch.setenv("AUTH_ENABLED", value)
            config = ServerConfig.from_env()
            assert config.auth_enabled is expected, f"Failed for value: {value}"
    
    def test_from_env_cors_origins_parsing(self, monkeypatch):
        """Test that CORS origins are parsed correctly from comma-separated string."""
        monkeypatch.setenv("CORS_ORIGINS", "https://a.com, https://b.com , https://c.com")
        config = ServerConfig.from_env()
        
        assert config.cors_origins == ["https://a.com", "https://b.com", "https://c.com"]
    
    def test_from_env_integer_parsing(self, monkeypatch):
        """Test that integer environment variables are parsed correctly."""
        monkeypatch.setenv("HTTP_PORT", "3000")
        monkeypatch.setenv("MAX_BULLET_POINTS", "7")
        monkeypatch.setenv("MAX_SUMMARY_LINES", "1")
        
        config = ServerConfig.from_env()
        
        assert config.http_port == 3000
        assert config.max_bullet_points == 7
        assert config.max_summary_lines == 1


class TestServerConfigValidation:
    """Tests for configuration validation."""
    
    def test_validate_valid_config(self):
        """Test that validation passes for valid configuration."""
        config = ServerConfig()
        config.validate()  # Should not raise
    
    def test_validate_invalid_transport_mode(self):
        """Test that validation fails for invalid transport mode."""
        config = ServerConfig(transport_mode="invalid")  # type: ignore
        
        with pytest.raises(ValueError, match="Invalid transport_mode"):
            config.validate()
    
    def test_validate_invalid_http_port_too_low(self):
        """Test that validation fails for port number too low."""
        config = ServerConfig(http_port=0)
        
        with pytest.raises(ValueError, match="Invalid http_port"):
            config.validate()
    
    def test_validate_invalid_http_port_too_high(self):
        """Test that validation fails for port number too high."""
        config = ServerConfig(http_port=65536)
        
        with pytest.raises(ValueError, match="Invalid http_port"):
            config.validate()
    
    def test_validate_invalid_max_bullet_points(self):
        """Test that validation fails for invalid max_bullet_points."""
        config = ServerConfig(max_bullet_points=0)
        
        with pytest.raises(ValueError, match="Invalid max_bullet_points"):
            config.validate()
    
    def test_validate_invalid_max_summary_lines(self):
        """Test that validation fails for invalid max_summary_lines."""
        config = ServerConfig(max_summary_lines=0)
        
        with pytest.raises(ValueError, match="Invalid max_summary_lines"):
            config.validate()
    
    def test_validate_invalid_log_level(self):
        """Test that validation fails for invalid log level."""
        config = ServerConfig(log_level="INVALID")
        
        with pytest.raises(ValueError, match="Invalid log_level"):
            config.validate()
    
    def test_validate_valid_log_levels(self):
        """Test that all valid log levels pass validation."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = ServerConfig(log_level=level)
            config.validate()  # Should not raise
    
    def test_validate_tls_enabled_without_cert_path(self):
        """Test that validation fails when TLS is enabled but cert path is missing."""
        config = ServerConfig(tls_enabled=True, tls_key_path="/path/to/key.pem")
        
        with pytest.raises(ValueError, match="tls_cert_path is not set"):
            config.validate()
    
    def test_validate_tls_enabled_without_key_path(self):
        """Test that validation fails when TLS is enabled but key path is missing."""
        config = ServerConfig(tls_enabled=True, tls_cert_path="/path/to/cert.pem")
        
        with pytest.raises(ValueError, match="tls_key_path is not set"):
            config.validate()
    
    def test_validate_tls_enabled_with_nonexistent_cert(self):
        """Test that validation fails when TLS cert file doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=False) as key_file:
            key_path = key_file.name
        
        try:
            config = ServerConfig(
                tls_enabled=True,
                tls_cert_path="/nonexistent/cert.pem",
                tls_key_path=key_path
            )
            
            with pytest.raises(ValueError, match="TLS certificate file not found"):
                config.validate()
        finally:
            Path(key_path).unlink()
    
    def test_validate_tls_enabled_with_nonexistent_key(self):
        """Test that validation fails when TLS key file doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=False) as cert_file:
            cert_path = cert_file.name
        
        try:
            config = ServerConfig(
                tls_enabled=True,
                tls_cert_path=cert_path,
                tls_key_path="/nonexistent/key.pem"
            )
            
            with pytest.raises(ValueError, match="TLS key file not found"):
                config.validate()
        finally:
            Path(cert_path).unlink()
    
    def test_validate_tls_enabled_with_valid_files(self):
        """Test that validation passes when TLS is properly configured."""
        with tempfile.NamedTemporaryFile(delete=False) as cert_file, \
             tempfile.NamedTemporaryFile(delete=False) as key_file:
            cert_path = cert_file.name
            key_path = key_file.name
        
        try:
            config = ServerConfig(
                tls_enabled=True,
                tls_cert_path=cert_path,
                tls_key_path=key_path
            )
            config.validate()  # Should not raise
        finally:
            Path(cert_path).unlink()
            Path(key_path).unlink()
    
    def test_validate_http_mode_with_auth_enabled_no_token(self, monkeypatch):
        """Test that validation fails for HTTP mode with auth but no token."""
        monkeypatch.setenv("TRANSPORT_MODE", "http")
        monkeypatch.setenv("AUTH_ENABLED", "true")
        # Don't set MCP_AUTH_TOKEN
        
        with pytest.raises(ValueError, match="MCP_AUTH_TOKEN is not set"):
            ServerConfig.from_env()
    
    def test_validate_http_mode_with_auth_enabled_with_token(self, monkeypatch):
        """Test that validation passes for HTTP mode with auth and token."""
        monkeypatch.setenv("TRANSPORT_MODE", "http")
        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("MCP_AUTH_TOKEN", "test-token")
        
        config = ServerConfig.from_env()
        assert config.auth_token == "test-token"
    
    def test_validate_http_mode_creates_workspace_dir(self, monkeypatch):
        """Test that validation creates workspace directory for HTTP mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "test-workspace"
            
            monkeypatch.setenv("TRANSPORT_MODE", "http")
            monkeypatch.setenv("AUTH_ENABLED", "false")
            monkeypatch.setenv("WORKSPACE_DIR", str(workspace))
            
            config = ServerConfig.from_env()
            
            assert workspace.exists()
            assert workspace.is_dir()
    
    def test_validate_ssh_key_path_nonexistent(self):
        """Test that validation fails when SSH key file doesn't exist."""
        config = ServerConfig(ssh_key_path="/nonexistent/ssh_key")
        
        with pytest.raises(ValueError, match="SSH key file not found"):
            config.validate()
    
    def test_validate_ssh_key_path_valid(self):
        """Test that validation passes when SSH key file exists."""
        with tempfile.NamedTemporaryFile(delete=False) as ssh_key:
            ssh_key_path = ssh_key.name
        
        try:
            config = ServerConfig(ssh_key_path=ssh_key_path)
            config.validate()  # Should not raise
        finally:
            Path(ssh_key_path).unlink()


class TestServerConfigHelperMethods:
    """Tests for ServerConfig helper methods."""
    
    def test_is_remote_mode_true(self):
        """Test is_remote_mode returns True for HTTP transport."""
        config = ServerConfig(transport_mode="http")
        assert config.is_remote_mode() is True
    
    def test_is_remote_mode_false(self):
        """Test is_remote_mode returns False for stdio transport."""
        config = ServerConfig(transport_mode="stdio")
        assert config.is_remote_mode() is False
    
    def test_is_local_mode_true(self):
        """Test is_local_mode returns True for stdio transport."""
        config = ServerConfig(transport_mode="stdio")
        assert config.is_local_mode() is True
    
    def test_is_local_mode_false(self):
        """Test is_local_mode returns False for HTTP transport."""
        config = ServerConfig(transport_mode="http")
        assert config.is_local_mode() is False


class TestServerConfigErrorHandling:
    """Tests for configuration error handling."""
    
    def test_from_env_invalid_integer_value(self, monkeypatch):
        """Test that invalid integer values raise appropriate errors."""
        monkeypatch.setenv("HTTP_PORT", "not-a-number")
        
        with pytest.raises(ValueError):
            ServerConfig.from_env()
    
    def test_from_env_with_dotenv_file(self, monkeypatch):
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_file.write("TRANSPORT_MODE=http\n")
            env_file.write("HTTP_PORT=9999\n")
            env_file.write("AUTH_ENABLED=false\n")
            env_file.write("LOG_LEVEL=WARNING\n")
            env_path = env_file.name
        
        try:
            # Clear environment to ensure we're loading from file
            for key in ["TRANSPORT_MODE", "HTTP_PORT", "AUTH_ENABLED", "LOG_LEVEL"]:
                monkeypatch.delenv(key, raising=False)
            
            config = ServerConfig.from_env(env_file=env_path)
            
            assert config.transport_mode == "http"
            assert config.http_port == 9999
            assert config.auth_enabled is False
            assert config.log_level == "WARNING"
        finally:
            Path(env_path).unlink()
    
    @pytest.mark.skipif(os.name == 'nt', reason="Permission tests unreliable on Windows")
    def test_validate_workspace_dir_permission_error(self, monkeypatch):
        """Test that validation handles permission errors for workspace directory."""
        # This test is platform-dependent and may not work on all systems
        # We'll create a directory and try to make it read-only
        with tempfile.TemporaryDirectory() as tmpdir:
            readonly_parent = Path(tmpdir) / "readonly"
            readonly_parent.mkdir()
            
            # Try to make it read-only (may not work on all platforms)
            try:
                readonly_parent.chmod(0o444)
                workspace = readonly_parent / "workspace"
                
                config = ServerConfig(
                    transport_mode="http",
                    auth_enabled=False,
                    workspace_dir=str(workspace)
                )
                
                with pytest.raises(ValueError, match="Cannot create workspace directory"):
                    config.validate()
            finally:
                # Restore permissions for cleanup
                readonly_parent.chmod(0o755)
