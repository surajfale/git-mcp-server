"""Main MCP server implementation."""

import os
from pathlib import Path
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from fastmcp import FastMCP

from git_commit_mcp.models import CommitResult, ServerConfig
from git_commit_mcp.change_tracker import ChangeTracker
from git_commit_mcp.message_generator import CommitMessageGenerator
from git_commit_mcp.git_operations import GitOperationsManager
from git_commit_mcp.changelog_manager import ChangelogManager

# Initialize FastMCP server
mcp = FastMCP("git-commit-server")

# Initialize configuration
config = ServerConfig()


def execute_git_commit_and_push(
    repository_path: str = ".",
    confirm_push: bool = False
) -> dict:
    """
    Track changes, generate commit message, commit, and optionally push.
    
    This is the core implementation function that can be called directly
    or through the MCP tool interface.
    
    Args:
        repository_path: Path to the Git repository (default: current directory)
        confirm_push: Whether to push to remote after committing (default: False)
    
    Returns:
        Dictionary containing commit result information:
            - success: Whether the operation completed successfully
            - commit_hash: The SHA hash of the created commit
            - commit_message: The full commit message used
            - files_changed: Number of files affected
            - pushed: Whether the commit was pushed to remote
            - changelog_updated: Whether CHANGELOG.md was updated
            - message: Human-readable status message
            - error: Error message if operation failed
    """
    # Initialize result with default values
    result = CommitResult(
        success=False,
        commit_hash=None,
        commit_message=None,
        files_changed=0,
        pushed=False,
        changelog_updated=False,
        message="",
        error=None
    )
    
    try:
        # Validate and resolve repository path
        repo_path = Path(repository_path).resolve()
        
        if not repo_path.exists():
            result.error = f"Repository path does not exist: {repository_path}"
            result.message = result.error
            return result.__dict__
        
        # Initialize Git repository
        try:
            repo = Repo(repo_path)
        except InvalidGitRepositoryError:
            result.error = f"Not a git repository: {repository_path}"
            result.message = result.error
            return result.__dict__
        
        # Initialize components
        change_tracker = ChangeTracker()
        message_generator = CommitMessageGenerator(
            max_bullet_points=config.max_bullet_points,
            max_summary_lines=config.max_summary_lines
        )
        git_ops = GitOperationsManager()
        changelog_mgr = ChangelogManager(changelog_file=config.changelog_file)
        
        # Step 1: Track changes
        try:
            changes = change_tracker.get_changes(repo)
        except GitCommandError as e:
            result.error = f"Failed to track changes: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Check if there are any changes
        if changes.is_empty():
            result.success = True
            result.message = "No changes to commit"
            result.files_changed = 0
            return result.__dict__
        
        result.files_changed = changes.total_files()
        
        # Step 2: Generate commit message
        try:
            commit_message = message_generator.generate_message(changes, repo)
            result.commit_message = commit_message
        except Exception as e:
            result.error = f"Failed to generate commit message: {str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Step 3: Stage changes
        try:
            git_ops.stage_changes(repo, changes)
        except (GitCommandError, InvalidGitRepositoryError) as e:
            result.error = f"Failed to stage changes: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Step 4: Create commit
        try:
            commit_hash = git_ops.create_commit(repo, commit_message)
            result.commit_hash = commit_hash
        except (GitCommandError, InvalidGitRepositoryError) as e:
            result.error = f"Failed to create commit: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Step 5: Handle push (if confirmed)
        if confirm_push:
            try:
                push_result = git_ops.push_to_remote(repo)
                result.pushed = push_result["success"]
                result.message = push_result["message"]
            except ValueError as e:
                # No remote configured - not a critical error
                result.pushed = False
                result.message = f"Commit created successfully but not pushed: {str(e)}"
            except (GitCommandError, InvalidGitRepositoryError) as e:
                # Push failed - commit still succeeded
                result.pushed = False
                error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
                result.message = f"Commit created successfully but push failed: {error_msg}"
        else:
            result.pushed = False
            result.message = f"Commit created successfully (not pushed)"
        
        # Step 6: Update changelog
        try:
            changelog_mgr.update_changelog(
                commit_hash=commit_hash,
                commit_message=commit_message,
                pushed=result.pushed,
                repo_path=str(repo_path)
            )
            result.changelog_updated = True
        except IOError as e:
            # Changelog update failure is not critical
            result.changelog_updated = False
            # Append warning to message
            result.message += f" (Warning: Failed to update changelog: {str(e)})"
        
        # Mark as successful
        result.success = True
        
        # Enhance message with commit details
        short_hash = commit_hash[:7] if commit_hash else "unknown"
        if not result.message:
            result.message = f"Successfully committed {result.files_changed} file(s) [{short_hash}]"
        
        return result.__dict__
        
    except Exception as e:
        # Catch-all for unexpected errors
        result.error = f"Unexpected error: {str(e)}"
        result.message = result.error
        return result.__dict__


@mcp.tool()
def git_commit_and_push(
    repository_path: str = ".",
    confirm_push: bool = False
) -> dict:
    """
    Track changes, generate commit message, commit, and optionally push.
    
    This tool automates the Git commit workflow by:
    1. Detecting all changes in the repository
    2. Generating a conventional commit message
    3. Staging and committing the changes
    4. Optionally pushing to remote (if confirm_push is True)
    5. Updating the CHANGELOG.md file
    
    Args:
        repository_path: Path to the Git repository (default: current directory)
        confirm_push: Whether to push to remote after committing (default: False)
    
    Returns:
        Dictionary containing commit result information:
            - success: Whether the operation completed successfully
            - commit_hash: The SHA hash of the created commit
            - commit_message: The full commit message used
            - files_changed: Number of files affected
            - pushed: Whether the commit was pushed to remote
            - changelog_updated: Whether CHANGELOG.md was updated
            - message: Human-readable status message
            - error: Error message if operation failed
    """
    return execute_git_commit_and_push(repository_path, confirm_push)
