#!/usr/bin/env python3
"""Commit and push changes."""

import sys
sys.path.insert(0, 'src')

from git_commit_mcp.server import execute_git_commit_and_push

# Commit and push
result = execute_git_commit_and_push(
    repository_path=".",
    confirm_push=True  # Push to remote
)

print("=" * 60)
print("COMMIT RESULT:")
print("=" * 60)
print(f"Success: {result['success']}")
print(f"Commit Hash: {result['commit_hash']}")
print(f"Files Changed: {result['files_changed']}")
print(f"Pushed: {result['pushed']}")
print(f"\nCommit Message:\n{result['commit_message']}")
if result['error']:
    print(f"\nError: {result['error']}")
print("=" * 60)
