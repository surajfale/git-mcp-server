"""Git operations manager for executing Git commands."""

from typing import Optional
from git import Repo, Remote
from git.exc import GitCommandError, InvalidGitRepositoryError

from git_commit_mcp.models import ChangeSet


class GitOperationsManager:
    """Manages Git operations including staging, committing, and pushing.
    
    This component wraps GitPython operations and provides error handling
    for common Git workflow tasks.
    """
    
    def stage_changes(self, repo: Repo, changes: ChangeSet) -> None:
        """Stage all tracked changes from the ChangeSet.
        
        Stages modified, added, deleted, and renamed files for commit.
        
        Args:
            repo: GitPython Repo object representing the repository
            changes: ChangeSet containing files to stage
            
        Raises:
            GitCommandError: If staging operations fail
            InvalidGitRepositoryError: If the repository is invalid
        """
        try:
            # Stage modified files
            if changes.modified:
                repo.index.add(changes.modified)
            
            # Stage added files
            if changes.added:
                repo.index.add(changes.added)
            
            # Stage deleted files
            if changes.deleted:
                repo.index.remove(changes.deleted)
            
            # Stage renamed files (add new path, remove old path)
            if changes.renamed:
                for old_path, new_path in changes.renamed:
                    repo.index.remove([old_path], working_tree=True)
                    repo.index.add([new_path])
                    
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"Invalid Git repository: {e}"
            ) from e
        except GitCommandError as e:
            raise GitCommandError(
                command=e.command,
                status=e.status,
                stderr=f"Failed to stage changes: {e.stderr}"
            ) from e
    
    def create_commit(self, repo: Repo, message: str) -> str:
        """Create a commit with the given message.
        
        Args:
            repo: GitPython Repo object representing the repository
            message: Commit message to use
            
        Returns:
            The SHA hash of the created commit
            
        Raises:
            GitCommandError: If commit creation fails
            InvalidGitRepositoryError: If the repository is invalid
        """
        try:
            commit = repo.index.commit(message)
            return commit.hexsha
            
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"Invalid Git repository: {e}"
            ) from e
        except GitCommandError as e:
            raise GitCommandError(
                command=e.command,
                status=e.status,
                stderr=f"Failed to create commit: {e.stderr}"
            ) from e
    
    def get_current_branch(self, repo: Repo) -> str:
        """Retrieve the name of the current active branch.
        
        Args:
            repo: GitPython Repo object representing the repository
            
        Returns:
            Name of the current branch
            
        Raises:
            InvalidGitRepositoryError: If the repository is invalid
            TypeError: If HEAD is detached (no active branch)
        """
        try:
            if repo.head.is_detached:
                raise TypeError("HEAD is detached - not on any branch")
            
            return repo.active_branch.name
            
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"Invalid Git repository: {e}"
            ) from e
    
    def push_to_remote(self, repo: Repo) -> dict:
        """Push the current branch to its remote.
        
        Pushes the current branch to the configured remote repository.
        
        Args:
            repo: GitPython Repo object representing the repository
            
        Returns:
            Dictionary containing push result information:
                - success: Whether push succeeded
                - branch: Name of the branch that was pushed
                - remote: Name of the remote
                - message: Status message
                
        Raises:
            GitCommandError: If push operation fails
            InvalidGitRepositoryError: If the repository is invalid
            ValueError: If no remote is configured
        """
        try:
            # Get current branch
            branch_name = self.get_current_branch(repo)
            
            # Check if remote exists
            if not repo.remotes:
                raise ValueError("No remote repository configured")
            
            # Get the default remote (usually 'origin')
            remote: Remote = repo.remotes[0]
            remote_name = remote.name
            
            # Push to remote
            push_info = remote.push(branch_name)
            
            # Check if push was successful
            if push_info and len(push_info) > 0:
                info = push_info[0]
                
                # Check for errors in push result
                if info.flags & info.ERROR:
                    raise GitCommandError(
                        command=['git', 'push'],
                        status=1,
                        stderr=f"Push failed: {info.summary}"
                    )
                
                return {
                    "success": True,
                    "branch": branch_name,
                    "remote": remote_name,
                    "message": f"Successfully pushed to {remote_name}/{branch_name}"
                }
            else:
                raise GitCommandError(
                    command=['git', 'push'],
                    status=1,
                    stderr="Push operation returned no information"
                )
                
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"Invalid Git repository: {e}"
            ) from e
        except ValueError as e:
            raise ValueError(str(e)) from e
        except GitCommandError as e:
            # Re-raise with more context
            raise GitCommandError(
                command=e.command if hasattr(e, 'command') else ['git', 'push'],
                status=e.status if hasattr(e, 'status') else 1,
                stderr=f"Failed to push to remote: {e.stderr if hasattr(e, 'stderr') else str(e)}"
            ) from e
