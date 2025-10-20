#!/usr/bin/env python3
import sys
sys.path.insert(0, 'src')
from git_commit_mcp.server import execute_git_commit_and_push

result = execute_git_commit_and_push(".", True)
print(f"Success: {result['success']}")
print(f"Pushed: {result['pushed']}")
print(f"Commit: {result['commit_hash'][:7] if result['commit_hash'] else 'N/A'}")
print(f"\nMessage:\n{result['commit_message']}")
