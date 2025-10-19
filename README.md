# Git Commit MCP Server

An MCP (Model Context Protocol) server that automates Git commit workflows with conventional commit messages, changelog management, and push confirmation.

## Overview

Git Commit MCP Server streamlines your Git workflow by providing AI assistants with intelligent commit automation. It analyzes your code changes, generates professional commit messages following industry standards, and maintains a comprehensive changelog—all through natural language interactions with your AI assistant.

## Features

- **Automatic Change Detection**: Tracks modified, added, deleted, and renamed files since the last commit
- **Conventional Commit Messages**: Generates standardized commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification
- **Smart Commit Type Detection**: Analyzes file changes to determine appropriate commit types (feat, fix, docs, chore, etc.) based on file paths and patterns
- **Intelligent Scope Extraction**: Automatically determines commit scope from directory structure
- **Push Confirmation**: Requires explicit user approval before pushing to remote repositories
- **Changelog Management**: Automatically maintains a CHANGELOG.md file with commit history in reverse chronological order
- **MCP Integration**: Works seamlessly with AI assistants that support the Model Context Protocol (Kiro, Claude Desktop, etc.)

## Installation

### Prerequisites

- Python 3.10 or higher
- Git installed and configured on your system
- An MCP-compatible AI assistant (Kiro, Claude Desktop, etc.)

### Using uvx (Recommended)

The easiest way to use this MCP server is with `uvx`, which comes with the `uv` Python package manager. This method requires no manual installation—the server is automatically downloaded and run when needed.

1. **Install uv** if you haven't already:

   **macOS/Linux:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   
   **Windows:**
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   **Alternative methods:**
   ```bash
   # Using pip
   pip install uv
   
   # Using Homebrew (macOS)
   brew install uv
   
   # Using pipx
   pipx install uv
   ```

2. **Configure your MCP client** (see Configuration section below). The server will be automatically downloaded and run when your AI assistant needs it.

### Manual Installation (Development)

For local development or testing:

```bash
# Clone the repository
git clone https://github.com/yourusername/git-commit-mcp-server.git
cd git-commit-mcp-server

# Install with uv
uv pip install -e .

# Or install with development dependencies
uv pip install -e ".[dev]"
```

### Verifying Installation

After configuration, you can verify the server is working by asking your AI assistant:
```
"Can you check if the git-commit MCP server is available?"
```

## Configuration

### MCP Client Configuration

Add this server to your MCP client's configuration file. The location varies by client:

- **Kiro IDE**: `.kiro/settings/mcp.json` (workspace) or `~/.kiro/settings/mcp.json` (global)
- **Claude Desktop**: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

#### Production Configuration (Using uvx)

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

#### Development Configuration (Local)

For local development and testing:

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/git-commit-mcp-server", "python", "-m", "git_commit_mcp.server"],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

**Note:** Replace `/absolute/path/to/git-commit-mcp-server` with the actual path to your local repository.

#### Configuration Options

- **`disabled`**: Set to `true` to temporarily disable the server without removing the configuration
- **`autoApprove`**: List of tool names to auto-approve without user confirmation (use with caution)
  ```json
  "autoApprove": ["git_commit_and_push"]
  ```

### Applying Configuration Changes

After modifying the configuration:

- **Kiro IDE**: The server reconnects automatically, or use the MCP Server view to manually reconnect
- **Claude Desktop**: Restart the application

## Usage

Once configured, AI assistants can use the `git_commit_and_push` tool to automate your Git workflow through natural language interactions.

### Available Tools

#### `git_commit_and_push`

Automates the complete Git commit workflow: detects changes, generates a commit message, stages files, creates the commit, optionally pushes to remote, and updates the changelog.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repository_path` | string | No | `"."` | Path to the Git repository. Use `"."` for current directory or provide an absolute/relative path. |
| `confirm_push` | boolean | No | `false` | Whether to push to remote after committing. Set to `true` only after user confirmation. |

**Returns:**

```json
{
  "success": true,
  "commit_hash": "abc1234567890def",
  "commit_message": "feat(auth): Add user authentication\n\n- Add login module\n- Add password validation",
  "files_changed": 3,
  "pushed": false,
  "changelog_updated": true,
  "message": "Successfully committed 3 file(s) [abc1234]"
}
```

### Example Interactions

#### Basic Commit

```
User: "Commit my changes"

AI Assistant: "I'll commit your changes. Let me check what's been modified..."

[AI uses git_commit_and_push with default parameters]

AI Assistant: "I've created a commit with the message:

feat(auth): Add user authentication module

- Add user_auth.py
- Update api_endpoints.py
- Update login_form.py

The commit has been created locally. Would you like me to push it to the remote repository?"
```

#### Commit and Push

```
User: "Yes, push it"

AI Assistant: [Uses git_commit_and_push with confirm_push=true]

"Successfully pushed to origin/main! Your changes are now on the remote repository."
```

#### Commit Specific Repository

```
User: "Commit the changes in my backend project at ~/projects/backend"

AI Assistant: [Uses git_commit_and_push with repository_path="~/projects/backend"]

"I've committed the changes in your backend project:

fix(database): Fix connection timeout issue

- Update connection_pool.py
- Update retry_logic.py

Would you like to push this commit?"
```

#### No Changes to Commit

```
User: "Commit my changes"

AI Assistant: [Uses git_commit_and_push]

"There are no changes to commit. Your working directory is clean."
```

### Workflow

The tool follows this workflow:

1. **Detect Changes**: Scans the repository for modified, added, deleted, and renamed files
2. **Generate Message**: Creates a conventional commit message based on the changes
3. **Stage Files**: Stages all detected changes using `git add`
4. **Create Commit**: Creates the commit with the generated message
5. **Push (Optional)**: If `confirm_push` is true, pushes to the remote repository
6. **Update Changelog**: Appends an entry to CHANGELOG.md with commit details

### Best Practices

- **Always review** the generated commit message before pushing
- **Use push confirmation**: Let the AI ask before pushing to ensure you're ready
- **Commit frequently**: Make small, focused commits rather than large ones
- **Check the changelog**: Review CHANGELOG.md periodically to ensure it's accurate
- **Stage intentionally**: The tool commits all changes, so review `git status` first if needed
- **Use meaningful file names**: Better file names lead to better commit messages

## Frequently Asked Questions

### How does the server determine commit type?

The server analyzes file paths, extensions, and change patterns. For example:
- New files in `src/` → `feat`
- Changes in `tests/` → `test`
- Changes to `.md` files → `docs`
- Changes to config files → `chore`

See the [Commit Types](#commit-types) section for full details.

### Can I customize the commit message format?

Currently, the server uses a fixed format following Conventional Commits. You can manually edit commit messages after they're generated by using standard Git commands, but the server will always generate messages in this format.

### What happens if I have uncommitted changes in multiple directories?

The server will:
1. Detect all changes across all directories
2. Determine the most common scope from the changed files
3. Generate a single commit with all changes
4. List up to 5 files in the bullet points

For better commit organization, consider committing changes from different features separately.

### Does the server work with Git submodules?

The server works with the main repository but doesn't automatically handle submodules. You'll need to commit submodule changes separately within each submodule directory.

### Can I use this with GitHub/GitLab/Bitbucket?

Yes! The server works with any Git remote. It uses standard Git commands, so it's compatible with all Git hosting services.

### What if I want to commit only specific files?

The server commits all detected changes. To commit specific files:
1. Stage only the files you want: `git add file1.py file2.py`
2. Use the server to commit staged changes
3. Or use standard Git commands for more granular control

### How do I disable the server temporarily?

Set `"disabled": true` in your MCP configuration:
```json
{
  "mcpServers": {
    "git-commit": {
      "disabled": true
    }
  }
}
```

### Can multiple people use this on the same repository?

Yes! Each person can use the server independently. The CHANGELOG.md file will contain entries from all commits, regardless of who made them or whether they used this server.

### What happens if the changelog update fails?

The commit still succeeds. Changelog updates are non-critical, so if they fail (e.g., due to permissions), you'll see a warning but the commit will be created successfully.

## Conventional Commit Format

The server generates commit messages following the [Conventional Commits](https://www.conventionalcommits.org/) specification, which provides a standardized format for commit messages that makes it easier to understand project history and automate versioning.

### Message Structure

```
<type>(<scope>): <short description>
<optional second line for additional context>

- <bullet point 1>
- <bullet point 2>
- <bullet point 3>
- <bullet point 4>
- <bullet point 5>
```

**Example:**
```
feat(auth): Add user authentication module

- Add user_auth.py with login/logout functions
- Update api_endpoints.py with auth routes
- Add password validation utility
```

### Commit Types

The server automatically detects the appropriate commit type based on file changes:

| Type | Description | Example Files |
|------|-------------|---------------|
| **feat** | New features or functionality | New files in `src/`, `lib/`, `app/` |
| **fix** | Bug fixes | Files with bug-related changes |
| **docs** | Documentation changes | `README.md`, `*.md` files, `docs/` directory |
| **style** | Code style/formatting changes | `*.css`, `*.scss` files, style directories |
| **refactor** | Code refactoring without new features | Modified files without additions |
| **test** | Test additions or modifications | Files in `test/`, `tests/`, `__tests__/` |
| **chore** | Maintenance, configuration, dependencies | `pyproject.toml`, `package.json`, config files |

### Type Detection Logic

The server uses intelligent heuristics to determine commit type:

1. **File Path Analysis**: Examines directory structure (e.g., `tests/` → `test`)
2. **File Extension**: Checks file types (e.g., `.md` → `docs`, `.css` → `style`)
3. **Change Pattern**: Analyzes whether files are added, modified, or deleted
4. **Priority System**: When multiple types apply, uses priority: `feat` > `fix` > `docs` > `style` > `refactor` > `test` > `chore`

### Scope Detection

The scope is automatically extracted from the directory structure:

- **Single Directory**: Changes in `src/auth/` → scope: `auth`
- **Multiple Directories**: Uses the most common directory
- **Nested Structure**: Skips common prefixes like `src/`, `lib/` to find meaningful scope
- **No Clear Scope**: Omits scope if unclear (e.g., root-level files)

**Examples:**
- `src/auth/login.py` → scope: `auth`
- `lib/database/connection.py` → scope: `database`
- `README.md` → no scope

### Bullet Points

The server generates up to 5 bullet points describing the changes:

- **Added files**: "Add filename.py"
- **Deleted files**: "Remove filename.py"
- **Renamed files**: "Rename old_name.py to new_name.py"
- **Modified files**: "Update filename.py"

Bullet points are prioritized: additions first, then deletions, renames, and finally modifications.

## Changelog Management

The server automatically maintains a `CHANGELOG.md` file in your repository, providing a human-readable history of all commits.

### Changelog Format

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### 2025-10-19 14:30:45 - abc1234 [PUSHED]

feat(auth): Add user authentication module

- Add user_auth.py
- Update api_endpoints.py
- Update login_form.py

### 2025-10-19 13:15:22 - def5678 [LOCAL]

docs: Update README with installation instructions

- Update README.md
- Add code examples
```

### Entry Components

Each changelog entry includes:

| Component | Description | Example |
|-----------|-------------|---------|
| **Timestamp** | Date and time of commit | `2025-10-19 14:30:45` |
| **Short Hash** | First 7 characters of commit SHA | `abc1234` |
| **Push Status** | Whether commit was pushed | `[PUSHED]` or `[LOCAL]` |
| **Commit Message** | Full conventional commit message | Type, scope, description, and bullet points |

### Changelog Features

- **Automatic Creation**: If CHANGELOG.md doesn't exist, it's created with proper headers
- **Reverse Chronological Order**: Newest entries appear first
- **Unreleased Section**: New commits are added under `## [Unreleased]`
- **Push Tracking**: Clearly indicates which commits are local vs. pushed
- **Consistent Formatting**: Maintains professional, readable format

### Manual Changelog Editing

You can manually edit CHANGELOG.md to:
- Add release version headers (e.g., `## [1.0.0] - 2025-10-19`)
- Group commits by type (features, fixes, etc.)
- Add release notes or migration guides
- Remove or consolidate entries

The server will continue to append new entries under `## [Unreleased]` without disrupting your manual edits.

## Troubleshooting

### Server Not Found or Won't Start

**Symptoms:** MCP client reports the server is unavailable or fails to start.

**Solutions:**

1. **Verify uv installation:**
   ```bash
   uv --version
   ```
   If not found, reinstall uv following the installation instructions above.

2. **Check PATH:** Ensure `uv` is in your system PATH:
   ```bash
   # macOS/Linux
   which uv
   
   # Windows
   where uv
   ```

3. **Verify configuration:** Check that your `mcp.json` has the correct syntax and server name.

4. **Restart your MCP client** after configuration changes.

5. **Check server logs:** Look for error messages in your MCP client's logs or console.

6. **Test manually:**
   ```bash
   uvx git-commit-mcp-server
   ```

### Authentication Errors When Pushing

**Symptoms:** Push operations fail with "authentication failed" or "permission denied" errors.

**Solutions:**

1. **Configure Git credentials:**
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   ```

2. **Set up SSH keys** (recommended):
   ```bash
   # Generate SSH key
   ssh-keygen -t ed25519 -C "your.email@example.com"
   
   # Add to ssh-agent
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   
   # Copy public key and add to GitHub/GitLab/etc.
   cat ~/.ssh/id_ed25519.pub
   ```

3. **Use credential helper** (HTTPS):
   ```bash
   # macOS
   git config --global credential.helper osxkeychain
   
   # Windows
   git config --global credential.helper wincred
   
   # Linux
   git config --global credential.helper cache
   ```

4. **Test authentication manually:**
   ```bash
   git push
   ```
   If this works, the MCP server should work too.

### No Remote Configured

**Symptoms:** Error message "No remote repository configured" when trying to push.

**Solutions:**

1. **Add a remote:**
   ```bash
   git remote add origin https://github.com/username/repo.git
   # or
   git remote add origin git@github.com:username/repo.git
   ```

2. **Verify remote:**
   ```bash
   git remote -v
   ```

3. **Set upstream branch:**
   ```bash
   git push -u origin main
   ```

### Permission Errors with CHANGELOG.md

**Symptoms:** Server reports it can't write to CHANGELOG.md.

**Solutions:**

1. **Check file permissions:**
   ```bash
   ls -la CHANGELOG.md
   ```

2. **Fix permissions:**
   ```bash
   chmod 644 CHANGELOG.md
   ```

3. **Verify repository path:** Ensure the `repository_path` parameter points to the correct directory.

4. **Check disk space:**
   ```bash
   df -h
   ```

### "Not a Git Repository" Error

**Symptoms:** Error message "Not a git repository" when trying to commit.

**Solutions:**

1. **Initialize Git repository:**
   ```bash
   git init
   ```

2. **Verify you're in the correct directory:**
   ```bash
   pwd  # macOS/Linux
   cd   # Windows
   ```

3. **Check for .git directory:**
   ```bash
   ls -la .git
   ```

### No Changes to Commit

**Symptoms:** Server reports "No changes to commit" when you expect changes.

**Solutions:**

1. **Check Git status manually:**
   ```bash
   git status
   ```

2. **Verify files are tracked:** Untracked files are detected but may need to be added first.

3. **Check .gitignore:** Ensure your changes aren't being ignored.

4. **Refresh your editor:** Some editors cache file states.

### Server Performance Issues

**Symptoms:** Server is slow or times out.

**Solutions:**

1. **Check repository size:** Very large repositories may take longer to analyze.

2. **Reduce number of changes:** Commit more frequently with smaller changesets.

3. **Check system resources:**
   ```bash
   # macOS/Linux
   top
   
   # Windows
   taskmgr
   ```

4. **Update dependencies:**
   ```bash
   uv pip install --upgrade git-commit-mcp-server
   ```

### Getting Help

If you continue to experience issues:

1. **Check the logs:** Look for detailed error messages in your MCP client's console or log files.

2. **Create an issue:** Report bugs on the [GitHub repository](https://github.com/yourusername/git-commit-mcp-server/issues) with:
   - Error messages
   - Your configuration
   - Steps to reproduce
   - System information (OS, Python version, uv version)

3. **Test in isolation:** Try running the server manually to isolate MCP client issues:
   ```bash
   uvx git-commit-mcp-server
   ```

## Development

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/git-commit-mcp-server.git
   cd git-commit-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   uv pip install -e ".[dev]"
   ```

3. **Run the server locally:**
   ```bash
   uv run python -m git_commit_mcp.server
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=git_commit_mcp

# Run specific test file
pytest tests/test_change_tracker.py

# Run with verbose output
pytest -v
```

### Project Structure

```
git-commit-mcp-server/
├── .kiro/                          # Kiro IDE configuration
│   ├── settings/                   # MCP and other settings
│   ├── specs/                      # Feature specifications
│   └── steering/                   # AI assistant guidance
├── src/
│   └── git_commit_mcp/
│       ├── __init__.py             # Package initialization
│       ├── server.py               # Main MCP server and tool definitions
│       ├── models.py               # Data models (ChangeSet, CommitResult, etc.)
│       ├── change_tracker.py       # Git change detection logic
│       ├── message_generator.py    # Commit message generation
│       ├── git_operations.py       # Git command wrappers
│       └── changelog_manager.py    # CHANGELOG.md management
├── tests/                          # Test suite
│   ├── test_change_tracker.py
│   ├── test_message_generator.py
│   ├── test_git_operations.py
│   └── test_changelog_manager.py
├── pyproject.toml                  # Project metadata and dependencies
└── README.md                       # This file
```

### Architecture

The server follows a modular architecture with clear separation of concerns:

- **server.py**: MCP server entry point, orchestrates the workflow
- **change_tracker.py**: Detects file changes using GitPython
- **message_generator.py**: Analyzes changes and generates commit messages
- **git_operations.py**: Executes Git commands (stage, commit, push)
- **changelog_manager.py**: Maintains CHANGELOG.md file
- **models.py**: Data structures shared across components

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all public classes and methods
- Keep functions focused and single-purpose
- Add tests for new features

### Testing Guidelines

- Write unit tests for all new functionality
- Use mocks for Git operations to avoid side effects
- Test both success and failure scenarios
- Maintain test coverage above 80%

## Contributing

Contributions are welcome! Here's how you can help:

1. **Report bugs**: Open an issue with details about the problem
2. **Suggest features**: Describe new functionality you'd like to see
3. **Submit pull requests**: Fix bugs or implement features

### Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes using conventional commits
7. Push to your fork (`git push origin feature/amazing-feature`)
8. Open a pull request

## License

[Add your license here]

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) - A framework for building MCP servers
- Uses [GitPython](https://github.com/gitpython-developers/GitPython) - Python library for Git operations
- Follows [Conventional Commits](https://www.conventionalcommits.org/) - A specification for commit messages
- Inspired by the need for better Git workflow automation in AI-assisted development

## Related Projects

- [Model Context Protocol](https://modelcontextprotocol.io/) - The protocol specification
- [FastMCP](https://github.com/jlowin/fastmcp) - MCP server framework
- [Kiro IDE](https://kiro.ai/) - AI-powered IDE with MCP support

## Support

- **Documentation**: This README and inline code documentation
- **Issues**: [GitHub Issues](https://github.com/yourusername/git-commit-mcp-server/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/git-commit-mcp-server/discussions)
