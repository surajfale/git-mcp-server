# Design Document: Git Commit MCP Server

## Overview

The Git Commit MCP Server is a Model Context Protocol server that provides automated Git commit workflow tools. It exposes MCP tools that can be invoked by AI assistants to track changes, generate conventional commit messages, create commits, manage push operations with user approval, and maintain a changelog.

The server supports two deployment modes:
1. **Local Mode (stdio)**: Runs locally and communicates via standard input/output
2. **Remote Mode (HTTP/SSE)**: Runs as a web service accessible over the network with authentication

The server will be implemented using Python, leveraging the FastMCP framework for rapid development, GitPython for Git operations, and supporting multiple transport protocols for flexible deployment.

## Architecture

### High-Level Architecture

#### Local Mode (stdio)
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
│  └──────────┬───────────────────────┘   │
└─────────────┼──────────────────────────┘
              │
     ┌────────▼────────┐
     │  Git Repository │
     │  - .git/        │
     │  - CHANGELOG.md │
     └─────────────────┘
```

#### Remote Mode (HTTP/SSE)
```
┌─────────────────┐       ┌─────────────────┐
│   AI Assistant  │       │   AI Assistant  │
│   (MCP Client)  │       │   (MCP Client)  │
└────────┬────────┘       └────────┬────────┘
         │                         │
         │ HTTP/SSE + Auth Token   │
         │                         │
         └────────┬────────────────┘
                  │
         ┌────────▼────────┐
         │  Load Balancer  │ (Optional)
         │   / Reverse     │
         │     Proxy       │
         └────────┬────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐    ┌───▼───┐    ┌───▼───┐
│Server │    │Server │    │Server │
│   1   │    │   2   │    │   N   │
└───┬───┘    └───┬───┘    └───┬───┘
    │            │            │
┌───▼────────────▼────────────▼───┐
│  Git Commit MCP Server          │
│  ┌──────────────────────────┐   │
│  │  Transport Layer         │   │
│  │  - HTTP/SSE Handler      │   │
│  │  - Authentication        │   │
│  │  - CORS Handler          │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │  MCP Tool Interface      │   │
│  │  - git_commit_and_push   │   │
│  └──────────┬───────────────┘   │
│             │                    │
│  ┌──────────▼───────────────┐   │
│  │  Core Components         │   │
│  │  - Change Tracker        │   │
│  │  - Message Generator     │   │
│  │  - Git Operations Mgr    │   │
│  │  - Changelog Manager     │   │
│  │  - Repository Manager    │   │
│  └──────────┬───────────────┘   │
└─────────────┼──────────────────┘
              │
     ┌────────▼────────┐
     │  Git Repository │
     │  - Local Clone  │
     │  - SSH/HTTPS    │
     │  - CHANGELOG.md │
     └─────────────────┘
```

### Technology Stack

- **Language**: Python 3.10+
- **MCP Framework**: FastMCP (for rapid MCP server development)
- **Git Library**: GitPython (for Git operations)
- **Web Framework**: FastAPI (for HTTP/SSE transport in remote mode)
- **Authentication**: JWT tokens or API keys
- **Containerization**: Docker (for cloud deployment)
- **Packaging**: uv/uvx for distribution

### Deployment Options

#### 1. Cloud Run / ECS / Azure Container Instances
- **Best for**: Auto-scaling, managed infrastructure
- **Pros**: No server management, automatic scaling, pay-per-use
- **Cons**: Cold start latency, stateless (requires external storage)
- **Setup**: Docker container + environment variables

#### 2. AWS Lambda / Google Cloud Functions / Azure Functions
- **Best for**: Serverless, event-driven workloads
- **Pros**: Zero infrastructure management, extreme cost efficiency
- **Cons**: Execution time limits, cold starts, complex Git operations
- **Setup**: Function handler + layer for dependencies

#### 3. Traditional VPS (DigitalOcean, Linode, AWS EC2)
- **Best for**: Full control, persistent storage
- **Pros**: Persistent state, no cold starts, full control
- **Cons**: Manual scaling, server management required
- **Setup**: systemd service + nginx reverse proxy

#### 4. Kubernetes
- **Best for**: Large-scale deployments, multi-tenant
- **Pros**: Advanced orchestration, auto-scaling, high availability
- **Cons**: Complex setup, overkill for small deployments
- **Setup**: Deployment + Service + Ingress

## Components and Interfaces

### 0. Transport Layer (New for Remote Mode)

**Responsibility:** Handle HTTP/SSE communication, authentication, and CORS for remote deployments.

**Interface:**
```python
class TransportHandler:
    def __init__(self, auth_token: str, cors_origins: List[str]):
        """Initialize transport with authentication and CORS settings."""
        pass
    
    def authenticate_request(self, request: Request) -> bool:
        """Validate authentication token from request headers."""
        pass
    
    def handle_sse_connection(self, request: Request) -> EventSourceResponse:
        """Handle Server-Sent Events connection for streaming."""
        pass
    
    def health_check(self) -> dict:
        """Return health status for load balancer checks."""
        pass
```

**FastAPI Integration:**
```python
from fastapi import FastAPI, Header, HTTPException
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.post("/mcp/tools/git_commit_and_push")
async def git_commit_and_push_endpoint(
    repository_path: str = ".",
    confirm_push: bool = False,
    authorization: str = Header(None)
):
    # Validate token
    if not validate_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Execute tool
    result = await execute_git_commit_and_push(repository_path, confirm_push)
    return result

@app.get("/mcp/sse")
async def sse_endpoint(authorization: str = Header(None)):
    # Validate token and stream events
    if not validate_token(authorization):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return EventSourceResponse(event_generator())
```

**Authentication Mechanisms:**
1. **API Key**: Simple bearer token in Authorization header
2. **JWT**: Signed tokens with expiration
3. **OAuth 2.0**: For enterprise integrations (future)

**CORS Configuration:**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://trusted-client.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

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

### 7. Repository Manager (New for Remote Mode)

**Responsibility:** Manage Git repository access for remote deployments, including cloning, authentication, and cleanup.

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
    
    def configure_ssh_key(self, private_key: str) -> None:
        """Configure SSH key for Git operations."""
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
- For remote mode, clone repositories to `/tmp/git-workspaces/{repo_hash}/`
- Support SSH key-based authentication via environment variables or mounted secrets
- Support HTTPS with username/password or personal access tokens
- Implement workspace cleanup after operations complete
- Cache cloned repositories for performance (with TTL)
- Handle concurrent access with file locking

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
    
    # Transport settings
    transport_mode: Literal["stdio", "http"] = "stdio"
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    
    # Authentication settings
    auth_enabled: bool = True
    auth_token: Optional[str] = None  # Read from env: MCP_AUTH_TOKEN
    
    # CORS settings
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # TLS/HTTPS settings
    tls_enabled: bool = False
    tls_cert_path: Optional[str] = None
    tls_key_path: Optional[str] = None
    
    # Repository settings (for remote mode)
    workspace_dir: str = "/tmp/git-workspaces"
    ssh_key_path: Optional[str] = None  # Read from env: GIT_SSH_KEY_PATH
    git_username: Optional[str] = None
    git_token: Optional[str] = None
    
    # Monitoring settings
    enable_metrics: bool = True
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        return cls(
            transport_mode=os.getenv("TRANSPORT_MODE", "stdio"),
            http_host=os.getenv("HTTP_HOST", "0.0.0.0"),
            http_port=int(os.getenv("HTTP_PORT", "8000")),
            auth_token=os.getenv("MCP_AUTH_TOKEN"),
            cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
            tls_enabled=os.getenv("TLS_ENABLED", "false").lower() == "true",
            tls_cert_path=os.getenv("TLS_CERT_PATH"),
            tls_key_path=os.getenv("TLS_KEY_PATH"),
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

8. **Authentication Failure (Remote Mode)**
   - Detection: Missing or invalid auth token in request
   - Response: HTTP 401 Unauthorized with error message

9. **Repository Clone Fails (Remote Mode)**
   - Detection: GitCommandError during clone operation
   - Response: Return error with repository URL and authentication hint

10. **Workspace Full (Remote Mode)**
    - Detection: Disk space check before clone
    - Response: Return error suggesting cleanup or storage expansion

11. **Concurrent Access Conflict (Remote Mode)**
    - Detection: File lock acquisition failure
    - Response: Return error suggesting retry after delay

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
    "fastapi>=0.104.0",  # For HTTP/SSE transport
    "uvicorn>=0.24.0",   # ASGI server
    "sse-starlette>=1.6.0",  # Server-Sent Events
    "pyjwt>=2.8.0",      # JWT authentication
    "python-multipart>=0.0.6",  # Form data parsing
    "pydantic>=2.0.0",   # Data validation
    "python-dotenv>=1.0.0",  # Environment variable loading
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",  # For testing HTTP endpoints
    "pytest-cov>=4.1.0",
]
```

### Project Structure

```
git-commit-mcp-server/
├── src/
│   └── git_commit_mcp/
│       ├── __init__.py
│       ├── server.py              # Main MCP server (stdio mode)
│       ├── http_server.py         # HTTP/SSE server (remote mode)
│       ├── transport.py           # Transport layer abstraction
│       ├── auth.py                # Authentication handlers
│       ├── change_tracker.py
│       ├── message_generator.py
│       ├── git_operations.py
│       ├── changelog_manager.py
│       ├── repository_manager.py  # Repository access for remote mode
│       ├── models.py
│       └── config.py              # Configuration management
├── tests/
│   ├── test_change_tracker.py
│   ├── test_message_generator.py
│   ├── test_git_operations.py
│   ├── test_changelog_manager.py
│   ├── test_repository_manager.py
│   ├── test_http_server.py
│   └── test_auth.py
├── deployment/
│   ├── Dockerfile                 # Container image
│   ├── docker-compose.yml         # Local testing
│   ├── kubernetes/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   ├── cloud-run/
│   │   └── service.yaml
│   └── systemd/
│       └── git-commit-mcp.service
├── .env.example                   # Environment variable template
├── pyproject.toml
└── README.md
```

### Server Setup

#### Local Mode (stdio)
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

if __name__ == "__main__":
    mcp.run()  # Uses stdio transport
```

#### Remote Mode (HTTP/SSE)
```python
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import uvicorn

app = FastAPI(title="Git Commit MCP Server")

# Load configuration
config = ServerConfig.from_env()

# Add CORS middleware
if config.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Authentication dependency
async def verify_token(authorization: str = Header(None)):
    if config.auth_enabled:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")
        token = authorization.replace("Bearer ", "")
        if token != config.auth_token:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    return True

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "transport": "http",
        "auth_enabled": config.auth_enabled
    }

@app.post("/mcp/tools/git_commit_and_push")
async def git_commit_and_push_endpoint(
    repository_path: str = ".",
    confirm_push: bool = False,
    authenticated: bool = Depends(verify_token)
):
    """Execute git commit and push operation."""
    try:
        result = await execute_git_commit_and_push(repository_path, confirm_push)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/sse")
async def sse_endpoint(authenticated: bool = Depends(verify_token)):
    """Server-Sent Events endpoint for streaming updates."""
    async def event_generator():
        # Stream events to client
        yield {"event": "connected", "data": "MCP Server Ready"}
    
    return EventSourceResponse(event_generator())

if __name__ == "__main__":
    if config.tls_enabled:
        uvicorn.run(
            app,
            host=config.http_host,
            port=config.http_port,
            ssl_certfile=config.tls_cert_path,
            ssl_keyfile=config.tls_key_path,
        )
    else:
        uvicorn.run(
            app,
            host=config.http_host,
            port=config.http_port,
        )
```

#### Unified Entry Point
```python
# src/git_commit_mcp/__main__.py
import sys
from .config import ServerConfig
from .server import run_stdio_server
from .http_server import run_http_server

def main():
    config = ServerConfig.from_env()
    
    if config.transport_mode == "stdio":
        run_stdio_server()
    elif config.transport_mode == "http":
        run_http_server(config)
    else:
        print(f"Unknown transport mode: {config.transport_mode}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Security Considerations

### Local Mode
1. **Path Traversal**: Validate `repository_path` to prevent access outside intended directories
2. **Command Injection**: Use GitPython's API exclusively, avoid shell commands
3. **Credential Exposure**: Never log or return Git credentials
4. **File Permissions**: Respect file system permissions when writing CHANGELOG.md

### Remote Mode (Additional)
5. **Authentication**: Require valid bearer tokens for all API requests
6. **TLS/HTTPS**: Enforce HTTPS in production to encrypt data in transit
7. **Rate Limiting**: Implement rate limiting to prevent abuse (e.g., 100 requests/minute per token)
8. **Input Validation**: Sanitize all inputs (repository URLs, paths, commit messages)
9. **Secret Management**: Store sensitive credentials (SSH keys, tokens) in environment variables or secret managers
10. **CORS Policy**: Restrict CORS origins to trusted domains only
11. **Workspace Isolation**: Ensure cloned repositories are isolated per user/session
12. **Audit Logging**: Log all operations with timestamps, user identifiers, and outcomes
13. **Token Rotation**: Support token expiration and rotation for long-lived deployments
14. **Network Security**: Deploy behind firewall/VPC with restricted ingress rules
15. **Container Security**: Run containers as non-root user, scan images for vulnerabilities

## Deployment Examples

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Expose port
EXPOSE 8000

# Set environment
ENV TRANSPORT_MODE=http
ENV HTTP_PORT=8000

# Run server
CMD ["python", "-m", "git_commit_mcp"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  git-commit-mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - TRANSPORT_MODE=http
      - HTTP_HOST=0.0.0.0
      - HTTP_PORT=8000
      - MCP_AUTH_TOKEN=${MCP_AUTH_TOKEN}
      - GIT_SSH_KEY_PATH=/secrets/ssh_key
      - CORS_ORIGINS=https://myapp.com
    volumes:
      - ./secrets:/secrets:ro
      - git-workspaces:/tmp/git-workspaces
    restart: unless-stopped

volumes:
  git-workspaces:
```

### Cloud Run Deployment
```bash
# Build and push image
docker build -t gcr.io/my-project/git-commit-mcp:latest .
docker push gcr.io/my-project/git-commit-mcp:latest

# Deploy to Cloud Run
gcloud run deploy git-commit-mcp \
  --image gcr.io/my-project/git-commit-mcp:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars TRANSPORT_MODE=http,MCP_AUTH_TOKEN=secret123 \
  --allow-unauthenticated \
  --port 8000
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: git-commit-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: git-commit-mcp
  template:
    metadata:
      labels:
        app: git-commit-mcp
    spec:
      containers:
      - name: server
        image: git-commit-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: TRANSPORT_MODE
          value: "http"
        - name: MCP_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: auth-token
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: git-commit-mcp
spec:
  selector:
    app: git-commit-mcp
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Systemd Service (VPS)
```ini
[Unit]
Description=Git Commit MCP Server
After=network.target

[Service]
Type=simple
User=mcpuser
WorkingDirectory=/opt/git-commit-mcp
Environment="TRANSPORT_MODE=http"
Environment="HTTP_PORT=8000"
Environment="MCP_AUTH_TOKEN=your-secret-token"
ExecStart=/opt/git-commit-mcp/.venv/bin/python -m git_commit_mcp
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Client Configuration

### Local Mode (stdio)
```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uvx",
      "args": ["git-commit-mcp-server"]
    }
  }
}
```

### Remote Mode (HTTP)
```json
{
  "mcpServers": {
    "git-commit-remote": {
      "url": "https://mcp.example.com",
      "transport": "http",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

### Railway Deployment

Railway is a modern platform-as-a-service that simplifies deployment with built-in CI/CD, persistent volumes, and environment management.

#### Railway Configuration

**railway.json**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "python -m git_commit_mcp",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### Dockerfile for Railway

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (Git and SSH)
RUN apt-get update && apt-get install -y \
    git \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create workspace directory
RUN mkdir -p /data/git-workspaces && chmod 755 /data/git-workspaces

# Expose port (Railway assigns PORT env var)
EXPOSE 8000

# Set default environment variables
ENV TRANSPORT_MODE=http
ENV HTTP_HOST=0.0.0.0
ENV WORKSPACE_DIR=/data/git-workspaces
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run server
CMD ["python", "-m", "git_commit_mcp"]
```

#### Railway Environment Variables

Configure these in the Railway dashboard:

**Required:**
- `TRANSPORT_MODE=http`
- `HTTP_PORT=8000` (or use Railway's `$PORT`)
- `MCP_AUTH_TOKEN=<generate-secure-token>`
- `WORKSPACE_DIR=/data/git-workspaces`

**Optional:**
- `GIT_SSH_KEY_PATH=/data/ssh/id_rsa` (if using SSH)
- `GIT_USERNAME=<github-username>` (if using HTTPS)
- `GIT_TOKEN=<github-token>` (if using HTTPS)
- `CORS_ORIGINS=*` (or specific domains)
- `LOG_LEVEL=INFO`
- `ENABLE_METRICS=true`

#### Railway Volume Configuration

1. **Create a Volume:**
   - Name: `git-workspaces`
   - Mount Path: `/data`
   - Size: 2-5 GB (adjust based on needs)

2. **Volume Benefits:**
   - Cloned repositories persist across deployments
   - Faster subsequent operations (no re-cloning)
   - SSH keys can be stored persistently
   - Reduces bandwidth usage

#### Deployment Steps

1. **Connect Repository:**
   ```bash
   # Push code to GitHub
   git push origin main
   ```

2. **Create Railway Project:**
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure Volume:**
   - In project settings, go to "Volumes"
   - Click "New Volume"
   - Set mount path to `/data`
   - Set size to 2 GB

4. **Set Environment Variables:**
   - Go to "Variables" tab
   - Add all required environment variables
   - Generate secure token for `MCP_AUTH_TOKEN`

5. **Deploy:**
   - Railway auto-deploys on push
   - Monitor logs in Railway dashboard
   - Access via generated Railway URL

#### Railway-Specific Considerations

**Port Binding:**
Railway provides a `PORT` environment variable. Update config to use it:
```python
# In config.py
http_port: int = int(os.getenv("PORT", "8000"))
```

**Health Checks:**
Railway uses the `/health` endpoint to monitor service health.

**Logging:**
All logs to stdout/stderr are captured by Railway's logging system.

**Scaling:**
Railway Hobby plan supports vertical scaling. Adjust resources in project settings.

**Custom Domain:**
Configure custom domain in Railway settings for production use.

## Future Enhancements

1. Support for custom commit message templates
2. Integration with issue trackers (e.g., "Fixes #123")
3. Configurable changelog format
4. Support for semantic versioning in changelog
5. Pre-commit hooks integration
6. Support for multiple remotes
7. WebSocket transport for bidirectional communication
8. Multi-tenancy with per-user workspaces
9. Repository caching and incremental updates
10. Webhook support for CI/CD integration
11. GraphQL API for advanced queries
12. Metrics and observability dashboard
