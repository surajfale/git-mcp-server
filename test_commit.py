#!/usr/bin/env python3
"""Test script for the git commit functionality."""

import sys
sys.path.insert(0, 'src')

from git_commit_mcp.server import execute_git_commit_and_push

# Test the commit functionality
result = execute_git_commit_and_push(
    repository_path=".",
    confirm_push=False
)

print("Result:")
print(f"  Success: {result['success']}")
print(f"  Commit Hash: {result['commit_hash']}")
print(f"  Files Changed: {result['files_changed']}")
print(f"  Pushed: {result['pushed']}")
print(f"  Changelog Updated: {result['changelog_updated']}")
print(f"  Message: {result['message']}")
if result['commit_message']:
    print(f"\nCommit Message:\n{result['commit_message']}")
if result['error']:
    print(f"\nError: {result['error']}")
