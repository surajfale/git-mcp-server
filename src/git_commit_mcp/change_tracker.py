"""Change tracking component for detecting Git repository changes."""

from typing import List, Tuple
from git import Repo, DiffIndex, Diff
from git.exc import GitCommandError

from git_commit_mcp.models import ChangeSet


class ChangeTracker:
    """Tracks changes in a Git repository since the last commit.
    
    This component identifies modified, added, deleted, and renamed files
    by analyzing the Git repository state using GitPython.
    """
    
    def get_changes(self, repo: Repo) -> ChangeSet:
        """Detect all changes in the working directory since the last commit.
        
        Analyzes the repository to identify:
        - Modified files (tracked files with changes)
        - Added files (untracked files)
        - Deleted files (tracked files that were removed)
        - Renamed files (files that were moved or renamed)
        
        Args:
            repo: GitPython Repo object representing the repository
            
        Returns:
            ChangeSet object containing categorized file changes
            
        Raises:
            GitCommandError: If Git operations fail
        """
        modified: List[str] = []
        added: List[str] = []
        deleted: List[str] = []
        renamed: List[Tuple[str, str]] = []
        
        # Get unstaged changes (working directory vs index)
        unstaged_diff: DiffIndex = repo.index.diff(None)
        
        # Get staged changes (index vs HEAD)
        try:
            staged_diff: DiffIndex = repo.index.diff('HEAD')
        except GitCommandError:
            # No HEAD exists (empty repository), so no staged changes
            staged_diff = []
        
        # Process all diffs (both staged and unstaged)
        all_diffs = list(unstaged_diff) + list(staged_diff)
        
        # Track processed paths to avoid duplicates
        processed_paths = set()
        
        for diff_item in all_diffs:
            # Handle renamed files
            if diff_item.renamed_file:
                old_path = diff_item.rename_from
                new_path = diff_item.rename_to
                rename_tuple = (old_path, new_path)
                if rename_tuple not in renamed:
                    renamed.append(rename_tuple)
                processed_paths.add(old_path)
                processed_paths.add(new_path)
            
            # Handle deleted files
            elif diff_item.deleted_file:
                file_path = diff_item.a_path
                if file_path not in processed_paths and file_path not in deleted:
                    deleted.append(file_path)
                    processed_paths.add(file_path)
            
            # Handle new files (added to index)
            elif diff_item.new_file:
                file_path = diff_item.b_path
                if file_path not in processed_paths and file_path not in added:
                    added.append(file_path)
                    processed_paths.add(file_path)
            
            # Handle modified files
            elif diff_item.a_path and diff_item.b_path:
                file_path = diff_item.a_path
                if file_path not in processed_paths and file_path not in modified:
                    modified.append(file_path)
                    processed_paths.add(file_path)
        
        # Get untracked files (not in index at all)
        untracked_files = repo.untracked_files
        for file_path in untracked_files:
            if file_path not in processed_paths and file_path not in added:
                added.append(file_path)
        
        return ChangeSet(
            modified=modified,
            added=added,
            deleted=deleted,
            renamed=renamed
        )

