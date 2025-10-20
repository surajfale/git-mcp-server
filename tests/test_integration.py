"""Integration tests for Git Commit MCP Server.

This module contains end-to-end tests that verify the complete workflow
of the git_commit_and_push tool, including:
- Change detection
- Commit message generation
- Git operations (commit, push)
- Changelog updates
- MCP protocol compliance
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from git import Repo
from git.exc import GitCommandError

from git_commit_mcp.server import execute_git_commit_and_push


class TestIntegrationWorkflow:
    """End-to-end integration tests for the complete Git workflow."""
    
    @pytest.fixture
    def test_repo(self):
        """Create a temporary Git repository for testing.
        
        Yields:
            Path: Path to the temporary repository
        """
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)
        
        try:
            # Initialize Git repository
            repo = Repo.init(repo_path)
            
            # Configure Git user (required for commits)
            with repo.config_writer() as config:
                config.set_value("user", "name", "Test User")
                config.set_value("user", "email", "test@example.com")
            
            # Create initial commit to establish HEAD
            initial_file = repo_path / "README.md"
            initial_file.write_text("# Test Repository\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            
            yield repo_path
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_complete_workflow_with_new_file(self, test_repo):
        """Test complete workflow: add file → commit → verify changelog."""
        # Step 1: Make changes - add a new file
        new_file = test_repo / "src" / "new_feature.py"
        new_file.parent.mkdir(parents=True, exist_ok=True)
        new_file.write_text("def new_feature():\n    pass\n")
        
        # Step 2: Invoke the tool
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Step 3: Verify commit was created
        assert result["success"] is True
        assert result["commit_hash"] is not None
        assert len(result["commit_hash"]) == 40  # Full SHA hash
        assert result["files_changed"] == 1
        assert result["pushed"] is False
        assert result["changelog_updated"] is True
        
        # Verify commit message format
        assert result["commit_message"] is not None
        assert "feat" in result["commit_message"] or "chore" in result["commit_message"]
        
        # Step 4: Verify commit exists in repository
        repo = Repo(test_repo)
        # Note: The latest commit is the changelog commit, so we check the parent
        # The returned commit_hash is the main commit (before changelog commit)
        latest_commit = repo.head.commit
        # The main commit should be either HEAD or HEAD~1 (if changelog was committed)
        if result["changelog_updated"]:
            # If changelog was updated, the main commit is the parent of HEAD
            main_commit = latest_commit.parents[0] if latest_commit.parents else latest_commit
            assert main_commit.hexsha == result["commit_hash"]
        else:
            # If no changelog commit, HEAD should be the main commit
            assert latest_commit.hexsha == result["commit_hash"]
        
        # Step 5: Verify changelog was updated
        changelog_path = test_repo / "CHANGELOG.md"
        assert changelog_path.exists()
        
        changelog_content = changelog_path.read_text()
        assert "# Changelog" in changelog_content
        assert result["commit_hash"][:7] in changelog_content
        assert "[LOCAL]" in changelog_content
    
    def test_complete_workflow_with_modified_file(self, test_repo):
        """Test workflow with modified existing file."""
        # Step 1: Modify existing file
        readme = test_repo / "README.md"
        readme.write_text("# Test Repository\n\nUpdated content\n")
        
        # Step 2: Invoke the tool
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Step 3: Verify results
        assert result["success"] is True
        assert result["files_changed"] == 1
        assert result["commit_hash"] is not None
        
        # Verify commit type (docs for README changes)
        assert "docs" in result["commit_message"]
    
    def test_complete_workflow_with_multiple_changes(self, test_repo):
        """Test workflow with multiple file changes."""
        # Step 1: Make multiple changes
        # Add new file
        new_file = test_repo / "src" / "module.py"
        new_file.parent.mkdir(parents=True, exist_ok=True)
        new_file.write_text("class Module:\n    pass\n")
        
        # Modify existing file
        readme = test_repo / "README.md"
        readme.write_text("# Test Repository\n\nMultiple changes\n")
        
        # Add another new file
        config_file = test_repo / "config.json"
        config_file.write_text('{"setting": "value"}\n')
        
        # Step 2: Invoke the tool
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Step 3: Verify results
        assert result["success"] is True
        assert result["files_changed"] == 3
        assert result["commit_hash"] is not None
        
        # Verify all files are in the commit
        repo = Repo(test_repo)
        latest_commit = repo.head.commit
        # If changelog was updated, check the parent commit (main commit)
        if result["changelog_updated"] and latest_commit.parents:
            main_commit = latest_commit.parents[0]
            committed_files = list(main_commit.stats.files.keys())
        else:
            committed_files = list(latest_commit.stats.files.keys())
        assert "src/module.py" in committed_files
        assert "README.md" in committed_files
        assert "config.json" in committed_files
    
    def test_workflow_with_no_changes(self, test_repo):
        """Test workflow when there are no changes to commit."""
        # Invoke tool without making any changes
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Verify appropriate response
        assert result["success"] is True
        assert result["message"] == "No changes to commit"
        assert result["files_changed"] == 0
        assert result["commit_hash"] is None
        assert result["changelog_updated"] is False
    
    def test_workflow_with_deleted_file(self, test_repo):
        """Test workflow with deleted file."""
        # Step 1: Create and commit a file first
        temp_file = test_repo / "temp.txt"
        temp_file.write_text("Temporary content\n")
        
        repo = Repo(test_repo)
        repo.index.add(["temp.txt"])
        repo.index.commit("Add temp file")
        
        # Step 2: Delete the file
        temp_file.unlink()
        
        # Step 3: Invoke the tool
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Step 4: Verify results
        assert result["success"] is True
        assert result["files_changed"] == 1
        assert result["commit_hash"] is not None
        
        # Verify file is deleted in commit
        latest_commit = repo.head.commit
        # If changelog was updated, check the parent commit (main commit)
        if result["changelog_updated"] and latest_commit.parents:
            main_commit = latest_commit.parents[0]
            assert "temp.txt" in main_commit.stats.files
        else:
            assert "temp.txt" in latest_commit.stats.files
    
    def test_changelog_format_and_ordering(self, test_repo):
        """Test that changelog maintains proper format and chronological order."""
        # Create first commit
        file1 = test_repo / "file1.txt"
        file1.write_text("Content 1\n")
        
        result1 = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Create second commit
        file2 = test_repo / "file2.txt"
        file2.write_text("Content 2\n")
        
        result2 = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Verify both commits succeeded
        assert result1["success"] is True
        assert result2["success"] is True
        
        # Read changelog
        changelog_path = test_repo / "CHANGELOG.md"
        changelog_content = changelog_path.read_text()
        
        # Verify format
        assert "# Changelog" in changelog_content
        assert "## [Unreleased]" in changelog_content
        
        # Verify both commits are present
        assert result1["commit_hash"][:7] in changelog_content
        assert result2["commit_hash"][:7] in changelog_content
        
        # Verify chronological order (newest first)
        pos1 = changelog_content.find(result1["commit_hash"][:7])
        pos2 = changelog_content.find(result2["commit_hash"][:7])
        assert pos2 < pos1, "Newer commit should appear before older commit"


class TestErrorHandling:
    """Integration tests for error handling scenarios."""
    
    def test_invalid_repository_path(self):
        """Test handling of non-existent repository path."""
        result = execute_git_commit_and_push(
            repository_path="/nonexistent/path",
            confirm_push=False
        )
        
        assert result["success"] is False
        assert result["error"] is not None
        assert "does not exist" in result["error"]
    
    def test_not_a_git_repository(self):
        """Test handling of directory that is not a Git repository."""
        # Create temporary directory without Git
        temp_dir = tempfile.mkdtemp()
        
        try:
            result = execute_git_commit_and_push(
                repository_path=temp_dir,
                confirm_push=False
            )
            
            assert result["success"] is False
            assert result["error"] is not None
            assert "not a git repository" in result["error"].lower()
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_commit_without_git_config(self):
        """Test handling of repository without user configuration."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)
        
        try:
            # Initialize repo without user config
            repo = Repo.init(repo_path)
            
            # Create a file to commit
            test_file = repo_path / "test.txt"
            test_file.write_text("Test content\n")
            
            # Attempt to commit (should fail without user config)
            result = execute_git_commit_and_push(
                repository_path=str(repo_path),
                confirm_push=False
            )
            
            # Should fail with appropriate error
            assert result["success"] is False
            assert result["error"] is not None
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestMCPProtocolCompliance:
    """Tests to verify MCP protocol compliance."""
    
    @pytest.fixture
    def test_repo(self):
        """Create a temporary Git repository for testing."""
        temp_dir = tempfile.mkdtemp()
        repo_path = Path(temp_dir)
        
        try:
            repo = Repo.init(repo_path)
            
            with repo.config_writer() as config:
                config.set_value("user", "name", "Test User")
                config.set_value("user", "email", "test@example.com")
            
            initial_file = repo_path / "README.md"
            initial_file.write_text("# Test\n")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            
            yield repo_path
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_tool_returns_dictionary(self, test_repo):
        """Test that tool returns a dictionary (required for MCP)."""
        # Make a change
        test_file = test_repo / "test.txt"
        test_file.write_text("Test\n")
        
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Verify return type
        assert isinstance(result, dict)
    
    def test_tool_has_required_fields(self, test_repo):
        """Test that tool response contains all required fields."""
        # Make a change
        test_file = test_repo / "test.txt"
        test_file.write_text("Test\n")
        
        result = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Verify all required fields are present
        required_fields = [
            "success",
            "commit_hash",
            "commit_message",
            "files_changed",
            "pushed",
            "changelog_updated",
            "message"
        ]
        
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
    
    def test_tool_handles_optional_parameters(self, test_repo):
        """Test that tool handles optional parameters correctly."""
        # Make a change
        test_file = test_repo / "test.txt"
        test_file.write_text("Test\n")
        
        # Test with default parameters
        result1 = execute_git_commit_and_push()
        
        # Test with explicit parameters
        result2 = execute_git_commit_and_push(
            repository_path=str(test_repo),
            confirm_push=False
        )
        
        # Both should return valid results
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert "success" in result2
    
    def test_tool_error_response_format(self):
        """Test that error responses follow consistent format."""
        result = execute_git_commit_and_push(
            repository_path="/invalid/path",
            confirm_push=False
        )
        
        # Verify error response structure
        assert isinstance(result, dict)
        assert result["success"] is False
        assert "error" in result
        assert result["error"] is not None
        assert "message" in result
        assert result["message"] is not None
