## Usage — git-commit-mcp-server

This page covers setup, configuration, and common usage patterns for running the MCP server locally or in production.

Prerequisites
- Python 3.10+
- Git installed and configured
- (Optional) `uv` / `uvx` for convenient distribution and execution

Env vars (important)
- `OPENAI_API_KEY` — required when `ENABLE_AI=true` (used by `AIClient`). The server reads this environment variable at process startup.
- `ENABLE_AI` — `true`/`false` to enable AI generation
- `AI_PROVIDER`, `AI_MODEL`, `AI_BASE_URL`, `AI_TEMPERATURE`, `AI_MAX_TOKENS` — AI-related overrides
- `WORKSPACE_DIR` — where remote repositories are cloned
- `FORCE_SSH_ONLY` — when `true`, remote HTTPS URLs are rejected; defaults to `true` in config

Setting the OpenAI key (PowerShell)

Set it for the current session (temporary):

```powershell
$env:OPENAI_API_KEY = 'sk-REPLACE'
```

Make it persistent (user-level):

```powershell
setx OPENAI_API_KEY "sk-REPLACE"
# restart shells to pick up the value
```

Running the server

- Production via uvx (recommended):

```powershell
uvx git-commit-mcp-server
```

- Development (run from the repo root):

```powershell
# install dev deps first (optional)
uv pip install -e ".[dev]"
uv run python -m git_commit_mcp.server
# or
python -m git_commit_mcp.__main__
```

Configuring your MCP client (Kiro + Copilot examples)

Add the server to your Kiro workspace `.kiro/settings/mcp.json` or your global settings file. The simple production example (uvx) looks like this:

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

If your Kiro/Copilot integration supports passing environment variables or an env-file to the launched MCP server, prefer injecting `OPENAI_API_KEY` there so the server process can read it at startup. Example (client-supported `env` key — client schema varies):

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uvx",
      "args": ["git-commit-mcp-server"],
      "disabled": false,
      "autoApprove": [],
      "env": {
        "OPENAI_API_KEY": "sk-REPLACE"
      }
    }
  }
}
```

Alternate approach: point the client to an env-file (if supported) so secrets are kept out of the repo:

```json
{
  "mcpServers": {
    "git-commit": {
      "command": "uvx",
      "args": ["git-commit-mcp-server"],
      "disabled": false,
      "autoApprove": [],
      "envFile": ".env"
    }
  }
}
```

Notes:
- `.kiro/settings/mcp.json` configures the client, not the server process environment by default — verify your client supports `env`/`envFile` fields before relying on them.
- If the client does not support env injection, start the server from a shell that has `$env:OPENAI_API_KEY` set, or use a separate process manager that injects the variable.

Use the provided `.env.example` as a starting point

This repository includes a `.env.example` at the project root with common settings. Do not commit real secrets — copy the file to an untracked `.env` and edit values, or point your MCP client at the example for local testing.

Example steps (PowerShell):

```powershell
# Copy example to local .env (one-time)
Copy-Item .env.example .env
# Edit the .env file in a safe location and set your real OPENAI_API_KEY
notepad .env
```

Contents of `.env.example` (keys shown):

```
OPENAI_API_KEY=sk-REPLACE
ENABLE_AI=true
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
WORKSPACE_DIR=/tmp/git-workspaces
FORCE_SSH_ONLY=true
```

Generating messages and committing

- Generate only a commit message (no commit): call the MCP tool `generate_commit_message` with `repository_path` (defaults to `.`).
- Commit (local) with generated message: call `git_commit_and_push` with `repository_path` (defaults to `.`) and `confirm_push=false`.
- Commit and push: call `git_commit_and_push` with `confirm_push=true` (the tool will push the current branch to the default remote).

Testing

- Run unit tests:

```powershell
pytest
```

- Integration tests cover cloning, message generation, changelog updates. Inspect `tests/test_integration.py`.

Troubleshooting

- "OPENAI_API_KEY is not set": start the server from a shell where `$env:OPENAI_API_KEY` is set.
- "Not a git repository": ensure `repository_path` points to a Git repo or pass an SSH remote URL (if `FORCE_SSH_ONLY=true`).
- Changelog write failures are non-fatal — commits will still be created.

Advanced: Loading .env automatically

`ServerConfig.from_env()` supports loading a `.env` file if you modify the invocation to pass `env_file` (or install `python-dotenv` and update `src/git_commit_mcp/__main__.py` to call `ServerConfig.from_env(env_file='.env')`). This repository does not auto-load `.env` by default to avoid surprising behavior in production.
