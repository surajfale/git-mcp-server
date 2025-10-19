# Design Document: Git Commit MCP Server

## Overview

The Git Commit MCP Server is a Model Context Protocol server that provides automated Git commit workflow tools. It exposes MCP tools that can be invoked by AI assistants to track changes, generate conventional commit messages, create commits, manage push operations with user approval, and maintain a changelog.

The server will be implemented as a standalone MCP server using Python, leveraging the FastMCP framework for rapid development and the GitPython library for Git operations.

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   AI Assistant  │
│   (MCP Client)  │
└────────┬────────┘
         │ MCP Protocol
         │
┌────────▼────────────────────────────────┐
│     Git Commit MCP Server               │
│  ┌──────────────────────────────────┐   │
│  │  MCP Tool Interface              │   │
│  │  - git_commit_and_push           │   │
│  └──────────┬───────────────────────┘   │
│             │                            │
│  ┌──────────▼───────────────────────┐   │
│  │  Core Components                 │   │
│  │  - Change Tracker                │   │
│  │  - Commit Message Generator      │   │
│  │  - Git Operations Manager        │   │
│  │  - Changelog Manager             │   │
│  └──────────┬───────────────────────┘   │
└─────────────┼──────────────────────────┘
              │
     ┌────────▼────────┐
     │  Git Repository │
     │  - .git/        │
     │  - CHANGELOG.md │
     └─────────────────┘
```

### Technology Stack

- **Language**: Python 3.10+
- **MCP Framework**: FastMCP (for rapid MCP server development)
- **Git Library**: GitPython (for Git operations)
- **Packaging**: uv/uvx for distribution

## Components and Interfaces

### 1. MCP Tool Interface

**Tool: `git_commit_and_push`**

This is the primary tool exposed by the MCP server.

**Input Parameters:**
- `repository_path` (optional, string): Path to the Git repository. Defaults to current working directory.

**Output:**
```json
{
  "success": boolean,
  "commit_hash": string,
  "commit_message": string,
  "files_changed": number,
  "pushed": boolean,
  "changelog_updated": boolean,
  "message": string
}
```

**Workflow:**
1. Track changes since last commit
2. Generate conventional commit message
3. Stage and commit changes
4. Request user confirmation for push
5. Execute push if approved
6. Update CHANGELOG.md

### 2. Change Tracker Component

**Responsibility:** Identify all changes in the working directory since the last commit.

**Interface:**
```python
class ChangeTracker:
    def get_changes(self, repo: Repo) -> ChangeSet:
        """
        Returns a ChangeSet containing modified, added, and deleted files.
        """
        pass
```

**ChangeSet Data Structure:**
```python
@dataclass
class ChangeSet:
    modified: List[str]
    added: List[str]
    deleted: List[str]
    renamed: List[Tuple[str, str]]
    
    def is_empty(self) -> bool:
        return not (self.modified or self.added or self.deleted or self.renamed)
    
    def total_files(self) -> int:
        return len(self.modified) + len(self.added) + len(self.deleted) + len(self.renamed)
```

**Implementation Details:**
- Use `repo.index.diff(None)` to get unstaged changes
- Use `repo.untracked_files` to identify new files (but exclude from auto-commit)
- Parse diff output to categorize changes

### 3. Commit Message Generator Component

**Responsibility:** Generate conventional commit messages based on detected changes.

**Interface:**
```python
class CommitMessageGenerator:
    def generate_message(self, changes: ChangeSet, repo: Repo) -> str:
        """
        Generates a conventional commit message with max 2 line summary
        and max 5 bullet points.
        """
        pass
```

**Message Format:**
```
<type>(<scope>): <short description>
<optional second line for additional context>

- <bullet point 1>
- <bullet point 2>
- <bullet point 3>
- <bullet point 4>
- <bullet point 5>
```

**Commit Type Detection Logic:**
- Analyze file paths and extensions
- Prioritize types: feat > fix > docs > style > refactor > test > chore
- Use heuristics:
  - New files in `src/` or `lib/` → `feat`
  - Changes in test files → `test`
  - Changes in `README.md`, `docs/` → `docs`
  - Changes in config files → `chore`
  - Bug-related keywords in diffs → `fix`

**Scope Detection:**
- Extract from directory structure (e.g., `src/auth/` → scope: `auth`)
- Use root-level directory names
- Default to empty scope if unclear

**Bullet Point Generation:**
- Limit to 5 most significant changes
- Format: "Action verb + file/component + brief description"
- Examples:
  - "Add user authentication module"
  - "Update API endpoint for user profile"
  - "Remove deprecated utility functions"
  - "Fix validation error in login form"
  - "Refactor database connection logic"

### 4. Git Operations Manager Component

**Responsibility:** Execute Git commands (stage, commit, push).

**Interface:**
```python
class GitOperationsManager:
    def stage_changes(self, repo: Repo, changes: ChangeSet) -> None:
        """Stage all tracked changes."""
        pass
    
    def create_commit(self, repo: Repo, message: str) -> str:
        """Create commit and return commit hash."""
        pass
    
    def push_to_remote(self, repo: Repo) -> PushResult:
        """Push to current branch's remote."""
        pass
    
    def get_current_branch(self, repo: Repo) -> str:
        """Get the name of the current branch."""
        pass
```

**Implementation Details:**
- Use `repo.index.add()` for staging
- Use `repo.index.commit()` for committing
- Use `repo.remote().push()` for pushing
- Handle authentication errors gracefully
- Detect if remote is configured

### 5. Changelog Manager Component

**Responsibility:** Maintain CHANGELOG.md file with commit history.

**Interface:**
```python
class ChangelogManager:
    def update_changelog(
        self, 
        commit_hash: str, 
        commit_message: str, 
        pushed: bool,
        repo_path: str
    ) -> None:
        """Append entry to CHANGELOG.md."""
        pass
    
    def create_changelog_if_missing(self, repo_path: str) -> None:
        """Create CHANGELOG.md with headers if it doesn't exist."""
        pass
```

**CHANGELOG.md Format:**
```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### 2025-10-19 14:30:45 - abc1234 [PUSHED]

feat(auth): Add user authentication module

- Add user authentication module
- Update API endpoint for user profile
- Fix validation error in login form

### 2025-10-19 13:15:22 - def5678 [LOCAL]

docs: Update README with installation instructions

- Update README with installation instructions
- Add code examples for API usage
```

**Implementation Details:**
- Insert new entries after the `## [Unreleased]` section
- Include timestamp, commit hash (short), and push status
- Preserve existing changelog content
- Create file with template if missing

### 6. User Confirmation Handler

**Responsibility:** Request user approval before pushing.

**Implementation:**
Since MCP servers run as background processes, user confirmation will be handled through the MCP protocol's resource or prompt capabilities. The server will return a response indicating that push confirmation is needed, and the AI assistant will ask the user.

**Alternative Approach:**
Expose two separate tools:
- `git_commit` - commits without pushing
- `git_push` - pushes the last commit

This gives the AI assistant control over when to push, allowing it to ask the user naturally.

**Recommended Design:**
Use a single tool with a `confirm_push` parameter that the AI assistant must explicitly set to `true` after asking the user.

## Data Models

### Configuration

```python
@dataclass
class ServerConfig:
    default_repo_path: str = "."
    max_bullet_points: int = 5
    max_summary_lines: int = 2
    changelog_file: str = "CHANGELOG.md"
```

### Response Models

```python
@dataclass
class CommitResult:
    success: bool
    commit_hash: Optional[str]
    commit_message: Optional[str]
    files_changed: int
    pushed: bool
    changelog_updated: bool
    message: str
    error: Optional[str] = None
```

## Error Handling

### Error Scenarios

1. **No Git Repository Found**
   - Detection: GitPython raises `InvalidGitRepositoryError`
   - Response: Return error message "Not a git repository"

2. **No Changes to Commit**
   - Detection: ChangeSet is empty
   - Response: Return success=false with message "No changes to commit"

3. **Commit Fails**
   - Detection: Exception during `repo.index.commit()`
   - Response: Return error with details from exception

4. **Push Fails (No Remote)**
   - Detection: No remote configured
   - Response: Return success=true for commit, pushed=false, message indicating no remote

5. **Push Fails (Authentication)**
   - Detection: GitCommandError with authentication failure
   - Response: Return error message with authentication guidance

6. **Push Fails (Network)**
   - Detection: GitCommandError with network-related error
   - Response: Return error message suggesting retry

7. **Changelog Update Fails**
   - Detection: IOError or PermissionError
   - Response: Log warning, continue (non-critical failure)

### Error Response Format

```python
{
    "success": false,
    "error": "Error message",
    "message": "User-friendly description"
}
```

## Testing Strategy

### Unit Tests

1. **ChangeTracker Tests**
   - Test with modified files only
   - Test with added files only
   - Test with deleted files only
   - Test with mixed changes
   - Test with no changes

2. **CommitMessageGenerator Tests**
   - Test commit type detection for different file patterns
   - Test scope extraction from paths
   - Test bullet point generation and limiting
   - Test summary line limiting

3. **GitOperationsManager Tests**
   - Test staging changes
   - Test commit creation
   - Test push operations (mocked)
   - Test error handling

4. **ChangelogManager Tests**
   - Test changelog creation
   - Test entry appending
   - Test format consistency
   - Test with missing file

### Integration Tests

1. **End-to-End Workflow Test**
   - Create test repository
   - Make changes
   - Invoke tool
   - Verify commit created
   - Verify changelog updated

2. **MCP Protocol Test**
   - Test tool discovery
   - Test tool invocation
   - Test response format

### Manual Testing

1. Test with real repository
2. Test push confirmation flow
3. Test with various change patterns
4. Verify changelog readability

## Implementation Notes

### Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=0.1.0",
    "gitpython>=3.1.0",
]
```

### Project Structure

```
git-commit-mcp-server/
├── src/
│   └── git_commit_mcp/
│       ├── __init__.py
│       ├── server.py           # Main MCP server
│       ├── change_tracker.py
│       ├── message_generator.py
│       ├── git_operations.py
│       ├── changelog_manager.py
│       └── models.py
├── tests/
│   ├── test_change_tracker.py
│   ├── test_message_generator.py
│   ├── test_git_operations.py
│   └── test_changelog_manager.py
├── pyproject.toml
└── README.md
```

### FastMCP Server Setup

```python
from fastmcp import FastMCP

mcp = FastMCP("git-commit-server")

@mcp.tool()
def git_commit_and_push(
    repository_path: str = ".",
    confirm_push: bool = False
) -> dict:
    """
    Track changes, generate commit message, commit, and optionally push.
    """
    # Implementation
    pass
```

## Security Considerations

1. **Path Traversal**: Validate `repository_path` to prevent access outside intended directories
2. **Command Injection**: Use GitPython's API exclusively, avoid shell commands
3. **Credential Exposure**: Never log or return Git credentials
4. **File Permissions**: Respect file system permissions when writing CHANGELOG.md

## Future Enhancements

1. Support for custom commit message templates
2. Integration with issue trackers (e.g., "Fixes #123")
3. Configurable changelog format
4. Support for semantic versioning in changelog
5. Pre-commit hooks integration
6. Support for multiple remotes
