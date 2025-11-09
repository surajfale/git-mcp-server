# Cursor IDE Setup Guide

This guide provides step-by-step instructions for setting up the git-commit-mcp server in Cursor IDE, especially for local development installations.

## Quick Start

### Step 1: Locate Cursor's MCP Configuration File

**Windows:**
```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

**macOS:**
```
~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

**Linux:**
```
~/.config/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

### Step 2: Create Configuration File (if it doesn't exist)

**PowerShell (Windows):**
```powershell
$configPath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings"
New-Item -ItemType Directory -Force -Path $configPath

$configFile = Join-Path $configPath "cline_mcp_settings.json"
@'
{
  "mcpServers": {}
}
'@ | Out-File -FilePath $configFile -Encoding utf8
```

### Step 3: Add Server Configuration

#### Option A: Using pipx Installation (Recommended)

If you've installed the server globally with pipx:

```json
{
  "mcpServers": {
    "git-commit-mcp": {
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

#### Option B: Local Development Mode (Windows)

For local development, you can use the venv's executable directly:

**Option B1: Using venv's script executable (Recommended):**

If you've installed the package in your venv (e.g., `pip install -e .`), use the script directly:

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

**Option B2: Using venv's Python executable:**

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

**Option B3: Using python command with cwd:**

If your venv is activated or Python is in PATH:

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

**Important:** 
- Replace `C:\\Users\\suraj\\MyWork\\mcp_servers\\git_commit_message` with your actual project path
- Replace `.venv` with your venv folder name if different (e.g., `venv`, `env`)
- Option B1 is recommended as it uses the venv's installed script directly

#### Option C: Using uv (Windows)

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
        "ENABLE_AI": "true"
      }
    }
  }
}
```

### Step 4: Verify Configuration

1. **Test the command manually:**
   ```powershell
   # For pipx installation
   git-commit-mcp --help
   
   # For local development
   cd C:\Users\suraj\MyWork\mcp_servers\git_commit_message
   python -m git_commit_mcp.__main__
   ```

2. **Restart Cursor completely** (close all windows)

3. **Check Cursor's Output Panel:**
   - Open View → Output
   - Select "MCP" or "Claude Dev" from dropdown
   - Look for any error messages

## Common Issues and Solutions

### Issue 1: Red Status Indicator / Server Not Connecting

**Symptoms:** Server shows red status in Cursor but works fine in terminal

**Solutions:**

1. **Rename the server** to avoid cache issues:
   ```json
   {
     "mcpServers": {
       "git-commit-mcp-local": {  // Changed name
         ...
       }
     }
   }
   ```

2. **Use full Python path** if `python` isn't found:
   ```json
   {
     "command": "C:\\Python\\python.exe",  // Use full path
     ...
   }
   ```

3. **Check PATH environment variable:**
   Add Python to PATH in the config:
   ```json
   {
     "env": {
       "PATH": "C:\\Python;C:\\Python\\Scripts;%PATH%",
       ...
     }
   }
   ```

### Issue 2: "Command not found" Error

**Solution:** Use absolute paths for all executables:

```json
{
  "command": "C:\\Users\\YourUser\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
  ...
}
```

Or install globally with pipx:
```powershell
pipx install git-commit-mcp-server
```

### Issue 3: "Module not found" Error

**Solution:** Ensure dependencies are installed:

```powershell
cd C:\Users\suraj\MyWork\mcp_servers\git_commit_message
pip install -e ".[dev]"
```

Or with uv:
```powershell
uv pip install -e ".[dev]"
```

### Issue 4: Configuration File Not Found

**Solution:** Create the directory structure manually:

```powershell
$basePath = "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings"
New-Item -ItemType Directory -Force -Path $basePath
```

### Issue 5: JSON Syntax Errors

**Common mistakes:**
- Trailing commas (not allowed in JSON)
- Single quotes instead of double quotes
- Incorrect path escaping

**Solution:** Use a JSON validator or check the file with:
```powershell
Get-Content "$env:APPDATA\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json" | ConvertFrom-Json
```

## Verification Checklist

- [ ] Configuration file exists at correct location
- [ ] JSON syntax is valid (no trailing commas, proper quotes)
- [ ] Paths use double backslashes (`\\`) or forward slashes (`/`)
- [ ] Python executable is accessible (test with `python --version`)
- [ ] Dependencies are installed (test with `python -m git_commit_mcp.__main__`)
- [ ] Environment variables are set correctly
- [ ] Cursor has been restarted after configuration changes
- [ ] Checked Cursor's Output panel for error messages

## Testing the Setup

Once configured, test the server:

1. Open a Git repository in Cursor
2. Make some changes
3. Ask Cursor's AI: "Commit my changes"
4. The AI should use the MCP server to generate and create a commit

## Getting Help

If issues persist:

1. Check the detailed troubleshooting section in [`docs/usage.md`](usage.md#cursor-ide-specific-issues)
2. Review Cursor's Output panel for specific error messages
3. Verify the server works outside Cursor (terminal test)
4. Try renaming the server to avoid cache issues
5. Consider using pipx installation instead of local development mode

## Additional Resources

- [Full Usage Documentation](usage.md)
- [Architecture Overview](architecture.md)
- [Main README](../README.md)

