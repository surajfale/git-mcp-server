"""Unit tests for ChangelogManager component."""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from git_commit_mcp.changelog_manager import ChangelogManager


class TestChangelogManager:
    """Tests for ChangelogManager component."""
    
    @pytest.fixture
    def manager(self):
        """Create a ChangelogManager instance for testing."""
        return ChangelogManager()
    
    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a temporary directory to simulate a repository."""
        return tmp_path
    
    # Tests for create_changelog_if_missing
    
    def test_create_changelog_if_missing_creates_file(self, manager, temp_repo):
        """Test that changelog file is created when it doesn't exist."""
        changelog_path = temp_repo / "CHANGELOG.md"
        
        # Verify file doesn't exist initially
        assert not changelog_path.exists()
        
        # Execute
        manager.create_changelog_if_missing(str(temp_repo))
        
        # Verify file was created
        assert changelog_path.exists()
        content = changelog_path.read_text(encoding='utf-8')
        assert "# Changelog" in content
        assert "## [Unreleased]" in content
    
    def test_create_changelog_if_missing_does_not_overwrite_existing(self, manager, temp_repo):
        """Test that existing changelog file is not overwritten."""
        changelog_path = temp_repo / "CHANGELOG.md"
        existing_content = "# My Custom Changelog\n\nExisting content"
        changelog_path.write_text(existing_content, encoding='utf-8')
        
        # Execute
        manager.create_changelog_if_missing(str(temp_repo))
        
        # Verify content was not changed
        content = changelog_path.read_text(encoding='utf-8')
        assert content == existing_content
    
    def test_create_changelog_if_missing_raises_io_error(self, manager, temp_repo):
        """Test that IOError is raised when file creation fails."""
        # Use a non-existent path to simulate IO error
        invalid_path = str(temp_repo / "nonexistent" / "deeply" / "nested" / "path")
        
        with pytest.raises(IOError) as exc_info:
            manager.create_changelog_if_missing(invalid_path)
        
        assert "Failed to create changelog file" in str(exc_info.value)
    
    # Tests for update_changelog
    
    def test_update_changelog_appends_entry_after_unreleased(self, manager, temp_repo):
        """Test that new entry is inserted after [Unreleased] section."""
        # Setup: Create changelog with existing content
        changelog_path = temp_repo / "CHANGELOG.md"
        initial_content = """# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### 2025-10-18 10:00:00 - abc1234 [LOCAL]

fix: Previous commit

- Fixed a bug
"""
        changelog_path.write_text(initial_content, encoding='utf-8')
        
        # Execute
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="def5678901234567890",
                commit_message="feat(auth): Add authentication\n\n- Add login feature",
                pushed=True,
                repo_path=str(temp_repo)
            )
        
        # Verify
        content = changelog_path.read_text(encoding='utf-8')
        
        # New entry should be after [Unreleased] but before old entry
        assert "## [Unreleased]" in content
        assert "### 2025-10-19 14:30:45 - def5678 [PUSHED]" in content
        assert "feat(auth): Add authentication" in content
        
        # Verify chronological order (newest first)
        new_entry_pos = content.find("2025-10-19 14:30:45")
        old_entry_pos = content.find("2025-10-18 10:00:00")
        assert new_entry_pos < old_entry_pos
    
    def test_update_changelog_creates_file_if_missing(self, manager, temp_repo):
        """Test that changelog is created if it doesn't exist."""
        changelog_path = temp_repo / "CHANGELOG.md"
        
        # Verify file doesn't exist
        assert not changelog_path.exists()
        
        # Execute
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message="feat: Initial commit",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        # Verify file was created and entry was added
        assert changelog_path.exists()
        content = changelog_path.read_text(encoding='utf-8')
        assert "# Changelog" in content
        assert "## [Unreleased]" in content
        assert "### 2025-10-19 14:30:45 - abc1234 [LOCAL]" in content
    
    def test_update_changelog_with_pushed_status(self, manager, temp_repo):
        """Test that pushed commits are marked with [PUSHED]."""
        manager.create_changelog_if_missing(str(temp_repo))
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message="feat: New feature",
                pushed=True,
                repo_path=str(temp_repo)
            )
        
        content = (temp_repo / "CHANGELOG.md").read_text(encoding='utf-8')
        assert "[PUSHED]" in content
        assert "[LOCAL]" not in content
    
    def test_update_changelog_with_local_status(self, manager, temp_repo):
        """Test that unpushed commits are marked with [LOCAL]."""
        manager.create_changelog_if_missing(str(temp_repo))
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message="feat: New feature",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        content = (temp_repo / "CHANGELOG.md").read_text(encoding='utf-8')
        assert "[LOCAL]" in content
        assert "[PUSHED]" not in content
    
    def test_update_changelog_uses_short_hash(self, manager, temp_repo):
        """Test that only first 7 characters of commit hash are used."""
        manager.create_changelog_if_missing(str(temp_repo))
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abcdef1234567890abcdef",
                commit_message="feat: Test",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        content = (temp_repo / "CHANGELOG.md").read_text(encoding='utf-8')
        assert "abcdef1" in content
        assert "abcdef1234567890abcdef" not in content
    
    def test_update_changelog_preserves_multiline_commit_message(self, manager, temp_repo):
        """Test that multiline commit messages are preserved."""
        manager.create_changelog_if_missing(str(temp_repo))
        
        multiline_message = """feat(api): Add new API endpoint

- Add POST /api/users endpoint
- Add validation for user data
- Add error handling
- Update API documentation
- Add integration tests"""
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message=multiline_message,
                pushed=True,
                repo_path=str(temp_repo)
            )
        
        content = (temp_repo / "CHANGELOG.md").read_text(encoding='utf-8')
        assert "feat(api): Add new API endpoint" in content
        assert "- Add POST /api/users endpoint" in content
        assert "- Add integration tests" in content
    
    def test_update_changelog_maintains_reverse_chronological_order(self, manager, temp_repo):
        """Test that multiple entries are kept in reverse chronological order."""
        manager.create_changelog_if_missing(str(temp_repo))
        
        # Add first entry
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 10, 0, 0)
            manager.update_changelog(
                commit_hash="first123",
                commit_message="feat: First commit",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        # Add second entry
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 11, 0, 0)
            manager.update_changelog(
                commit_hash="second456",
                commit_message="fix: Second commit",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        # Add third entry
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 12, 0, 0)
            manager.update_changelog(
                commit_hash="third789",
                commit_message="docs: Third commit",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        content = (temp_repo / "CHANGELOG.md").read_text(encoding='utf-8')
        
        # Verify order: newest (12:00) should come before older entries
        third_pos = content.find("2025-10-19 12:00:00")
        second_pos = content.find("2025-10-19 11:00:00")
        first_pos = content.find("2025-10-19 10:00:00")
        
        assert third_pos < second_pos < first_pos
    
    def test_update_changelog_without_unreleased_section(self, manager, temp_repo):
        """Test that entry is appended when [Unreleased] section is missing."""
        # Create changelog without [Unreleased] section
        changelog_path = temp_repo / "CHANGELOG.md"
        initial_content = """# Changelog

Some custom content without unreleased section.
"""
        changelog_path.write_text(initial_content, encoding='utf-8')
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message="feat: New feature",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        content = changelog_path.read_text(encoding='utf-8')
        assert "### 2025-10-19 14:30:45 - abc1234 [LOCAL]" in content
        assert "feat: New feature" in content
    
    def test_update_changelog_raises_io_error_on_write_failure(self, manager, temp_repo):
        """Test that IOError is raised when file write fails."""
        manager.create_changelog_if_missing(str(temp_repo))
        changelog_path = temp_repo / "CHANGELOG.md"
        
        # Make file read-only to simulate write error
        changelog_path.chmod(0o444)
        
        try:
            with pytest.raises(IOError) as exc_info:
                manager.update_changelog(
                    commit_hash="abc1234567890",
                    commit_message="feat: Test",
                    pushed=False,
                    repo_path=str(temp_repo)
                )
            
            assert "Failed to update changelog" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            changelog_path.chmod(0o644)
    
    # Tests for _format_entry
    
    def test_format_entry_with_pushed_status(self, manager):
        """Test entry formatting with pushed status."""
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            entry = manager._format_entry(
                commit_hash="abcdef1234567890",
                commit_message="feat: Test feature",
                pushed=True
            )
        
        assert "### 2025-10-19 14:30:45 - abcdef1 [PUSHED]" in entry
        assert "feat: Test feature" in entry
    
    def test_format_entry_with_local_status(self, manager):
        """Test entry formatting with local status."""
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            entry = manager._format_entry(
                commit_hash="abcdef1234567890",
                commit_message="fix: Bug fix",
                pushed=False
            )
        
        assert "### 2025-10-19 14:30:45 - abcdef1 [LOCAL]" in entry
        assert "fix: Bug fix" in entry
    
    def test_format_entry_includes_full_commit_message(self, manager):
        """Test that full commit message is included in entry."""
        multiline_message = """feat(auth): Add authentication

- Add login endpoint
- Add JWT token generation
- Add password hashing"""
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            entry = manager._format_entry(
                commit_hash="abc1234567890",
                commit_message=multiline_message,
                pushed=True
            )
        
        assert "feat(auth): Add authentication" in entry
        assert "- Add login endpoint" in entry
        assert "- Add JWT token generation" in entry
        assert "- Add password hashing" in entry
    
    # Tests for custom changelog filename
    
    def test_custom_changelog_filename(self, temp_repo):
        """Test using a custom changelog filename."""
        manager = ChangelogManager(changelog_file="HISTORY.md")
        
        manager.create_changelog_if_missing(str(temp_repo))
        
        history_path = temp_repo / "HISTORY.md"
        assert history_path.exists()
        assert not (temp_repo / "CHANGELOG.md").exists()
    
    def test_update_with_custom_changelog_filename(self, temp_repo):
        """Test updating a custom changelog filename."""
        manager = ChangelogManager(changelog_file="HISTORY.md")
        
        with patch('git_commit_mcp.changelog_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 10, 19, 14, 30, 45)
            manager.update_changelog(
                commit_hash="abc1234567890",
                commit_message="feat: Test",
                pushed=False,
                repo_path=str(temp_repo)
            )
        
        history_path = temp_repo / "HISTORY.md"
        assert history_path.exists()
        content = history_path.read_text(encoding='utf-8')
        assert "### 2025-10-19 14:30:45 - abc1234 [LOCAL]" in content
