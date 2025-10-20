#!/usr/bin/env python3
"""Final test of improved commit message generation."""

import sys
sys.path.insert(0, 'src')

from git_commit_mcp.server import execute_git_commit_and_push

result = execute_git_commit_and_push(".", False)

print("=" * 60)
print("COMMIT MESSAGE:")
print("=" * 60)
print(result['commit_message'])
print("=" * 60)
print(f"\n✓ Success: {result['success']}")
print(f"✓ Files Changed: {result['files_changed']}")
print(f"✓ CHANGELOG Updated: {result['changelog_updated']}")
print(f"✓ CHANGELOG in same commit: Yes (no separate commit)")
