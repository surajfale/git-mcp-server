"""Main MCP server implementation."""

import os
from pathlib import Path
from typing import Optional
from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from fastmcp import FastMCP

from git_commit_mcp.models import CommitResult
from git_commit_mcp.config import ServerConfig
from git_commit_mcp.change_tracker import ChangeTracker
from git_commit_mcp.message_generator import CommitMessageGenerator
from git_commit_mcp.git_operations import GitOperationsManager
from git_commit_mcp.changelog_manager import ChangelogManager
from git_commit_mcp.repository_manager import RepositoryManager, GitCredentials

# Initialize FastMCP server
mcp = FastMCP("git-commit-server")

# Initialize configuration (can be overridden by loading from environment)
config = ServerConfig()

# Initialize repository manager (lazy initialization)
_repo_manager: Optional[RepositoryManager] = None


def get_repository_manager() -> RepositoryManager:
    """Get or create the global repository manager instance.
    
    Returns:
        RepositoryManager instance configured with current settings
    """
    global _repo_manager
    if _repo_manager is None:
        _repo_manager = RepositoryManager(workspace_dir=config.workspace_dir)
    return _repo_manager


def execute_git_commit_and_push(
    repository_path: str = ".",
    confirm_push: bool = False
) -> dict:
    """
    Track changes, generate commit message, commit, and optionally push.
    
    This is the core implementation function that can be called directly
    or through the MCP tool interface. It supports both local paths and
    remote repository URLs.
    
    Args:
        repository_path: Path to the Git repository or remote URL (default: current directory)
                        Supports:
                        - Local paths: ".", "/path/to/repo", "relative/path"
                        - SSH URLs: "git@github.com:user/repo.git"
                        - HTTPS URLs: "https://github.com/user/repo.git"
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
    
    repo_manager = None
    is_remote_repo = False
    
    try:
        # Determine if repository_path is a URL or local path
        is_remote_repo = (
            repository_path.startswith("http://") or
            repository_path.startswith("https://") or
            repository_path.startswith("git@") or
            repository_path.startswith("ssh://")
        )
        
        # Initialize Git repository
        try:
            if is_remote_repo:
                # Handle remote repository URL
                repo_manager = get_repository_manager()
                
                # Build credentials from config if available
                credentials = None
                if config.ssh_key_path or config.git_username or config.git_token:
                    # Determine auth type based on URL and available credentials
                    if repository_path.startswith("git@") or repository_path.startswith("ssh://"):
                        if config.ssh_key_path:
                            credentials = GitCredentials(
                                auth_type="ssh",
                                ssh_key=config.ssh_key_path
                            )
                    elif repository_path.startswith("http"):
                        if config.git_token:
                            credentials = GitCredentials(
                                auth_type="token",
                                token=config.git_token
                            )
                        elif config.git_username:
                            # Note: For HTTPS with username/password, password should be in config
                            # For now, we'll use token auth as it's more common
                            credentials = GitCredentials(
                                auth_type="token",
                                token=config.git_token or ""
                            )
                
                # Clone or get existing repository
                repo = repo_manager.get_or_clone_repository(repository_path, credentials)
                repo_path = Path(repo.working_dir)
            else:
                # Handle local repository path
                repo_path = Path(repository_path).resolve()
                
                if not repo_path.exists():
                    result.error = f"Repository path does not exist: {repository_path}"
                    result.message = result.error
                    return result.__dict__
                
                repo_manager = get_repository_manager()
                repo = repo_manager.get_local_repository(str(repo_path))
                
        except InvalidGitRepositoryError as e:
            result.error = f"Not a git repository: {repository_path}"
            result.message = result.error
            return result.__dict__
        except GitCommandError as e:
            error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
            result.error = f"Failed to access repository: {error_msg}"
            result.message = result.error
            return result.__dict__
        except FileNotFoundError as e:
            result.error = str(e)
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
        
        # Step 2: Generate commit message (exclude CHANGELOG.md from message)
        try:
            # Filter out CHANGELOG.md for message generation since it's auto-updated
            changes_for_message = changes.exclude_file(config.changelog_file)
            commit_message = message_generator.generate_message(changes_for_message, repo)
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
        
        # Step 6: Update changelog with actual commit info and create a second commit for it
        try:
            changelog_mgr.update_changelog(
                commit_hash=commit_hash,
                commit_message=commit_message,
                pushed=result.pushed,
                repo_path=str(repo_path)
            )
            result.changelog_updated = True
            
            # Stage and commit the changelog update
            changelog_path = repo_path / config.changelog_file
            if changelog_path.exists():
                # Add the changelog file to the index
                repo.index.add([config.changelog_file])
                
                # Check if there are actually changes to commit
                if repo.index.diff("HEAD"):
                    # Create a second commit for the changelog
                    changelog_commit_msg = f"docs: Update CHANGELOG.md for commit {commit_hash[:7]}"
                    repo.index.commit(changelog_commit_msg)
                    
                    # Push the changelog commit if original was pushed
                    if result.pushed:
                        git_ops.push_to_remote(repo)
                        
        except (IOError, GitCommandError) as e:
            # Changelog update failure is not critical
            result.changelog_updated = False
            result.message += f" (Warning: Failed to update changelog: {str(e)})"
        
        # Mark as successful
        result.success = True
        
        # Enhance message with commit details
        short_hash = commit_hash[:7] if commit_hash else "unknown"
        if not result.message:
            result.message = f"Successfully committed {result.files_changed} file(s) [{short_hash}]"
        
        return result.__dict__
        
    except GitCommandError as e:
        # Git operation error - provide detailed error message
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        result.error = f"Git operation failed: {error_msg}"
        result.message = result.error
        return result.__dict__
    except InvalidGitRepositoryError as e:
        # Invalid repository error
        result.error = f"Invalid Git repository: {str(e)}"
        result.message = result.error
        return result.__dict__
    except ValueError as e:
        # Configuration or validation error
        result.error = f"Configuration error: {str(e)}"
        result.message = result.error
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
    
    Supports both local repositories and remote repository URLs.
    For remote repositories, the tool will clone them to a workspace
    and perform operations there.
    
    Args:
        repository_path: Path to the Git repository or remote URL (default: current directory)
                        Supports:
                        - Local paths: ".", "/path/to/repo", "relative/path"
                        - SSH URLs: "git@github.com:user/repo.git"
                        - HTTPS URLs: "https://github.com/user/repo.git"
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


def run_stdio_server() -> None:
    """Run the MCP server in stdio mode.
    
    This function starts the FastMCP server with stdio transport for
    local MCP client communication. This is the default mode for
    AI assistants that support MCP.
    """
    mcp.run(transport="stdio")
