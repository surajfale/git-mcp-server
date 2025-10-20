#!/usr/bin/env python3
"""Test script for message generation."""

import sys
sys.path.insert(0, 'src')

from git_commit_mcp.server import execute_git_commit_and_push

# Test the commit functionality
result = execute_git_commit_and_push(
    repository_path=".",
    confirm_push=False
)

print("Commit Message:")
print(result['commit_message'])
print(f"\nSuccess: {result['success']}")
print(f"Files Changed: {result['files_changed']}")
