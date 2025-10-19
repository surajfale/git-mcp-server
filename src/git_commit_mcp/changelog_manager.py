"""Changelog management for Git Commit MCP Server."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class ChangelogManager:
    """Manages CHANGELOG.md file with commit history.
    
    This class handles creating and updating the CHANGELOG.md file with
    formatted commit entries in reverse chronological order.
    """
    
    CHANGELOG_TEMPLATE = """# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

"""
    
    def __init__(self, changelog_file: str = "CHANGELOG.md"):
        """Initialize the ChangelogManager.
        
        Args:
            changelog_file: Name of the changelog file (default: CHANGELOG.md)
        """
        self.changelog_file = changelog_file
    
    def create_changelog_if_missing(self, repo_path: str) -> None:
        """Create CHANGELOG.md with template headers if it doesn't exist.
        
        Args:
            repo_path: Path to the Git repository
            
        Raises:
            IOError: If file creation fails due to permissions or disk issues
        """
        changelog_path = Path(repo_path) / self.changelog_file
        
        if not changelog_path.exists():
            try:
                changelog_path.write_text(self.CHANGELOG_TEMPLATE, encoding='utf-8')
            except (IOError, OSError) as e:
                raise IOError(f"Failed to create changelog file: {e}")
    
    def update_changelog(
        self,
        commit_hash: str,
        commit_message: str,
        pushed: bool,
        repo_path: str
    ) -> None:
        """Append new entry to CHANGELOG.md after the [Unreleased] section.
        
        Entries are inserted in reverse chronological order (newest first) with
        timestamp, short commit hash, push status, and full commit message.
        
        Args:
            commit_hash: Full commit hash
            commit_message: Complete commit message
            pushed: Whether the commit was pushed to remote
            repo_path: Path to the Git repository
            
        Raises:
            IOError: If file operations fail
        """
        changelog_path = Path(repo_path) / self.changelog_file
        
        # Ensure changelog exists
        self.create_changelog_if_missing(repo_path)
        
        try:
            # Read existing content
            content = changelog_path.read_text(encoding='utf-8')
            
            # Generate new entry
            entry = self._format_entry(commit_hash, commit_message, pushed)
            
            # Find the [Unreleased] section and insert after it
            unreleased_marker = "## [Unreleased]"
            
            if unreleased_marker in content:
                # Split at the marker
                parts = content.split(unreleased_marker, 1)
                
                # Reconstruct with new entry after [Unreleased]
                new_content = (
                    parts[0] + 
                    unreleased_marker + 
                    "\n\n" + 
                    entry + 
                    parts[1].lstrip('\n')
                )
            else:
                # If [Unreleased] section doesn't exist, append to end
                new_content = content.rstrip('\n') + "\n\n" + entry + "\n"
            
            # Write updated content
            changelog_path.write_text(new_content, encoding='utf-8')
            
        except (IOError, OSError) as e:
            raise IOError(f"Failed to update changelog: {e}")
    
    def _format_entry(
        self,
        commit_hash: str,
        commit_message: str,
        pushed: bool
    ) -> str:
        """Format a changelog entry with timestamp, hash, and message.
        
        Args:
            commit_hash: Full commit hash
            commit_message: Complete commit message
            pushed: Whether the commit was pushed to remote
            
        Returns:
            Formatted changelog entry string
        """
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get short hash (first 7 characters)
        short_hash = commit_hash[:7]
        
        # Determine push status indicator
        status = "[PUSHED]" if pushed else "[LOCAL]"
        
        # Format the entry
        entry = f"### {timestamp} - {short_hash} {status}\n\n{commit_message}"
        
        return entry
