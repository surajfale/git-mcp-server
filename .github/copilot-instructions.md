<!--
Guidance for AI coding agents working on the git-commit-mcp-server repo.
Keep this short, actionable, and codebase-specific. Do not repeat generic advice.
-->
# Copilot / AI agent instructions — git-commit-mcp-server

Overview
- This project is an MCP server that automates conventional Git commits. The runtime entry points live in `src/git_commit_mcp/server.py` and `src/git_commit_mcp/__main__.py`.
- High-level components:
  - `server.py`: MCP tool definitions and orchestration (uses FastMCP). Key functions: `git_commit_and_push` and `generate_commit_message`.
  - `change_tracker.py`: Detects added/modified/deleted/renamed files with GitPython.
  - `message_generator.py`: Heuristics-based Conventional Commit generator (types, scope, bullets). Look at `TYPE_PATTERNS` and `COMMIT_TYPE_PRIORITY` for rules.
  - `ai_client.py`: Thin OpenAI wrapper; reads `OPENAI_API_KEY` from the environment and supports `ai_base_url` for OpenAI-compatible endpoints.
  - `git_operations.py`: Stages, commits, and pushes using GitPython; follow its error handling for expected failure modes.
  - `changelog_manager.py`: Writes a `CHANGELOG.md` entry before the commit (placeholder hash) then replaces it after commit (amend flow).

Important conventions & behaviors (do not change without updating callers)
- Configuration is read from environment variables via `ServerConfig.from_env()` (see `src/git_commit_mcp/config.py`). Examples: `ENABLE_AI`, `OPENAI_API_KEY`, `AI_PROVIDER`, `AI_MODEL`, `WORKSPACE_DIR`, `FORCE_SSH_ONLY`.
- AI usage:
  - If `ENABLE_AI=true` the code will instantiate `AIClient` which requires `OPENAI_API_KEY` in the process environment. If the key is missing, AI calls raise a clear error and the code falls back to the heuristic generator.
  - To test AI locally, export `$env:OPENAI_API_KEY = "sk-..."` in PowerShell before launching the server/process.
- Remote repo handling: remote URLs must use SSH by default when `FORCE_SSH_ONLY` is true. When working with remote repos, `RepositoryManager` clones into `WORKSPACE_DIR`.
- Changelog update flow: the server writes a placeholder entry, stages CHANGELOG.md, creates the commit, replaces the placeholder with the real hash, then amends the commit to include the updated CHANGELOG. Changelog errors are non-fatal; commits still succeed.

Developer workflows (commands you can run)
- Run tests: `pytest` (project uses standard pytest tests under `tests/`).
- Run the server locally (stdio MCP transport):
  - Development: `uv run python -m git_commit_mcp.server` (or `python -m git_commit_mcp.__main__`)
  - Production (uvx): `uvx git-commit-mcp-server`
- Quick environment setup (PowerShell):
  ```powershell
  # temporary for current shell
  $env:OPENAI_API_KEY = 'sk-REPLACE'
  # run server in same shell so it inherits env
  uvx git-commit-mcp-server
  ```

Patterns & heuristics to preserve
- Commit type detection: see `CommitMessageGenerator._detect_commit_type` — it uses `TYPE_PATTERNS`, file extension and path heuristics, and counts to prioritize types. When adding new file categories, update `TYPE_PATTERNS` and unit tests.
- Scope extraction: the scope is inferred from first-level directories but skips common prefixes like `src/` or `lib/`. Keep this behaviour if you change message structure.
- Message generation fallback: AI is preferred but any AI failure must gracefully fall back to `CommitMessageGenerator`.

Integration points & dependencies
- FastMCP: MCP server framework; tools are declared with `@mcp.tool()` in `server.py`.
- GitPython: used across change detection and Git operations. Use `Repo` objects passed around — do not re-instantiate unexpectedly.
- OpenAI SDK: optional; code expects the `openai` package and environment key. The config supports `ai_base_url` for alternate endpoints.

Where to look for examples and tests
- End-to-end behavior: `tests/test_integration.py`.
- Message logic: `tests/test_message_generator.py` and `src/git_commit_mcp/message_generator.py`.
- Change detection: `tests/test_change_tracker.py` and `src/git_commit_mcp/change_tracker.py`.

How to modify safely
- Add unit tests for any behavioral change (message generation, changelog format, git ops). Use mocks for GitPython when possible.
- If you change how the changelog is written (format or placeholders), update both `ChangelogManager` and the amend flow in `server.py`.
- If you alter configuration keys, update `ServerConfig.from_env()` and the README configuration section.

If uncertain, ask for these facts before making edits:
- Should remote repo handling keep `FORCE_SSH_ONLY` enforcement?
- Should CHANGELOG.md format (timestamps, status tags) change? Other systems parse this file.
- Are there external MCP clients that rely on exact tool names or return shapes? (`git_commit_and_push`, `generate_commit_message`)

End of instructions
