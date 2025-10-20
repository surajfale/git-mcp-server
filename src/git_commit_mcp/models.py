"""Data models for Git Commit MCP Server."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class ChangeSet:
    """Represents a set of changes in a Git repository.
    
    Attributes:
        modified: List of modified file paths
        added: List of newly added file paths
        deleted: List of deleted file paths
        renamed: List of tuples containing (old_path, new_path) for renamed files
    """
    modified: List[str] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    renamed: List[Tuple[str, str]] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        """Check if there are no changes in this changeset.
        
        Returns:
            True if no files were modified, added, deleted, or renamed
        """
        return not (self.modified or self.added or self.deleted or self.renamed)
    
    def total_files(self) -> int:
        """Calculate the total number of files affected by changes.
        
        Returns:
            Total count of all changed files
        """
        return len(self.modified) + len(self.added) + len(self.deleted) + len(self.renamed)
    
    def exclude_file(self, filename: str) -> 'ChangeSet':
        """Create a new ChangeSet excluding a specific file.
        
        Args:
            filename: Name of the file to exclude (e.g., "CHANGELOG.md")
            
        Returns:
            New ChangeSet with the specified file removed from all lists
        """
        return ChangeSet(
            modified=[f for f in self.modified if f != filename],
            added=[f for f in self.added if f != filename],
            deleted=[f for f in self.deleted if f != filename],
            renamed=[(old, new) for old, new in self.renamed if old != filename and new != filename]
        )


@dataclass
class CommitResult:
    """Result of a git commit and push operation.
    
    Attributes:
        success: Whether the operation completed successfully
        commit_hash: The SHA hash of the created commit (if successful)
        commit_message: The full commit message used
        files_changed: Number of files affected by the commit
        pushed: Whether the commit was pushed to remote
        changelog_updated: Whether CHANGELOG.md was updated
        message: Human-readable status message
        error: Error message if the operation failed
    """
    success: bool
    commit_hash: Optional[str]
    commit_message: Optional[str]
    files_changed: int
    pushed: bool
    changelog_updated: bool
    message: str
    error: Optional[str] = None


@dataclass
class ServerConfig:
    """Configuration settings for the MCP server.
    
    Attributes:
        default_repo_path: Default path to Git repository
        max_bullet_points: Maximum number of bullet points in commit messages
        max_summary_lines: Maximum number of lines in commit summary
        changelog_file: Name of the changelog file to maintain
    """
    default_repo_path: str = "."
    max_bullet_points: int = 5
    max_summary_lines: int = 2
    changelog_file: str = "CHANGELOG.md"
