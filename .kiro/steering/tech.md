# Technology Stack

## Build System & Package Manager

- **Package Manager**: `uv` (modern Python package manager)
- **Build Backend**: Hatchling
- **Python Version**: >=3.10

## Core Dependencies

- **FastMCP** (>=0.1.0): MCP server framework
- **GitPython** (>=3.1.0): Git operations and repository management

## Installation & Setup

```bash
# Install dependencies
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"
```

## Running the Server

```bash
# Run via entry point
git-commit-mcp

# Run as module (for development)
uv run python -m git_commit_mcp.server

# Run with uvx (recommended for users)
uvx git-commit-mcp-server
```

## Testing

```bash
# Run tests
pytest
```

## Distribution

The package is distributed via PyPI and can be run directly with `uvx` without manual installation.
