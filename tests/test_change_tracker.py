"""Unit tests for ChangeTracker component."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from git import Repo, DiffIndex, Diff
from git.exc import GitCommandError

from git_commit_mcp.change_tracker import ChangeTracker
from git_commit_mcp.models import ChangeSet


class TestChangeTracker:
    """Tests for ChangeTracker component."""
    
    @pytest.fixture
    def tracker(self):
        """Create a ChangeTracker instance for testing."""
        return ChangeTracker()
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        repo = Mock(spec=Repo)
        repo.index = Mock()
        repo.untracked_files = []
        return repo
    
    def _create_mock_diff(self, change_type, a_path=None, b_path=None, 
                          renamed=False, rename_from=None, rename_to=None):
        """Helper to create a mock Diff object."""
        diff = Mock(spec=Diff)
        diff.a_path = a_path
        diff.b_path = b_path
        diff.renamed_file = renamed
        diff.rename_from = rename_from
        diff.rename_to = rename_to
        diff.deleted_file = (change_type == 'deleted')
        diff.new_file = (change_type == 'new')
        return diff
    
    def test_get_changes_with_modified_files_only(self, tracker, mock_repo):
        """Test detecting only modified files."""
        # Setup: Create mock diffs for modified files
        modified_diff1 = self._create_mock_diff('modified', 
                                                 a_path='src/file1.py', 
                                                 b_path='src/file1.py')
        modified_diff2 = self._create_mock_diff('modified', 
                                                 a_path='src/file2.py', 
                                                 b_path='src/file2.py')
        
        mock_repo.index.diff.side_effect = [
            [modified_diff1],  # unstaged changes
            [modified_diff2]   # staged changes
        ]
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert len(changes.modified) == 2
        assert 'src/file1.py' in changes.modified
        assert 'src/file2.py' in changes.modified
        assert len(changes.added) == 0
        assert len(changes.deleted) == 0
        assert len(changes.renamed) == 0
    
    def test_get_changes_with_added_files_only(self, tracker, mock_repo):
        """Test detecting only added files."""
        # Setup: Create mock diffs for new files
        new_diff = self._create_mock_diff('new', b_path='src/new_file.py')
        
        mock_repo.index.diff.side_effect = [
            [new_diff],  # unstaged changes
            []           # staged changes
        ]
        mock_repo.untracked_files = ['untracked.py']
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert len(changes.added) == 2
        assert 'src/new_file.py' in changes.added
        assert 'untracked.py' in changes.added
        assert len(changes.modified) == 0
        assert len(changes.deleted) == 0
        assert len(changes.renamed) == 0
    
    def test_get_changes_with_deleted_files_only(self, tracker, mock_repo):
        """Test detecting only deleted files."""
        # Setup: Create mock diffs for deleted files
        deleted_diff1 = self._create_mock_diff('deleted', a_path='src/old_file1.py')
        deleted_diff2 = self._create_mock_diff('deleted', a_path='src/old_file2.py')
        
        mock_repo.index.diff.side_effect = [
            [deleted_diff1],  # unstaged changes
            [deleted_diff2]   # staged changes
        ]
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert len(changes.deleted) == 2
        assert 'src/old_file1.py' in changes.deleted
        assert 'src/old_file2.py' in changes.deleted
        assert len(changes.modified) == 0
        assert len(changes.added) == 0
        assert len(changes.renamed) == 0
    
    def test_get_changes_with_renamed_files(self, tracker, mock_repo):
        """Test detecting renamed files."""
        # Setup: Create mock diff for renamed file
        renamed_diff = self._create_mock_diff('renamed', 
                                               renamed=True,
                                               rename_from='src/old_name.py',
                                               rename_to='src/new_name.py')
        
        mock_repo.index.diff.side_effect = [
            [renamed_diff],  # unstaged changes
            []               # staged changes
        ]
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert len(changes.renamed) == 1
        assert ('src/old_name.py', 'src/new_name.py') in changes.renamed
        assert len(changes.modified) == 0
        assert len(changes.added) == 0
        assert len(changes.deleted) == 0
    
    def test_get_changes_with_mixed_changes(self, tracker, mock_repo):
        """Test detecting multiple types of changes simultaneously."""
        # Setup: Create various types of changes
        modified_diff = self._create_mock_diff('modified', 
                                                a_path='src/modified.py', 
                                                b_path='src/modified.py')
        new_diff = self._create_mock_diff('new', b_path='src/new.py')
        deleted_diff = self._create_mock_diff('deleted', a_path='src/deleted.py')
        renamed_diff = self._create_mock_diff('renamed',
                                               renamed=True,
                                               rename_from='src/old.py',
                                               rename_to='src/renamed.py')
        
        mock_repo.index.diff.side_effect = [
            [modified_diff, deleted_diff],  # unstaged changes
            [new_diff, renamed_diff]        # staged changes
        ]
        mock_repo.untracked_files = ['untracked.txt']
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert len(changes.modified) == 1
        assert 'src/modified.py' in changes.modified
        
        assert len(changes.added) == 2
        assert 'src/new.py' in changes.added
        assert 'untracked.txt' in changes.added
        
        assert len(changes.deleted) == 1
        assert 'src/deleted.py' in changes.deleted
        
        assert len(changes.renamed) == 1
        assert ('src/old.py', 'src/renamed.py') in changes.renamed
    
    def test_get_changes_with_no_changes(self, tracker, mock_repo):
        """Test when there are no changes in the repository."""
        # Setup: Empty diffs
        mock_repo.index.diff.side_effect = [
            [],  # unstaged changes
            []   # staged changes
        ]
        mock_repo.untracked_files = []
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify
        assert changes.is_empty()
        assert len(changes.modified) == 0
        assert len(changes.added) == 0
        assert len(changes.deleted) == 0
        assert len(changes.renamed) == 0
    
    def test_get_changes_with_empty_repository(self, tracker, mock_repo):
        """Test handling of empty repository (no HEAD)."""
        # Setup: Simulate GitCommandError when trying to diff against HEAD
        mock_repo.index.diff.side_effect = [
            [],  # unstaged changes (no error)
            GitCommandError('git diff', 128)  # staged changes fail (no HEAD)
        ]
        mock_repo.untracked_files = ['initial_file.py']
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify - should handle gracefully and still detect untracked files
        assert len(changes.added) == 1
        assert 'initial_file.py' in changes.added
        assert changes.total_files() == 1
    
    def test_get_changes_avoids_duplicate_files(self, tracker, mock_repo):
        """Test that files appearing in both staged and unstaged are not duplicated."""
        # Setup: Same file in both staged and unstaged diffs
        modified_diff1 = self._create_mock_diff('modified', 
                                                 a_path='src/file.py', 
                                                 b_path='src/file.py')
        modified_diff2 = self._create_mock_diff('modified', 
                                                 a_path='src/file.py', 
                                                 b_path='src/file.py')
        
        mock_repo.index.diff.side_effect = [
            [modified_diff1],  # unstaged changes
            [modified_diff2]   # staged changes (same file)
        ]
        
        # Execute
        changes = tracker.get_changes(mock_repo)
        
        # Verify - should only appear once
        assert len(changes.modified) == 1
        assert 'src/file.py' in changes.modified
