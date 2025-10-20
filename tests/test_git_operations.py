"""Unit tests for GitOperationsManager component."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from git import Repo, Remote, PushInfo
from git.exc import GitCommandError, InvalidGitRepositoryError

from git_commit_mcp.git_operations import GitOperationsManager
from git_commit_mcp.models import ChangeSet


class TestGitOperationsManager:
    """Tests for GitOperationsManager component."""
    
    @pytest.fixture
    def manager(self):
        """Create a GitOperationsManager instance for testing."""
        return GitOperationsManager()
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.index = Mock()
        repo.head = Mock()
        repo.active_branch = Mock()
        repo.remotes = []
        return repo
    
    # Tests for stage_changes
    
    def test_stage_changes_with_modified_files(self, manager, mock_repo):
        """Test staging modified files."""
        changes = ChangeSet(modified=["file1.py", "file2.py"])
        
        manager.stage_changes(mock_repo, changes)
        
        mock_repo.index.add.assert_called_once_with(["file1.py", "file2.py"])
    
    def test_stage_changes_with_added_files(self, manager, mock_repo):
        """Test staging added files."""
        changes = ChangeSet(added=["new_file.py"])
        
        manager.stage_changes(mock_repo, changes)
        
        mock_repo.index.add.assert_called_once_with(["new_file.py"])
    
    def test_stage_changes_with_deleted_files(self, manager, mock_repo):
        """Test staging deleted files."""
        changes = ChangeSet(deleted=["old_file.py"])
        
        manager.stage_changes(mock_repo, changes)
        
        mock_repo.index.remove.assert_called_once_with(["old_file.py"])
    
    def test_stage_changes_with_renamed_files(self, manager, mock_repo):
        """Test staging renamed files."""
        changes = ChangeSet(renamed=[("old_name.py", "new_name.py")])
        
        manager.stage_changes(mock_repo, changes)
        
        # Should remove old path and add new path
        mock_repo.index.remove.assert_called_once_with(["old_name.py"], working_tree=True)
        mock_repo.index.add.assert_called_once_with(["new_name.py"])
    
    def test_stage_changes_with_mixed_changes(self, manager, mock_repo):
        """Test staging multiple types of changes."""
        changes = ChangeSet(
            modified=["modified.py"],
            added=["added.py"],
            deleted=["deleted.py"],
            renamed=[("old.py", "new.py")]
        )
        
        manager.stage_changes(mock_repo, changes)
        
        # Verify all operations were called
        assert mock_repo.index.add.call_count == 3  # modified, added, renamed (new)
        assert mock_repo.index.remove.call_count == 2  # deleted, renamed (old)
    
    def test_stage_changes_with_empty_changeset(self, manager, mock_repo):
        """Test staging with no changes."""
        changes = ChangeSet()
        
        manager.stage_changes(mock_repo, changes)
        
        # Should not call any staging operations
        mock_repo.index.add.assert_not_called()
        mock_repo.index.remove.assert_not_called()
    
    def test_stage_changes_raises_invalid_repository_error(self, manager, mock_repo):
        """Test that InvalidGitRepositoryError is raised for invalid repo."""
        changes = ChangeSet(modified=["file.py"])
        mock_repo.index.add.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        with pytest.raises(InvalidGitRepositoryError) as exc_info:
            manager.stage_changes(mock_repo, changes)
        
        assert "Invalid Git repository" in str(exc_info.value)
    
    def test_stage_changes_raises_git_command_error(self, manager, mock_repo):
        """Test that GitCommandError is raised when staging fails."""
        changes = ChangeSet(modified=["file.py"])
        mock_repo.index.add.side_effect = GitCommandError(
            command=['git', 'add'],
            status=1,
            stderr="Permission denied"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.stage_changes(mock_repo, changes)
        
        assert "Failed to stage changes" in str(exc_info.value)
    
    # Tests for create_commit
    
    def test_create_commit_success(self, manager, mock_repo):
        """Test successful commit creation."""
        message = "feat: Add new feature"
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.index.commit.return_value = mock_commit
        
        commit_hash = manager.create_commit(mock_repo, message)
        
        assert commit_hash == "abc123def456"
        mock_repo.index.commit.assert_called_once_with(message)
    
    def test_create_commit_raises_invalid_repository_error(self, manager, mock_repo):
        """Test that InvalidGitRepositoryError is raised for invalid repo."""
        message = "test commit"
        mock_repo.index.commit.side_effect = InvalidGitRepositoryError("Not a git repo")
        
        with pytest.raises(InvalidGitRepositoryError) as exc_info:
            manager.create_commit(mock_repo, message)
        
        assert "Invalid Git repository" in str(exc_info.value)
    
    def test_create_commit_raises_git_command_error(self, manager, mock_repo):
        """Test that GitCommandError is raised when commit fails."""
        message = "test commit"
        mock_repo.index.commit.side_effect = GitCommandError(
            command=['git', 'commit'],
            status=1,
            stderr="Nothing to commit"
        )
        
        with pytest.raises(GitCommandError) as exc_info:
            manager.create_commit(mock_repo, message)
        
        assert "Failed to create commit" in str(exc_info.value)
    
    # Tests for get_current_branch
    
    def test_get_current_branch_success(self, manager, mock_repo):
        """Test getting current branch name."""
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        
        branch_name = manager.get_current_branch(mock_repo)
        
        assert branch_name == "main"
    
    def test_get_current_branch_with_detached_head(self, manager, mock_repo):
        """Test that TypeError is raised when HEAD is detached."""
        mock_repo.head.is_detached = True
        
        with pytest.raises(TypeError) as exc_info:
            manager.get_current_branch(mock_repo)
        
        assert "HEAD is detached" in str(exc_info.value)
    
    def test_get_current_branch_raises_invalid_repository_error(self, manager, mock_repo):
        """Test that InvalidGitRepositoryError is raised for invalid repo."""
        mock_repo.head.is_detached = False
        mock_repo.active_branch = Mock()
        type(mock_repo.active_branch).name = property(Mock(side_effect=InvalidGitRepositoryError("Not a git repo")))
        
        with pytest.raises(InvalidGitRepositoryError) as exc_info:
            manager.get_current_branch(mock_repo)
        
        assert "Invalid Git repository" in str(exc_info.value)
    
    # Tests for push_to_remote
    
    def test_push_to_remote_success(self, manager, mock_repo):
        """Test successful push to remote."""
        # Setup
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        
        mock_remote = Mock(spec=Remote)
        mock_remote.name = "origin"
        mock_repo.remotes = [mock_remote]
        
        mock_push_info = Mock(spec=PushInfo)
        mock_push_info.flags = 0  # No error flags
        mock_push_info.ERROR = 1024  # PushInfo.ERROR constant
        mock_push_info.summary = "main -> main"
        mock_remote.push.return_value = [mock_push_info]
        
        # Execute
        result = manager.push_to_remote(mock_repo)
        
        # Verify
        assert result["success"] is True
        assert result["branch"] == "main"
        assert result["remote"] == "origin"
        assert "Successfully pushed" in result["message"]
        mock_remote.push.assert_called_once_with("main")
    
    def test_push_to_remote_with_no_remote_configured(self, manager, mock_repo):
        """Test that ValueError is raised when no remote is configured."""
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        mock_repo.remotes = []
        
        with pytest.raises(ValueError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "No remote repository configured" in str(exc_info.value)
    
    def test_push_to_remote_with_push_error_flag(self, manager, mock_repo):
        """Test that GitCommandError is raised when push has error flag."""
        # Setup
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        
        mock_remote = Mock(spec=Remote)
        mock_remote.name = "origin"
        mock_repo.remotes = [mock_remote]
        
        mock_push_info = Mock(spec=PushInfo)
        mock_push_info.ERROR = 1024  # PushInfo.ERROR constant
        mock_push_info.flags = 1024  # Set flags to ERROR
        mock_push_info.summary = "Error: rejected"
        mock_remote.push.return_value = [mock_push_info]
        
        # Execute & Verify
        with pytest.raises(GitCommandError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "Push failed" in str(exc_info.value)
    
    def test_push_to_remote_with_empty_push_info(self, manager, mock_repo):
        """Test that GitCommandError is raised when push returns no info."""
        # Setup
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        
        mock_remote = Mock(spec=Remote)
        mock_remote.name = "origin"
        mock_repo.remotes = [mock_remote]
        mock_remote.push.return_value = []
        
        # Execute & Verify
        with pytest.raises(GitCommandError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "Push operation returned no information" in str(exc_info.value)
    
    def test_push_to_remote_raises_git_command_error(self, manager, mock_repo):
        """Test that GitCommandError is raised when push fails."""
        # Setup
        mock_repo.head.is_detached = False
        mock_repo.active_branch.name = "main"
        
        mock_remote = Mock(spec=Remote)
        mock_remote.name = "origin"
        mock_repo.remotes = [mock_remote]
        mock_remote.push.side_effect = GitCommandError(
            command=['git', 'push'],
            status=1,
            stderr="Authentication failed"
        )
        
        # Execute & Verify
        with pytest.raises(GitCommandError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "Failed to push to remote" in str(exc_info.value)
    
    def test_push_to_remote_raises_invalid_repository_error(self, manager, mock_repo):
        """Test that InvalidGitRepositoryError is raised for invalid repo."""
        mock_repo.head.is_detached = False
        mock_repo.active_branch = Mock()
        type(mock_repo.active_branch).name = property(Mock(side_effect=InvalidGitRepositoryError("Not a git repo")))
        
        with pytest.raises(InvalidGitRepositoryError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "Invalid Git repository" in str(exc_info.value)
    
    def test_push_to_remote_with_detached_head(self, manager, mock_repo):
        """Test that TypeError is raised when trying to push with detached HEAD."""
        mock_repo.head.is_detached = True
        
        with pytest.raises(TypeError) as exc_info:
            manager.push_to_remote(mock_repo)
        
        assert "HEAD is detached" in str(exc_info.value)
