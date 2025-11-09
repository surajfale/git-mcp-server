"""Main MCP server implementation."""

import os
import time
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
from git_commit_mcp.logging_config import (
    get_logger,
    log_git_operation,
    setup_logging
)
from git_commit_mcp.ai_client import AIClient

# Get logger for this module
logger = get_logger(__name__)

# Initialize FastMCP server
mcp = FastMCP("git-commit-server")

# Initialize configuration from environment so MCP launch picks up settings
config = ServerConfig.from_env()

# Initialize repository manager (lazy initialization)
_repo_manager: Optional[RepositoryManager] = None


def find_git_repository(start_path: str) -> Optional[Path]:
    """Find the nearest git repository by walking up the directory tree.
    
    This function searches for a .git directory starting from the given path
    and walking up to the filesystem root, similar to how git itself works.
    
    Args:
        start_path: Starting directory path to search from
        
    Returns:
        Path to the git repository root, or None if not found
    """
    current = Path(start_path).resolve()
    
    # Walk up the directory tree
    for path in [current] + list(current.parents):
        git_dir = path / ".git"
        if git_dir.exists() and (git_dir.is_dir() or git_dir.is_file()):
            return path
    
    return None


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
    operation_start_time = time.time()
    
    # Log operation start
    logger.info(
        "Starting git commit and push operation",
        extra={
            "repository_path": repository_path,
            "confirm_push": confirm_push
        }
    )
    
    try:
        # Determine if repository_path is a URL or local path
        is_remote_repo = (
            repository_path.startswith("http://") or
            repository_path.startswith("https://") or
            repository_path.startswith("git@") or
            repository_path.startswith("ssh://")
        )
        # Enforce SSH-only for remote URLs if configured
        if is_remote_repo and config.force_ssh_only:
            if repository_path.startswith("http://") or repository_path.startswith("https://"):
                result.error = "Remote repository must use SSH (git@ or ssh://)."
                result.message = result.error
                return result.__dict__
        
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
                logger.info(
                    "Accessing remote repository",
                    extra={"repository_url": repository_path, "auth_type": credentials.auth_type if credentials else "none"}
                )
                repo = repo_manager.get_or_clone_repository(repository_path, credentials)
                repo_path = Path(repo.working_dir)
                logger.info(
                    "Remote repository accessed successfully",
                    extra={"repository_url": repository_path, "local_path": str(repo_path)}
                )
            else:
                # Handle local repository path
                # If path is ".", try to find git repo by walking up directory tree
                if repository_path == ".":
                    # Try to find git repo from current working directory
                    cwd = Path.cwd()
                    found_repo = find_git_repository(str(cwd))
                    if found_repo:
                        repo_path = found_repo
                        logger.info(
                            "Found git repository by walking up directory tree",
                            extra={"found_path": str(repo_path), "started_from": str(cwd)}
                        )
                    else:
                        # Fallback to resolving "." normally
                        repo_path = Path(repository_path).resolve()
                else:
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

            commit_message = None
            # Try AI first if enabled
            if config.enable_ai:
                try:
                    ai_client = AIClient(config)
                    prompt = _build_ai_prompt_from_changes(changes_for_message, repo)
                    commit_message = ai_client.generate_commit_message(prompt)
                except Exception:
                    commit_message = None

            # Fallback to heuristic generator
            if not commit_message:
                commit_message = message_generator.generate_message(changes_for_message, repo)

            result.commit_message = commit_message
        except Exception as e:
            result.error = f"Failed to generate commit message: {str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Step 3: Update changelog with placeholder hash BEFORE committing
        # This way CHANGELOG.md will be included in the same commit
        placeholder_hash = "0000000"
        try:
            changelog_mgr.update_changelog(
                commit_hash=placeholder_hash,
                commit_message=commit_message,
                pushed=False,
                repo_path=str(repo_path)
            )
        except IOError as e:
            # Changelog update failure is not critical, continue
            logger.warning("Failed to update changelog", extra={"error": str(e)})
        
        # Step 4: Stage changes (including CHANGELOG.md)
        try:
            git_ops.stage_changes(repo, changes)
            
            # Also stage CHANGELOG.md if it was updated
            changelog_path = repo_path / config.changelog_file
            if changelog_path.exists():
                repo.index.add([config.changelog_file])
        except (GitCommandError, InvalidGitRepositoryError) as e:
            result.error = f"Failed to stage changes: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            result.message = result.error
            return result.__dict__
        
        # Step 5: Create commit
        try:
            logger.info("Creating commit", extra={"files_changed": result.files_changed})
            commit_hash = git_ops.create_commit(repo, commit_message)
            result.commit_hash = commit_hash
            result.changelog_updated = True
            logger.info(
                "Commit created successfully",
                extra={"commit_hash": commit_hash, "files_changed": result.files_changed}
            )
        except (GitCommandError, InvalidGitRepositoryError) as e:
            result.error = f"Failed to create commit: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            result.message = result.error
            logger.error("Failed to create commit", extra={"error": result.error})
            return result.__dict__
        
        # Step 6: Update CHANGELOG with actual commit hash (amend the commit)
        try:
            changelog_mgr.replace_commit_hash(
                old_hash=placeholder_hash,
                new_hash=commit_hash,
                repo_path=str(repo_path),
                pushed=False
            )
            # Amend the commit to include the updated CHANGELOG
            repo.index.add([config.changelog_file])
            repo.git.commit('--amend', '--no-edit')
            
            # Update result with the final commit hash after amend
            result.commit_hash = repo.head.commit.hexsha
            
        except (IOError, GitCommandError) as e:
            # Not critical if this fails
            logger.warning("Failed to update changelog with commit hash", extra={"error": str(e)})
        
        # Step 7: Handle push (if confirmed)
        if confirm_push:
            try:
                logger.info("Pushing to remote", extra={"commit_hash": commit_hash})
                push_result = git_ops.push_to_remote(repo)
                result.pushed = push_result["success"]
                result.message = push_result["message"]
                
                # Update CHANGELOG push status if push succeeded
                if result.pushed:
                    try:
                        changelog_mgr.replace_commit_hash(
                            old_hash=commit_hash[:7],
                            new_hash=commit_hash,
                            repo_path=str(repo_path),
                            pushed=True
                        )
                    except IOError as e:
                        logger.warning("Failed to update changelog push status", extra={"error": str(e)})
                    
                    logger.info(
                        "Push completed successfully",
                        extra={"commit_hash": commit_hash, "branch": push_result.get("branch")}
                    )
            except ValueError as e:
                # No remote configured - not a critical error
                result.pushed = False
                result.message = f"Commit created successfully but not pushed: {str(e)}"
                logger.warning("No remote configured for push", extra={"error": str(e)})
            except (GitCommandError, InvalidGitRepositoryError) as e:
                # Push failed - commit still succeeded
                result.pushed = False
                error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
                result.message = f"Commit created successfully but push failed: {error_msg}"
                logger.error("Push failed", extra={"error": error_msg, "commit_hash": commit_hash})
        else:
            result.pushed = False
            result.message = f"Commit created successfully (not pushed)"
            logger.info("Push skipped (not confirmed)", extra={"commit_hash": commit_hash})
        
        # Mark as successful
        result.success = True
        
        # Enhance message with commit details
        short_hash = commit_hash[:7] if commit_hash else "unknown"
        if not result.message:
            result.message = f"Successfully committed {result.files_changed} file(s) [{short_hash}]"
        
        # Log final operation result
        operation_duration = time.time() - operation_start_time
        log_git_operation(
            operation="commit_and_push",
            repository=repository_path,
            success=True,
            duration=operation_duration,
            details={
                "commit_hash": commit_hash,
                "files_changed": result.files_changed,
                "pushed": result.pushed,
                "changelog_updated": result.changelog_updated
            }
        )
        
        return result.__dict__
        
    except GitCommandError as e:
        # Git operation error - provide detailed error message
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        result.error = f"Git operation failed: {error_msg}"
        result.message = result.error
        
        # Log error
        operation_duration = time.time() - operation_start_time
        log_git_operation(
            operation="commit_and_push",
            repository=repository_path,
            success=False,
            duration=operation_duration,
            error=result.error
        )
        logger.error("Git command error", extra={"error": error_msg, "repository": repository_path})
        
        return result.__dict__
    except InvalidGitRepositoryError as e:
        # Invalid repository error
        result.error = f"Invalid Git repository: {str(e)}"
        result.message = result.error
        
        # Log error
        operation_duration = time.time() - operation_start_time
        log_git_operation(
            operation="commit_and_push",
            repository=repository_path,
            success=False,
            duration=operation_duration,
            error=result.error
        )
        logger.error("Invalid Git repository", extra={"error": str(e), "repository": repository_path})
        
        return result.__dict__
    except ValueError as e:
        # Configuration or validation error
        result.error = f"Configuration error: {str(e)}"
        result.message = result.error
        
        # Log error
        operation_duration = time.time() - operation_start_time
        log_git_operation(
            operation="commit_and_push",
            repository=repository_path,
            success=False,
            duration=operation_duration,
            error=result.error
        )
        logger.error("Configuration error", extra={"error": str(e), "repository": repository_path})
        
        return result.__dict__
    except Exception as e:
        # Catch-all for unexpected errors
        result.error = f"Unexpected error: {str(e)}"
        result.message = result.error
        
        # Log error
        operation_duration = time.time() - operation_start_time
        log_git_operation(
            operation="commit_and_push",
            repository=repository_path,
            success=False,
            duration=operation_duration,
            error=result.error
        )
        logger.exception("Unexpected error during git operation", extra={"repository": repository_path})
        
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


def _is_remote_url(path: str) -> bool:
    return (
        path.startswith("http://") or
        path.startswith("https://") or
        path.startswith("git@") or
        path.startswith("ssh://")
    )


def _build_ai_prompt_from_changes(changes, repo: Repo, max_files: int = 20, max_diff_lines: int = 100) -> str:
    """Build AI prompt with file changes and diffs for better context.
    
    Args:
        changes: ChangeSet with file changes
        repo: Git repository object
        max_files: Maximum number of files to include
        max_diff_lines: Maximum lines of diff to include per file
        
    Returns:
        Formatted prompt string for AI
    """
    total = changes.total_files()
    parts = [
        "Generate a high-quality Conventional Commit message for these changes.",
        "- Follow types: feat, fix, docs, style, refactor, test, chore",
        "- Keep subject <= 72 chars, imperative",
        f"- Total files changed: {total}",
        "",
        "File changes with diffs:",
    ]
    
    # Get diffs for modified and added files
    try:
        # Get the diff against HEAD
        diffs = repo.head.commit.diff(None, create_patch=True)
        diff_by_file = {d.a_path or d.b_path: d for d in diffs}
    except Exception:
        diff_by_file = {}
    
    if changes.added:
        parts.append("\nAdded:")
        for f in changes.added[:max_files]:
            parts.append(f"  - {f}")
            # Try to get diff for added file
            if f in diff_by_file:
                diff_text = diff_by_file[f].diff.decode('utf-8', errors='ignore') if diff_by_file[f].diff else ""
                if diff_text:
                    lines = diff_text.split('\n')[:max_diff_lines]
                    parts.append("    Diff:")
                    for line in lines:
                        parts.append(f"    {line}")
                        
    if changes.deleted:
        parts.append("\nDeleted:")
        for f in changes.deleted[:max_files]:
            parts.append(f"  - {f}")
            
    if changes.renamed:
        parts.append("\nRenamed:")
        for old, new in changes.renamed[:max_files]:
            parts.append(f"  - {old} -> {new}")
            
    if changes.modified:
        parts.append("\nModified:")
        for f in changes.modified[:max_files]:
            parts.append(f"  - {f}")
            # Try to get diff for modified file
            if f in diff_by_file:
                diff_text = diff_by_file[f].diff.decode('utf-8', errors='ignore') if diff_by_file[f].diff else ""
                if diff_text:
                    lines = diff_text.split('\n')[:max_diff_lines]
                    parts.append("    Diff:")
                    for line in lines:
                        parts.append(f"    {line}")
                        
    return "\n".join(parts)


def execute_generate_commit_message(
    repository_path: str = "."
) -> dict:
    """Core implementation to generate a Conventional Commit message using AI or fallback.

    This function mirrors the MCP tool behavior but can be called directly from Python.

    Returns:
        { success, commit_message, files_changed, message, error?, ai_error? }
    """
    result = {
        "success": False,
        "commit_message": None,
        "files_changed": 0,
        "message": "",
        "error": None,
    }

    try:
        # Enforce SSH-only for remote URLs
        if _is_remote_url(repository_path):
            if repository_path.startswith("http://") or repository_path.startswith("https://"):
                err = "Remote repository must use SSH (git@ or ssh://)."
                result["error"] = err
                result["message"] = err
                return result

        # Access repository
        if _is_remote_url(repository_path):
            repo_manager = get_repository_manager()
            credentials = None
            # If SSH key is configured, use it; otherwise rely on agent
            if config.ssh_key_path:
                credentials = GitCredentials(auth_type="ssh", ssh_key=config.ssh_key_path)
            repo = repo_manager.get_or_clone_repository(repository_path, credentials)
            repo_path = Path(repo.working_dir)
        else:
            # If path is ".", try to find git repo by walking up directory tree
            if repository_path == ".":
                cwd = Path.cwd()
                found_repo = find_git_repository(str(cwd))
                if found_repo:
                    repo_path = found_repo
                else:
                    repo_path = Path(repository_path).resolve()
            else:
                repo_path = Path(repository_path).resolve()
            repo_manager = get_repository_manager()
            repo = repo_manager.get_local_repository(str(repo_path))

        # Track changes
        change_tracker = ChangeTracker()
        changes = change_tracker.get_changes(repo)
        if changes.is_empty():
            result.update({
                "success": True,
                "files_changed": 0,
                "message": "No changes to generate a message for",
                "commit_message": None,
            })
            return result

        result["files_changed"] = changes.total_files()

        # Try AI first
        commit_message = None
        ai_error = None
        if config.enable_ai:
            try:
                ai_client = AIClient(config)
                prompt = _build_ai_prompt_from_changes(changes, repo)
                commit_message = ai_client.generate_commit_message(prompt)
            except Exception as e:
                ai_error = str(e)

        # Fallback to heuristic
        if not commit_message:
            generator = CommitMessageGenerator(
                max_bullet_points=config.max_bullet_points,
                max_summary_lines=config.max_summary_lines,
            )
            commit_message = generator.generate_message(changes, repo)

        result.update({
            "success": True,
            "commit_message": commit_message,
            "message": "Generated commit message" + (" with AI" if ai_error is None and config.enable_ai else " (fallback)"),
        })
        if ai_error:
            result["ai_error"] = ai_error
        return result
    except Exception as e:
        result["error"] = str(e)
        result["message"] = str(e)
        return result


@mcp.tool()
def generate_commit_message(
    repository_path: str = "."
) -> dict:
    """
    Analyze changes and generate a Conventional Commit message using AI.

    - For remote repositories, only SSH URLs are allowed.
    - Uses OpenAI gpt-4o-mini (configurable) when ENABLE_AI=true.
    - Falls back to heuristic generator on failure or when AI is disabled.
    
    Returns:
        { success, commit_message, files_changed, message, error? }
    """
    return execute_generate_commit_message(repository_path)


def run_stdio_server() -> None:
    """Run the MCP server in stdio mode.
    
    This function starts the FastMCP server with stdio transport for
    local MCP client communication. This is the default mode for
    AI assistants that support MCP.
    """
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # When launched as a module (python -m git_commit_mcp.server), start stdio server
    # Configure basic logging (plain text) to avoid interfering with MCP stdio
    try:
        cfg = ServerConfig.from_env()
        setup_logging(log_level=cfg.log_level, use_json=False, log_file=None, stream="stderr")
    except Exception:
        # Fallback to default logging if env config fails
        setup_logging(log_level="INFO", use_json=False, log_file=None, stream="stderr")
    run_stdio_server()
