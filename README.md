# Git Commit MCP Server

A small MCP (Model Context Protocol) server that automates conventional Git commits, changelog updates, and optional pushes. Use this repository when you want an AI assistant to create well-formed Conventional Commit messages and manage the CHANGELOG automatically.

See detailed documentation in the `docs/` folder:

- `docs/architecture.md` — high-level architecture, components, and data flows.
- `docs/usage.md` — setup, configuration, and common workflows (PowerShell examples included).

## Quick Start

### Prerequisites

- Python 3.10+
- Git installed and configured
- `uv` package manager (for development)
- `pipx` (for global installation)

### Installation

**Option 1: Global Installation with pipx (Recommended)**

Install globally so the server is available from any directory:

```powershell
# Install pipx if you don't have it
uv tool install pipx

# Install from PyPI (production)
pipx install git-commit-mcp-server

# Or install from TestPyPI (testing)
pipx install git-commit-mcp-server --index-url https://test.pypi.org/simple/ --pip-args="--extra-index-url https://pypi.org/simple/"
```

**Option 2: Run with uvx (No Installation)**

Run directly without installing:

```powershell
uvx git-commit-mcp-server
```

**Option 3: Development Mode**

For local development:

```powershell
# Clone the repository
git clone https://github.com/surajfale/git-mcp-server.git
cd git-mcp-server

# Install with development dependencies
uv pip install -e ".[dev]"

# Run the server
python -m git_commit_mcp.__main__
```

## Configuration

### MCP Client Setup

Add to your MCP configuration file (`.kiro/settings/mcp.json` or `~/.kiro/settings/mcp.json`):

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

### Environment Variables

Key environment variables:

- `OPENAI_API_KEY` — Required when `ENABLE_AI=true` for AI-powered commit messages
- `ENABLE_AI` — Set to `true` to use AI generation (default: `true`)
- `AI_MODEL` — OpenAI model to use (default: `gpt-4o-mini`)
- `FORCE_SSH_ONLY` — Require SSH for Git operations (default: `true`)
- `LOG_LEVEL` — Logging level: DEBUG, INFO, WARNING, ERROR (default: `INFO`)

**Set in PowerShell:**

```powershell
# Current session
$env:OPENAI_API_KEY = 'sk-your-key-here'

# Persistent (user-level)
setx OPENAI_API_KEY "sk-your-key-here"
```

## Usage

Once configured, use natural language with your AI assistant:

```
User: "Commit my changes"
AI: [Analyzes your git diff and generates a conventional commit message]
AI: "Created commit abc1234: feat(auth): Add user authentication module"

User: "Commit and push"
AI: [Commits and pushes to remote]
AI: "Successfully pushed to origin/main"
```

The server provides two main tools:
- `generate_commit_message` — Generate a commit message without committing
- `git_commit_and_push` — Full workflow: analyze, commit, and optionally push

## Features

- **AI-Powered Messages**: Analyzes actual git diffs to generate accurate commit messages
- **Conventional Commits**: Follows the Conventional Commits specification
- **Smart Type Detection**: Automatically determines commit type (feat, fix, docs, etc.)
- **Changelog Management**: Maintains CHANGELOG.md with commit history
- **Push Confirmation**: Requires explicit approval before pushing
- **Multi-Repository**: Works with any Git repository, local or remote

## Testing

Run the test suite:

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=git_commit_mcp

# Run specific tests
pytest tests/test_integration.py -v
```

## Updating

Update to the latest version:

```powershell
# Update global installation
pipx upgrade git-commit-mcp-server

# Or from TestPyPI
pipx upgrade git-commit-mcp-server --index-url https://test.pypi.org/simple/ --pip-args="--extra-index-url https://pypi.org/simple/"
```

## Documentation

- **`docs/usage.md`** — Detailed setup, configuration, troubleshooting, and best practices
- **`docs/architecture.md`** — System architecture, components, and design decisions

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Links

- **Repository**: https://github.com/surajfale/git-mcp-server
- **Issues**: https://github.com/surajfale/git-mcp-server/issues
- **PyPI**: https://pypi.org/project/git-commit-mcp-server/
- **TestPyPI**: https://test.pypi.org/project/git-commit-mcp-server/
