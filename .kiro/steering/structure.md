# Project Structure

## Directory Organization

```
git-commit-mcp-server/
├── .kiro/                      # Kiro IDE configuration
│   ├── settings/               # MCP and other settings
│   ├── specs/                  # Feature specifications
│   └── steering/               # AI assistant guidance rules
├── src/
│   └── git_commit_mcp/         # Main package
│       ├── __init__.py
│       ├── server.py           # MCP server entry point
│       ├── models.py           # Data models and types
│       ├── change_tracker.py   # Git change detection logic
│       ├── message_generator.py # Commit message generation
│       ├── git_operations.py   # Git command wrappers
│       └── changelog_manager.py # CHANGELOG.md management
├── tests/                      # Test suite
├── pyproject.toml              # Project metadata and dependencies
└── README.md                   # User documentation
```

## Module Responsibilities

- **server.py**: Main MCP server implementation, exposes the `git_commit_and_push` tool
- **models.py**: Pydantic models and data structures for commits, changes, and configuration
- **change_tracker.py**: Detects and categorizes file changes (modified, added, deleted, renamed)
- **message_generator.py**: Generates conventional commit messages with type, scope, and description
- **git_operations.py**: Wraps GitPython operations (commit, push, status)
- **changelog_manager.py**: Maintains CHANGELOG.md with formatted commit entries

## Code Organization Principles

- Single responsibility: Each module handles one aspect of the Git workflow
- Source code lives in `src/git_commit_mcp/` following modern Python packaging standards
- Entry point defined in `pyproject.toml` as `git-commit-mcp`
- All imports use absolute paths from the `git_commit_mcp` package
