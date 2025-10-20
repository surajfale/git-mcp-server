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
            commit_hash: Full commit hash or placeholder (e.g., "pending")
            commit_message: Complete commit message (can be empty for placeholder)
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
    
    def replace_commit_hash(
        self,
        old_hash: str,
        new_hash: str,
        repo_path: str,
        pushed: bool = False
    ) -> None:
        """Replace a placeholder commit hash with the actual hash in the changelog.
        
        This is used when the changelog is updated before the commit is created,
        allowing us to replace the temporary hash with the real one.
        
        Args:
            old_hash: Placeholder hash to replace (e.g., "pending")
            new_hash: Actual commit hash
            repo_path: Path to the Git repository
            pushed: Whether the commit was pushed (updates the status indicator)
            
        Raises:
            IOError: If file operations fail
        """
        changelog_path = Path(repo_path) / self.changelog_file
        
        if not changelog_path.exists():
            return
        
        try:
            content = changelog_path.read_text(encoding='utf-8')
            
            # Replace the old hash with new hash (short version)
            short_new_hash = new_hash[:7]
            updated_content = content.replace(old_hash, short_new_hash)
            
            # Update push status if needed
            if pushed:
                updated_content = updated_content.replace(
                    f"{short_new_hash} [LOCAL]",
                    f"{short_new_hash} [PUSHED]"
                )
            
            changelog_path.write_text(updated_content, encoding='utf-8')
            
        except (IOError, OSError) as e:
            raise IOError(f"Failed to replace commit hash in changelog: {e}")
    
    def update_commit_message_in_changelog(
        self,
        commit_hash: str,
        commit_message: str,
        repo_path: str
    ) -> None:
        """Update the commit message for a specific commit in the changelog.
        
        This is used when the commit message is generated after the changelog entry
        is created with a placeholder.
        
        Args:
            commit_hash: Commit hash to find (short or full)
            commit_message: The commit message to insert
            repo_path: Path to the Git repository
            
        Raises:
            IOError: If file operations fail
        """
        changelog_path = Path(repo_path) / self.changelog_file
        
        if not changelog_path.exists():
            return
        
        try:
            content = changelog_path.read_text(encoding='utf-8')
            short_hash = commit_hash[:7]
            
            # Find the entry with this hash and add the commit message after it
            # Look for pattern: ### YYYY-MM-DD HH:MM:SS - HASH [STATUS]\n\n
            import re
            pattern = rf"(### \d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}} - {short_hash} \[(?:LOCAL|PUSHED)\])\n\n"
            replacement = rf"\1\n\n{commit_message}"
            
            updated_content = re.sub(pattern, replacement, content)
            
            changelog_path.write_text(updated_content, encoding='utf-8')
            
        except (IOError, OSError) as e:
            raise IOError(f"Failed to update commit message in changelog: {e}")
    
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
