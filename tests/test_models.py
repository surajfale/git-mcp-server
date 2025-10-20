"""Unit tests for data models."""

import pytest
from git_commit_mcp.models import ChangeSet


class TestChangeSet:
    """Tests for ChangeSet model."""
    
    def test_is_empty_with_no_changes(self):
        """Test that is_empty returns True when no changes exist."""
        changeset = ChangeSet()
        assert changeset.is_empty() is True
    
    def test_is_empty_with_modified_files(self):
        """Test that is_empty returns False when files are modified."""
        changeset = ChangeSet(modified=["file1.py"])
        assert changeset.is_empty() is False
    
    def test_is_empty_with_added_files(self):
        """Test that is_empty returns False when files are added."""
        changeset = ChangeSet(added=["new_file.py"])
        assert changeset.is_empty() is False
    
    def test_is_empty_with_deleted_files(self):
        """Test that is_empty returns False when files are deleted."""
        changeset = ChangeSet(deleted=["old_file.py"])
        assert changeset.is_empty() is False
    
    def test_is_empty_with_renamed_files(self):
        """Test that is_empty returns False when files are renamed."""
        changeset = ChangeSet(renamed=[("old.py", "new.py")])
        assert changeset.is_empty() is False
    
    def test_total_files_with_no_changes(self):
        """Test that total_files returns 0 when no changes exist."""
        changeset = ChangeSet()
        assert changeset.total_files() == 0
    
    def test_total_files_with_single_change_type(self):
        """Test total_files with only one type of change."""
        changeset = ChangeSet(modified=["file1.py", "file2.py"])
        assert changeset.total_files() == 2
    
    def test_total_files_with_mixed_changes(self):
        """Test total_files with multiple types of changes."""
        changeset = ChangeSet(
            modified=["file1.py", "file2.py"],
            added=["file3.py"],
            deleted=["file4.py"],
            renamed=[("old.py", "new.py")]
        )
        assert changeset.total_files() == 5
