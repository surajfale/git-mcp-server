"""Unit tests for RepositoryManager component."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from threading import Thread
import time

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from git_commit_mcp.repository_manager import RepositoryManager, GitCredentials


class TestGitCredentials:
    """Tests for GitCredentials dataclass."""
    
    def test_validate_ssh_credentials_success(self):
        """Test validation of valid SSH credentials."""
        creds = GitCredentials(auth_type="ssh", ssh_key="/path/to/key")
        creds.validate()  # Should not raise
    
    def test_validate_ssh_credentials_missing_key(self):
        """Test validation fails when SSH key is missing."""
        creds = GitCredentials(auth_type="ssh")
        
        with pytest.raises(ValueError) as exc_info:
            creds.validate()
        
        assert "SSH authentication requires ssh_key" in str(exc_info.value)
    
    def test_validate_https_credentials_success(self):
        """Test validation of valid HTTPS credentials."""
        creds = GitCredentials(
            auth_type="https",
            username="user",
            password="pass"
        )
        creds.validate()  # Should not raise
    
    def test_validate_https_credentials_missing_username(self):
        """Test validation fails when username is missing."""
        creds = GitCredentials(auth_type="https", password="pass")
        
        with pytest.raises(ValueError) as exc_info:
            creds.validate()
        
        assert "HTTPS authentication requires username and password" in str(exc_info.value)
    
    def test_validate_https_credentials_missing_password(self):
        """Test validation fails when password is missing."""
        creds = GitCredentials(auth_type="https", username="user")
        
        with pytest.raises(ValueError) as exc_info:
            creds.validate()
        
        assert "HTTPS authentication requires username and password" in str(exc_info.value)
    
    def test_validate_token_credentials_success(self):
        """Test validation of valid token credentials."""
        creds = GitCredentials(auth_type="token", token="ghp_token123")
        creds.validate()  # Should not raise
    
    def test_validate_token_credentials_missing_token(self):
        """Test validation fails when token is missing."""
        creds = GitCredentials(auth_type="token")
        
        with pytest.raises(ValueError) as exc_info:
            creds.validate()
        
        assert "Token authentication requires token" in str(exc_info.value)


class TestRepositoryManager:
    """Tests for RepositoryManager component."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def manager(self, temp_workspace):
        """Create a RepositoryManager instance with temp workspace."""
        return RepositoryManager(workspace_dir=temp_workspace)
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.remotes = []
        return repo
    
    # Tests for initialization
    
    def test_init_creates_workspace_directory(self, temp_workspace):
        """Test that initialization creates the workspace directory."""
        workspace = os.path.join(temp_workspace, "new_workspace")
        manager = RepositoryManager(workspace_dir=workspace)
        
        assert os.path.exists(workspace)
        assert os.path.isdir(workspace)
    
    def test_init_with_existing_workspace(self, temp_workspace):
        """Test initialization with existing workspace directory."""
        manager = RepositoryManager(workspace_dir=temp_workspace)
        
        assert manager.workspace_dir == Path(temp_workspace)
        assert os.path.exists(temp_workspace)
    
    # Tests for _generate_repo_id
    
    def test_generate_repo_id_consistency(self, manager):
        """Test that same URL generates same repo ID."""
        url = "https://github.com/user/repo.git"
        
        id1 = manager._generate_repo_id(url)
        id2 = manager._generate_repo_id(url)
        
        assert id1 == id2
        assert len(id1) == 16  # SHA256 hash truncated to 16 chars
    
    def test_generate_repo_id_uniqueness(self, manager):
        """Test that different URLs generate different repo IDs."""
        url1 = "https://github.com/user/repo1.git"
        url2 = "https://github.com/user/repo2.git"
        
        id1 = manager._generate_repo_id(url1)
        id2 = manager._generate_repo_id(url2)
        
        assert id1 != id2
    
    # Tests for _get_repo_path
    
    def test_get_repo_path(self, manager):
        """Test getting repository path."""
        url = "https://github.com/user/repo.git"
        
        path = manager._get_repo_path(url)
        
        assert path.parent == manager.workspace_dir
        assert len(path.name) == 16
    
    # Tests for configure_ssh_key
    
    def test_configure_ssh_key_success(self, manager, temp_workspace):
        """Test configuring SSH key."""
        # Create a temporary SSH key file
        key_path = os.path.join(temp_workspace, "test_key")
        with open(key_path, "w") as f:
            f.write("fake ssh key")
        
        manager.configure_ssh_key(key_path)
        
        assert "GIT_SSH_COMMAND" in os.environ
        assert key_path in os.environ["GIT_SSH_COMMAND"]
        assert "StrictHostKeyChecking=no" in os.environ["GIT_SSH_COMMAND"]
    
    def test_configure_ssh_key_file_not_found(self, manager):
        """Test that FileNotFoundError is raised for non-existent key."""
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.configure_ssh_key("/nonexistent/key")
        
        assert "SSH key file not found" in str(exc_info.value)
    
    def test_configure_ssh_key_not_a_file(self, manager, temp_workspace):
        """Test that ValueError is raised when path is not a file."""
        # Create a directory instead of a file
        dir_path = os.path.join(temp_workspace, "not_a_file")
        os.makedirs(dir_path)
        
        with pytest.raises(ValueError) as exc_info:
            manager.configure_ssh_key(dir_path)
        
        assert "SSH key path is not a file" in str(exc_info.value)
    
    # Tests for _build_auth_url
    
    def test_build_auth_url_without_credentials(self, manager):
        """Test building URL without credentials."""
        url = "https://github.com/user/repo.git"
        
        result = manager._build_auth_url(url, None)
        
        assert result == url
    
    def test_build_auth_url_with_https_credentials(self, manager):
        """Test building URL with HTTPS credentials."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(
            auth_type="https",
            username="testuser",
            password="testpass"
        )
        
        result = manager._build_auth_url(url, creds)
        
        assert result == "https://testuser:testpass@github.com/user/repo.git"
    
    def test_build_auth_url_with_token_credentials(self, manager):
        """Test building URL with token credentials."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(auth_type="token", token="ghp_token123")
        
        result = manager._build_auth_url(url, creds)
        
        assert result == "https://ghp_token123@github.com/user/repo.git"
    
    def test_build_auth_url_with_ssh_url(self, manager):
        """Test that SSH URLs are not modified."""
        url = "git@github.com:user/repo.git"
        creds = GitCredentials(auth_type="ssh", ssh_key="/path/to/key")
        
        result = manager._build_auth_url(url, creds)
        
        assert result == url
    
    def test_build_auth_url_with_non_https_url(self, manager):
        """Test that non-HTTPS URLs are not modified."""
        url = "http://github.com/user/repo.git"
        creds = GitCredentials(
            auth_type="https",
            username="user",
            password="pass"
        )
        
        result = manager._build_auth_url(url, creds)
        
        assert result == url
    
    # Tests for get_or_clone_repository with SSH
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_ssh_clone_success(self, mock_repo_class, manager, temp_workspace):
        """Test cloning a repository with SSH authentication."""
        url = "git@github.com:user/repo.git"
        
        # Create a fake SSH key file
        key_path = os.path.join(temp_workspace, "fake_key")
        with open(key_path, "w") as f:
            f.write("fake ssh key")
        
        creds = GitCredentials(auth_type="ssh", ssh_key=key_path)
        
        # Mock successful clone
        mock_repo_instance = Mock(spec=Repo)
        mock_repo_class.clone_from.return_value = mock_repo_instance
        
        result = manager.get_or_clone_repository(url, creds)
        
        assert result == mock_repo_instance
        mock_repo_class.clone_from.assert_called_once()
        assert "GIT_SSH_COMMAND" in os.environ
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_ssh_authentication_failure(
        self, mock_repo_class, manager, temp_workspace
    ):
        """Test SSH authentication failure during clone."""
        url = "git@github.com:user/repo.git"
        
        # Create a fake SSH key file
        key_path = os.path.join(temp_workspace, "fake_key")
        with open(key_path, "w") as f:
            f.write("fake ssh key")
        
        creds = GitCredentials(auth_type="ssh", ssh_key=key_path)
        
        # Mock authentication failure
        mock_repo_class.clone_from.side_effect = GitCommandError(
            command=['git', 'clone'],
            status=128,
            stderr="authentication failed"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.get_or_clone_repository(url, creds)
        
        assert "Authentication failed" in str(exc_info.value)
    
    # Tests for get_or_clone_repository with HTTPS
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_https_clone_success(self, mock_repo_class, manager):
        """Test cloning a repository with HTTPS authentication."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(
            auth_type="https",
            username="testuser",
            password="testpass"
        )
        
        # Mock successful clone
        mock_repo_instance = Mock(spec=Repo)
        mock_repo_class.clone_from.return_value = mock_repo_instance
        
        result = manager.get_or_clone_repository(url, creds)
        
        assert result == mock_repo_instance
        # Verify clone was called with authenticated URL
        call_args = mock_repo_class.clone_from.call_args
        assert "testuser:testpass" in call_args[0][0]
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_token_clone_success(self, mock_repo_class, manager):
        """Test cloning a repository with token authentication."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(auth_type="token", token="ghp_token123")
        
        # Mock successful clone
        mock_repo_instance = Mock(spec=Repo)
        mock_repo_class.clone_from.return_value = mock_repo_instance
        
        result = manager.get_or_clone_repository(url, creds)
        
        assert result == mock_repo_instance
        # Verify clone was called with token in URL
        call_args = mock_repo_class.clone_from.call_args
        assert "ghp_token123" in call_args[0][0]
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_https_authentication_failure(
        self, mock_repo_class, manager
    ):
        """Test HTTPS authentication failure during clone."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(
            auth_type="https",
            username="testuser",
            password="wrongpass"
        )
        
        # Mock authentication failure
        mock_repo_class.clone_from.side_effect = GitCommandError(
            command=['git', 'clone'],
            status=128,
            stderr="Authentication failed for 'https://github.com/user/repo.git'"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.get_or_clone_repository(url, creds)
        
        assert "Authentication failed" in str(exc_info.value)
    
    # Tests for get_or_clone_repository - existing repository
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_existing_repo_pull_success(
        self, mock_repo_class, manager, temp_workspace
    ):
        """Test pulling updates from existing cloned repository."""
        url = "https://github.com/user/repo.git"
        
        # Create fake repository directory
        repo_id = manager._generate_repo_id(url)
        repo_path = manager.workspace_dir / repo_id
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        
        # Mock existing repository
        mock_repo_instance = Mock(spec=Repo)
        mock_remote = Mock()
        mock_remote.pull = Mock()
        mock_repo_instance.remotes = [mock_remote]
        mock_repo_class.return_value = mock_repo_instance
        
        result = manager.get_or_clone_repository(url)
        
        assert result == mock_repo_instance
        mock_remote.pull.assert_called_once()
        mock_repo_class.clone_from.assert_not_called()
    
    @patch('git_commit_mcp.repository_manager.Repo')
    @patch('shutil.rmtree')
    def test_get_or_clone_repository_existing_repo_pull_failure_reclone(
        self, mock_rmtree, mock_repo_class, manager, temp_workspace
    ):
        """Test re-cloning when pull fails on existing repository."""
        url = "https://github.com/user/repo.git"
        
        # Create fake repository directory
        repo_id = manager._generate_repo_id(url)
        repo_path = manager.workspace_dir / repo_id
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()
        
        # Mock existing repository that fails to pull
        mock_repo_instance_fail = Mock(spec=Repo)
        mock_remote = Mock()
        mock_remote.pull.side_effect = GitCommandError(
            command=['git', 'pull'],
            status=1,
            stderr="Pull failed"
        )
        mock_repo_instance_fail.remotes = [mock_remote]
        
        # Mock successful re-clone
        mock_repo_instance_success = Mock(spec=Repo)
        
        mock_repo_class.side_effect = [
            mock_repo_instance_fail,  # First call (existing repo)
        ]
        mock_repo_class.clone_from.return_value = mock_repo_instance_success
        
        result = manager.get_or_clone_repository(url)
        
        assert result == mock_repo_instance_success
        mock_rmtree.assert_called_once()
        mock_repo_class.clone_from.assert_called_once()
    
    # Tests for get_or_clone_repository - error handling
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_network_error(self, mock_repo_class, manager):
        """Test network error during clone."""
        url = "https://github.com/user/repo.git"
        
        mock_repo_class.clone_from.side_effect = GitCommandError(
            command=['git', 'clone'],
            status=128,
            stderr="Could not resolve host: github.com"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.get_or_clone_repository(url)
        
        assert "Could not resolve host" in str(exc_info.value)
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_get_or_clone_repository_generic_error(self, mock_repo_class, manager):
        """Test generic error during clone."""
        url = "https://github.com/user/repo.git"
        
        mock_repo_class.clone_from.side_effect = GitCommandError(
            command=['git', 'clone'],
            status=1,
            stderr="Some other error"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.get_or_clone_repository(url)
        
        assert "Failed to clone repository" in str(exc_info.value)
    
    def test_get_or_clone_repository_invalid_credentials(self, manager):
        """Test that invalid credentials raise ValueError."""
        url = "https://github.com/user/repo.git"
        creds = GitCredentials(auth_type="ssh")  # Missing ssh_key
        
        with pytest.raises(ValueError) as exc_info:
            manager.get_or_clone_repository(url, creds)
        
        assert "SSH authentication requires ssh_key" in str(exc_info.value)
    
    # Tests for get_local_repository
    
    def test_get_local_repository_success(self, manager, temp_workspace):
        """Test accessing an existing local repository."""
        # Create a real git repository for testing
        repo_path = os.path.join(temp_workspace, "test_repo")
        os.makedirs(repo_path)
        
        with patch('git_commit_mcp.repository_manager.Repo') as mock_repo_class:
            mock_repo_instance = Mock(spec=Repo)
            mock_repo_class.return_value = mock_repo_instance
            
            result = manager.get_local_repository(repo_path)
            
            assert result == mock_repo_instance
            mock_repo_class.assert_called_once()
    
    def test_get_local_repository_path_not_exists(self, manager):
        """Test that FileNotFoundError is raised for non-existent path."""
        with pytest.raises(FileNotFoundError) as exc_info:
            manager.get_local_repository("/nonexistent/path")
        
        assert "Repository path does not exist" in str(exc_info.value)
    
    def test_get_local_repository_not_a_git_repo(self, manager, temp_workspace):
        """Test that InvalidGitRepositoryError is raised for non-git directory."""
        # Create a directory that's not a git repo
        non_git_path = os.path.join(temp_workspace, "not_a_repo")
        os.makedirs(non_git_path)
        
        with patch('git_commit_mcp.repository_manager.Repo') as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repo")
            
            with pytest.raises(InvalidGitRepositoryError) as exc_info:
                manager.get_local_repository(non_git_path)
            
            assert "Not a valid Git repository" in str(exc_info.value)
    
    # Tests for cleanup_workspace
    
    def test_cleanup_workspace_success(self, manager, temp_workspace):
        """Test cleaning up a cloned repository."""
        # Create a fake repository directory
        repo_id = "test_repo_id"
        repo_path = manager.workspace_dir / repo_id
        repo_path.mkdir(parents=True)
        (repo_path / "test_file.txt").touch()
        
        # Add a lock for this repo
        manager._get_repo_lock(repo_id)
        assert repo_id in manager._locks
        
        manager.cleanup_workspace(repo_id)
        
        assert not repo_path.exists()
        assert repo_id not in manager._locks
    
    def test_cleanup_workspace_nonexistent_repo(self, manager):
        """Test cleanup of non-existent repository (should not raise)."""
        repo_id = "nonexistent_repo"
        
        # Should not raise an error
        manager.cleanup_workspace(repo_id)
    
    def test_cleanup_workspace_permission_error(self, manager, temp_workspace):
        """Test cleanup failure due to permissions."""
        repo_id = "test_repo_id"
        repo_path = manager.workspace_dir / repo_id
        repo_path.mkdir(parents=True)
        
        with patch('shutil.rmtree') as mock_rmtree:
            mock_rmtree.side_effect = OSError("Permission denied")
            
            with pytest.raises(OSError) as exc_info:
                manager.cleanup_workspace(repo_id)
            
            assert "Failed to remove repository" in str(exc_info.value)
    
    # Tests for cleanup_all_workspaces
    
    def test_cleanup_all_workspaces_success(self, manager, temp_workspace):
        """Test cleaning up all cloned repositories."""
        # Create multiple fake repository directories
        repo1_path = manager.workspace_dir / "repo1"
        repo2_path = manager.workspace_dir / "repo2"
        repo1_path.mkdir()
        repo2_path.mkdir()
        
        # Add locks
        manager._get_repo_lock("repo1")
        manager._get_repo_lock("repo2")
        
        count = manager.cleanup_all_workspaces()
        
        assert count == 2
        assert not repo1_path.exists()
        assert not repo2_path.exists()
        assert len(manager._locks) == 0
    
    def test_cleanup_all_workspaces_empty_workspace(self, manager):
        """Test cleanup when workspace is empty."""
        count = manager.cleanup_all_workspaces()
        
        assert count == 0
    
    def test_cleanup_all_workspaces_partial_failure(self, manager, temp_workspace):
        """Test cleanup continues even if some directories fail."""
        # Create multiple fake repository directories
        repo1_path = manager.workspace_dir / "repo1"
        repo2_path = manager.workspace_dir / "repo2"
        repo1_path.mkdir()
        repo2_path.mkdir()
        
        with patch('shutil.rmtree') as mock_rmtree:
            # First call fails, second succeeds
            mock_rmtree.side_effect = [OSError("Permission denied"), None]
            
            count = manager.cleanup_all_workspaces()
            
            # Should continue despite failure
            assert count == 1
            assert len(manager._locks) == 0
    
    def test_cleanup_all_workspaces_nonexistent_workspace(self, temp_workspace):
        """Test cleanup when workspace directory doesn't exist."""
        workspace = os.path.join(temp_workspace, "nonexistent")
        manager = RepositoryManager(workspace_dir=workspace)
        
        # Remove the workspace directory
        shutil.rmtree(workspace)
        
        count = manager.cleanup_all_workspaces()
        
        assert count == 0
    
    # Tests for workspace locking (concurrent access)
    
    @patch('git_commit_mcp.repository_manager.Repo')
    def test_concurrent_access_locking(self, mock_repo_class, manager):
        """Test that concurrent access to same repository is properly locked."""
        url = "https://github.com/user/repo.git"
        
        # Mock clone operation with delay
        def slow_clone(*args, **kwargs):
            time.sleep(0.1)
            return Mock(spec=Repo)
        
        mock_repo_class.clone_from.side_effect = slow_clone
        
        results = []
        errors = []
        
        def clone_repo():
            try:
                repo = manager.get_or_clone_repository(url)
                results.append(repo)
            except Exception as e:
                errors.append(e)
        
        # Start two threads trying to clone the same repo
        thread1 = Thread(target=clone_repo)
        thread2 = Thread(target=clone_repo)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Both should succeed, but clone should only be called once
        # (second thread waits for first to complete)
        assert len(results) == 2
        assert len(errors) == 0
    
    def test_get_repo_lock_creates_lock(self, manager):
        """Test that _get_repo_lock creates a new lock if it doesn't exist."""
        repo_id = "test_repo"
        
        lock = manager._get_repo_lock(repo_id)
        
        assert repo_id in manager._locks
        assert manager._locks[repo_id] is lock
    
    def test_get_repo_lock_returns_existing_lock(self, manager):
        """Test that _get_repo_lock returns existing lock."""
        repo_id = "test_repo"
        
        lock1 = manager._get_repo_lock(repo_id)
        lock2 = manager._get_repo_lock(repo_id)
        
        assert lock1 is lock2
