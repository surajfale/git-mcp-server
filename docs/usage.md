# Usage — git-commit-mcp-server

This page covers setup, configuration, and common usage patterns for running the MCP server locally or in production.

## Prerequisites

- Python 3.10+
- Git installed and configured
- `uv` for package management (recommended)
- `pipx` for global installation (recommended)

## Installation

### Option 1: Global Installation with pipx (Recommended)

Install the package globally so it's available from any directory:

**From PyPI (Production):**
```powershell
pipx install git-commit-mcp-server
```

**From TestPyPI (Testing):**
```powershell
pipx install git-commit-mcp-server --index-url https://test.pypi.org/simple/ --pip-args="--extra-index-url https://pypi.org/simple/"
```

**Verify installation:**
```powershell
git-commit-mcp --help
```

### Option 2: Development Installation

For local development from the repository:

```powershell
# Clone the repository
git clone https://github.com/surajfale/git-mcp-server.git
cd git-mcp-server

# Install with development dependencies
uv pip install -e ".[dev]"

# Run directly
python -m git_commit_mcp.__main__
```

## Environment Variables

The server uses these environment variables for configuration:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes (if AI enabled) | - | OpenAI API key for AI-powered commit messages |
| `ENABLE_AI` | No | `true` | Enable/disable AI message generation |
| `AI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `FORCE_SSH_ONLY` | No | `true` | Reject HTTPS Git URLs, require SSH |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Setting Environment Variables

**PowerShell (Current Session):**
```powershell
$env:OPENAI_API_KEY = 'sk-your-key-here'
$env:ENABLE_AI = 'true'
$env:AI_MODEL = 'gpt-4o-mini'
```

**PowerShell (Persistent):**
```powershell
setx OPENAI_API_KEY "sk-your-key-here"
# Restart your terminal for changes to take effect
```

**Using .env file:**
```powershell
# Copy the example file
Copy-Item .env.example .env

# Edit with your values
notepad .env
```

## MCP Client Configuration

### Kiro IDE Configuration

Add the server to your MCP configuration file:

**Location:**
- Workspace: `.kiro/settings/mcp.json`
- Global: `~/.kiro/settings/mcp.json` (or `C:\Users\<username>\.kiro\settings\mcp.json` on Windows)

**Configuration (After Global Installation):**

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "git-commit-mcp",
      "args": [],
      "disabled": false,
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini",
        "FORCE_SSH_ONLY": "true"
      },
      "autoApprove": []
    }
  }
}
```

**Configuration (Development Mode):**

For local development, point to your repository:

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\path\\to\\git-commit-mcp-server",
        "python",
        "-m",
        "git_commit_mcp.__main__"
      ],
      "disabled": false,
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      },
      "autoApprove": []
    }
  }
}
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "git-commit-mcp",
      "args": [],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

### Cursor IDE Configuration

Cursor IDE has specific requirements for MCP server configuration. Follow these steps carefully:

**Configuration File Location:**

Cursor uses a global MCP configuration file:
- **Windows:** `%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`
- **macOS:** `~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **Linux:** `~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`

**Configuration (After Global Installation with pipx):**

```json
{
  "mcpServers": {
    "git-commit-mcp": {
      "command": "git-commit-mcp",
      "args": [],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini",
        "FORCE_SSH_ONLY": "true"
      }
    }
  }
}
```

**Configuration (Local Development Mode - Windows):**

For local development on Windows, use absolute paths with proper escaping:

**Option 1: Using venv's Python executable directly:**

```json
{
  "mcpServers": {
    "git-commit-mcp": {
      "command": "C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "git_commit_mcp.__main__"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

**Option 2: Using venv's installed script executable (Recommended if available):**

If you've installed the package in your venv, you can use the script directly:

```json
{
  "mcpServers": {
    "git-commit-mcp": {
      "command": "C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message\\.venv\\Scripts\\git-commit-mcp.exe",
      "args": [],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

**Option 3: Using python command with cwd (if venv is activated in PATH):**

```json
{
  "mcpServers": {
    "git-commit-mcp": {
      "command": "python",
      "args": [
        "-m",
        "git_commit_mcp.__main__"
      ],
      "cwd": "C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message",
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

**Alternative Configuration (Using uv on Windows):**

If you're using `uv` for development:

```json
{
  "mcpServers": {
    "git-commit-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message",
        "python",
        "-m",
        "git_commit_mcp.__main__"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-your-key-here",
        "ENABLE_AI": "true",
        "AI_MODEL": "gpt-4o-mini"
      }
    }
  }
}
```

**Important Notes for Cursor:**

1. **Server Name Caching:** Cursor caches MCP server names. If you see errors even after fixing configuration:
   - Try renaming the server to a unique name (e.g., `git-commit-mcp-v2`)
   - Restart Cursor completely
   - Clear Cursor's cache if needed

2. **Windows Path Handling:**
   - Use double backslashes (`\\`) or forward slashes (`/`) in paths
   - Use absolute paths when possible
   - Ensure Python is in your system PATH

3. **Verification Steps:**
   ```powershell
   # Test if the command works from terminal
   git-commit-mcp --help
   
   # Or for development mode
   python -m git_commit_mcp.__main__
   ```

4. **Common Issues:**
   - If Cursor shows a red status indicator, check the Cursor output panel for detailed error messages
   - Ensure Python executable is accessible (use full path if needed: `C:\\Python\\python.exe`)
   - Verify environment variables are set correctly in the `env` section

### Configuration Notes

- **Environment Variables:** Pass sensitive values like `OPENAI_API_KEY` through the `env` field to keep them out of version control
- **Auto-Approve:** Add tool names to `autoApprove` array to skip confirmation prompts (use with caution)
- **Disabled:** Set `"disabled": true` to temporarily disable the server without removing the configuration
- **Working Directory:** The server automatically uses the directory where your MCP client is opened

## Using the MCP Tools

The server provides two main tools for Git commit automation:

### 1. `generate_commit_message`

Generates a conventional commit message without creating a commit.

**Parameters:**
- `repository_path` (optional): Path to Git repository (default: `"."`)

**Returns:**
- `success`: Boolean indicating if message was generated
- `commit_message`: The generated conventional commit message
- `files_changed`: Number of files that would be committed
- `message`: Human-readable status message
- `error`: Error message if operation failed

**Example Usage:**
```
User: "Generate a commit message for my changes"
AI: [Calls generate_commit_message with repository_path="."]
```

### 2. `git_commit_and_push`

Automates the complete Git workflow: detects changes, generates message, commits, and optionally pushes.

**Parameters:**
- `repository_path` (optional): Path to Git repository (default: `"."`)
- `confirm_push` (optional): Whether to push after committing (default: `false`)

**Returns:**
- `success`: Boolean indicating if operation succeeded
- `commit_hash`: SHA hash of the created commit
- `commit_message`: The generated commit message
- `files_changed`: Number of files committed
- `pushed`: Boolean indicating if changes were pushed
- `changelog_updated`: Boolean indicating if CHANGELOG.md was updated
- `message`: Human-readable status message
- `error`: Error message if operation failed

**Example Interactions:**

**Commit locally:**
```
User: "Commit my changes"
AI: [Calls git_commit_and_push with confirm_push=false]
AI: "Created commit abc1234: feat(auth): Add user authentication"
```

**Commit and push:**
```
User: "Commit and push my changes"
AI: [Calls git_commit_and_push with confirm_push=true]
AI: "Committed and pushed to origin/main"
```

**Different repository:**
```
User: "Commit changes in ~/projects/backend"
AI: [Calls git_commit_and_push with repository_path="~/projects/backend"]
```

## Testing

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=git_commit_mcp

# Run specific test file
pytest tests/test_integration.py

# Run with verbose output
pytest -v
```

### Integration Tests

Integration tests cover:
- Repository cloning (SSH and HTTPS)
- Change detection
- AI-powered message generation
- Commit creation
- Changelog updates
- Push operations

See `tests/test_integration.py` for details.

## Troubleshooting

### Server Won't Start

**Problem:** `'git-commit-mcp' is not recognized as a command`

**Solution:**
```powershell
# Verify installation
pipx list

# Reinstall if needed
pipx install git-commit-mcp-server

# Check PATH
where.exe git-commit-mcp
```

### OpenAI API Key Issues

**Problem:** "OPENAI_API_KEY is not set" error

**Solution:**
1. Set the environment variable in your MCP config's `env` field
2. Or set it globally:
   ```powershell
   setx OPENAI_API_KEY "sk-your-key-here"
   ```
3. Restart your MCP client after setting the variable

### Git Repository Errors

**Problem:** "Not a git repository" error

**Solution:**
- Ensure you're in a Git repository directory
- Initialize Git if needed: `git init`
- Check that `.git` directory exists: `ls -la .git`

### Authentication Errors

**Problem:** Push fails with "authentication failed"

**Solution:**
1. **For SSH:** Set up SSH keys
   ```powershell
   ssh-keygen -t ed25519 -C "your.email@example.com"
   # Add public key to GitHub/GitLab
   ```

2. **For HTTPS:** Configure Git credentials
   ```powershell
   git config --global credential.helper wincred  # Windows
   git config --global credential.helper osxkeychain  # macOS
   ```

3. **Force SSH only:** Set `FORCE_SSH_ONLY=true` in your MCP config

### Changelog Issues

**Problem:** Changelog update fails

**Solution:**
- Changelog failures are non-fatal - commits still succeed
- Check file permissions: `ls -la CHANGELOG.md`
- Ensure write access to the repository directory

### Working Directory Issues

**Problem:** Server operates on wrong repository

**Solution:**
- The server uses the directory where your MCP client is opened
- For development mode, ensure `--directory` points to the correct path
- For global installation, open your MCP client in the desired project directory

### Cursor IDE Specific Issues

**Problem:** MCP server shows red status or errors in Cursor but works in other IDEs

**Solution Steps:**

1. **Verify Configuration File Location:**
   ```powershell
   # Windows - check if file exists
   Test-Path "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json"
   
   # If it doesn't exist, create the directory structure
   New-Item -ItemType Directory -Force -Path "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings"
   ```

2. **Check Configuration JSON Syntax:**
   - Ensure JSON is valid (no trailing commas, proper quotes)
   - Use a JSON validator if needed
   - Windows paths must use double backslashes: `C:\\Users\\...`

3. **Clear Cursor's Server Name Cache:**
   - Close Cursor completely
   - Rename your server to a unique name (e.g., `git-commit-mcp-local` instead of `git-commit-mcp`)
   - Restart Cursor
   - The cache issue is a known Cursor limitation

4. **Use Full Python Path (Windows):**
   If `python` command isn't found, use the full path:
   ```json
   {
     "mcpServers": {
       "git-commit-mcp": {
         "command": "C:\\Python\\python.exe",
         "args": ["-m", "git_commit_mcp.__main__"],
         "cwd": "C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message"
       }
     }
   }
   ```

5. **Check Cursor Output Panel:**
   - Open Cursor's Output panel (View → Output)
   - Select "MCP" or "Claude Dev" from the dropdown
   - Look for detailed error messages
   - Common errors include:
     - "Command not found" → Check PATH or use full path
     - "Module not found" → Ensure dependencies are installed
     - "Permission denied" → Check file permissions

6. **Test Command Manually:**
   ```powershell
   # Test the exact command Cursor will run
   cd C:\Users\suraj\MyWork\mcp_servers\git_commit_message
   python -m git_commit_mcp.__main__
   
   # Or if using pipx
   git-commit-mcp
   ```

7. **Alternative: Use pipx Installation:**
   If local development mode doesn't work, install globally with pipx:
   ```powershell
   pipx install git-commit-mcp-server
   ```
   Then use the simpler configuration:
   ```json
   {
     "mcpServers": {
       "git-commit-mcp": {
         "command": "git-commit-mcp",
         "args": []
       }
     }
   }
   ```

**Problem:** Server works in terminal but not in Cursor

**Solution:**
- Cursor may use a different PATH environment variable
- Check Cursor's environment: Add `"env": {"PATH": "C:\\Python;C:\\Python\\Scripts;%PATH%"}` to your config
- Or use absolute paths for all executables

**Problem:** Configuration file not found or not being read

**Solution:**
- Ensure the file is named exactly: `cline_mcp_settings.json`
- Check file permissions (should be readable)
- Try creating the file manually if it doesn't exist
- Restart Cursor after creating/modifying the file

## Updating the Package

### Update from PyPI

```powershell
pipx upgrade git-commit-mcp-server
```

### Update from TestPyPI

```powershell
pipx upgrade git-commit-mcp-server --index-url https://test.pypi.org/simple/ --pip-args="--extra-index-url https://pypi.org/simple/"
```

### Uninstall

```powershell
pipx uninstall git-commit-mcp-server
```

## Advanced Configuration

### Custom AI Models

You can use different OpenAI models by setting the `AI_MODEL` environment variable:

```json
{
  "env": {
    "OPENAI_API_KEY": "sk-your-key-here",
    "AI_MODEL": "gpt-4"
  }
}
```

Supported models:
- `gpt-4o-mini` (default, cost-effective)
- `gpt-4o` (more capable)
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Disable AI Generation

To use heuristic-based commit messages instead of AI:

```json
{
  "env": {
    "ENABLE_AI": "false"
  }
}
```

### Custom Workspace Directory

For remote repository cloning:

```json
{
  "env": {
    "WORKSPACE_DIR": "/custom/path/to/workspaces"
  }
}
```

## Best Practices

1. **Keep API Keys Secure:** Never commit API keys to version control
2. **Use Environment Variables:** Pass sensitive data through the `env` field in MCP config
3. **Test Before Pushing:** Review generated commit messages before pushing
4. **Commit Frequently:** Make small, focused commits for better AI-generated messages
5. **Review Changelog:** Periodically check CHANGELOG.md for accuracy
6. **Use SSH for Git:** More secure than HTTPS, set `FORCE_SSH_ONLY=true`
