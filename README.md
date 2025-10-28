# Git Commit MCP Server

A small MCP (Model Context Protocol) server that automates conventional Git commits, changelog updates, and optional pushes. Use this repository when you want an AI assistant to create well-formed Conventional Commit messages and manage the CHANGELOG automatically.

See detailed documentation in the `docs/` folder:

- `docs/architecture.md` — high-level architecture, components, and data flows.
- `docs/usage.md` — setup, configuration, and common workflows (PowerShell examples included).

Quick start

1. Ensure Python 3.10+ and Git are installed.
2. Install and run via uvx (recommended):

```powershell
uvx git-commit-mcp-server
```

3. For development, run the server locally:

```powershell
uv run python -m git_commit_mcp.server
# or
python -m git_commit_mcp.__main__
```

Environment variables

- `OPENAI_API_KEY` — required if `ENABLE_AI=true` (used by `AIClient`). Set it in PowerShell for the current shell:

```powershell
$env:OPENAI_API_KEY = 'sk-REPLACE'
```

Testing

Run the unit test suite with pytest:

```powershell
pytest -q
```

More

Read `docs/usage.md` for MCP client configuration (Kiro example), persistent environment setups, and troubleshooting tips. Read `docs/architecture.md` for an overview of components and the reasons behind key design decisions.
