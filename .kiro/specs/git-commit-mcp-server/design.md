# Design Document: Git Commit MCP Server

## Overview

The Git Commit MCP Server is a Model Context Protocol server that provides automated Git commit workflow tools. It exposes MCP tools that can be invoked by AI assistants to track changes, generate conventional commit messages, create commits, manage push operations with user approval, and maintain a changelog.

The server runs locally and communicates via stdio transport, making it lightweight and easy to integrate with AI assistants that support MCP.

The server is implemented using Python, leveraging the FastMCP framework for rapid development and GitPython for Git operations.

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│   AI Assistant  │
│   (MCP Client)  │
└────────┬────────┘
         │ stdio
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
│  │  - Repository Manager            │   │
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
- **Packaging**: uv/uvx for distribution via PyPI

## Components and Interfaces

### 1. MCP Tool Interface

**Tool: `git_commit_and_push`**

This is the primary tool exposed by the MCP server.

**Input Parameters:**
- `repository_path` (optional, string): Path to the Git repository or remote URL. Defaults to current working directory.
- `confirm_push` (optional, boolean): Whether to push to remote after committing. Defaults to false.

**Output:**
```json
{
  "success": boolean,
  "commit_hash": string,
  "commit_message": string,
  "files_changed": number,
  "pushed": boolean,
  "changelog_updated": boolean,
  "message": string,
  "error": string | null
}
```

**Workflow:**
1. Track changes since last commit
2. Generate conventional commit message
3. Stage and commit changes
4. Execute push if confirmed
5. Update CHANGELOG.md

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
- Use `repo.untracked_files` to identify new files
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
Use a single tool with a `confirm_push` parameter that the AI assistant must explicitly set to `true` after asking the user.

### 7. Repository Manager

**Responsibility:** Manage Git repository access, including local and remote repositories.

**Interface:**
```python
class RepositoryManager:
    def __init__(self, workspace_dir: str = "/tmp/git-workspaces"):
        """Initialize with workspace directory for cloned repos."""
        pass
    
    def get_or_clone_repository(
        self, 
        repo_url: str, 
        credentials: Optional[GitCredentials] = None
    ) -> Repo:
        """Clone repository if not exists, or pull latest changes."""
        pass
    
    def get_local_repository(self, repo_path: str) -> Repo:
        """Access existing local repository."""
        pass
    
    def cleanup_workspace(self, repo_id: str) -> None:
        """Remove cloned repository from workspace."""
        pass
```

**GitCredentials Data Structure:**
```python
@dataclass
class GitCredentials:
    auth_type: Literal["ssh", "https", "token"]
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    token: Optional[str] = None
```

**Implementation Details:**
- Clone remote repositories to workspace directory
- Support SSH key-based authentication via environment variables
- Support HTTPS with username/password or personal access tokens
- Implement workspace cleanup after operations complete
- Cache cloned repositories for performance

## Data Models

### Configuration

```python
@dataclass
class ServerConfig:
    # Core settings
    default_repo_path: str = "."
    max_bullet_points: int = 5
    max_summary_lines: int = 2
    changelog_file: str = "CHANGELOG.md"
    
    # Repository settings
    workspace_dir: str = "/tmp/git-workspaces"
    ssh_key_path: Optional[str] = None
    git_username: Optional[str] = None
    git_token: Optional[str] = None
    
    # Logging settings
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        return cls(
            default_repo_path=os.getenv("DEFAULT_REPO_PATH", "."),
            max_bullet_points=int(os.getenv("MAX_BULLET_POINTS", "5")),
            max_summary_lines=int(os.getenv("MAX_SUMMARY_LINES", "2")),
            changelog_file=os.getenv("CHANGELOG_FILE", "CHANGELOG.md"),
            workspace_dir=os.getenv("WORKSPACE_DIR", "/tmp/git-workspaces"),
            ssh_key_path=os.getenv("GIT_SSH_KEY_PATH"),
            git_username=os.getenv("GIT_USERNAME"),
            git_token=os.getenv("GIT_TOKEN"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
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

8. **Repository Clone Fails**
   - Detection: GitCommandError during clone operation
   - Response: Return error with repository URL and authentication hint

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

## Implementation Notes

### Dependencies

```toml
[project]
dependencies = [
    "fastmcp>=0.1.0",
    "gitpython>=3.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
]
```

### Project Structure

```
git-commit-mcp-server/
├── src/
│   └── git_commit_mcp/
│       ├── __init__.py
│       ├── __main__.py            # Entry point
│       ├── server.py              # Main MCP server
│       ├── change_tracker.py
│       ├── message_generator.py
│       ├── git_operations.py
│       ├── changelog_manager.py
│       ├── repository_manager.py
│       ├── models.py
│       ├── config.py
│       └── logging_config.py
├── tests/
│   ├── test_change_tracker.py
│   ├── test_message_generator.py
│   ├── test_git_operations.py
│   ├── test_changelog_manager.py
│   └── test_repository_manager.py
├── pyproject.toml
├── LICENSE
├── MANIFEST.in
└── README.md
```

### Server Setup

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

def run_stdio_server():
    """Run the MCP server in stdio mode."""
    mcp.run(transport="stdio")
```

## Security Considerations

1. **Path Traversal**: Validate `repository_path` to prevent access outside intended directories
2. **Command Injection**: Use GitPython's API exclusively, avoid shell commands
3. **Credential Exposure**: Never log or return Git credentials
4. **File Permissions**: Respect file system permissions when writing CHANGELOG.md
5. **Input Validation**: Sanitize all inputs (repository URLs, paths)
6. **Secret Management**: Store sensitive credentials (SSH keys, tokens) in environment variables
7. **Workspace Isolation**: Ensure cloned repositories are isolated

## PyPI Publication

### Package Metadata

- **Name**: git-commit-mcp-server
- **Version**: 0.1.0
- **License**: MIT
- **Author**: Suraj Fale
- **Keywords**: mcp, git, commit, automation, conventional-commits, changelog
- **Entry Point**: `git-commit-mcp` command

### Installation

Users can install via:
```bash
# Using uvx (recommended)
uvx git-commit-mcp-server

# Or install globally
pip install git-commit-mcp-server
```

### MCP Configuration

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uvx",
      "args": ["git-commit-mcp-server"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```
