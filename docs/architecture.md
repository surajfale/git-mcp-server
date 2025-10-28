# Architecture — git-commit-mcp-server

This document describes the high-level architecture, major components, and data flows for the Git Commit MCP Server. It is intended to help contributors and AI coding agents understand how pieces fit together and where to make safe changes.

Core components

- `src/git_commit_mcp/server.py`
  - MCP entry points and orchestration. Exposes two MCP tools: `git_commit_and_push` and `generate_commit_message`.
  - Coordinates the end-to-end workflow: repository access -> change detection -> message generation -> staging/commit -> changelog update -> optional push.

- `src/git_commit_mcp/change_tracker.py`
  - Uses GitPython to detect modified, added, deleted, and renamed files (combines staged + unstaged diffs and untracked files).

- `src/git_commit_mcp/message_generator.py`
  - Heuristic Conventional Commit generator. Key areas to review when changing behavior:
    - `TYPE_PATTERNS` — file/path heuristics mapping to commit types (docs, test, chore, style)
    - `COMMIT_TYPE_PRIORITY` — priority ordering used when multiple types score equally
    - Scope extraction logic (skips `src/`, `lib/` prefixes and prefers first-level directories)

- `src/git_commit_mcp/ai_client.py`
  - Thin wrapper around the OpenAI SDK. Reads `OPENAI_API_KEY` from the environment and supports `ai_base_url` for OpenAI-compatible endpoints.
  - If absent or if the client raises, server falls back to `CommitMessageGenerator`.

- `src/git_commit_mcp/git_operations.py`
  - Stages files, creates commits, and pushes via GitPython. Follow its error-wrapping approach — methods raise `GitCommandError` or `InvalidGitRepositoryError` for the caller to handle.

- `src/git_commit_mcp/changelog_manager.py`
  - Manages `CHANGELOG.md`. Important flow: server writes a placeholder entry (placeholder hash), stages the file, commits, replaces placeholder hash with real hash, then amends the commit to include the updated changelog.

- `src/git_commit_mcp/repository_manager.py`
  - Responsible for cloning and reusing workspaces when operating on remote repositories. Uses `workspace_dir` from config.

- `src/git_commit_mcp/config.py`
  - Central configuration using `ServerConfig.from_env()` (reads environment variables and optionally a `.env` file if configured).

Data flow (typical `git_commit_and_push`)

1. Tool call (MCP) -> `git_commit_and_push` in `server.py`.
2. Determine whether `repository_path` is local or remote. If remote and allowed, clone into `workspace_dir` via `RepositoryManager`.
3. `ChangeTracker.get_changes(repo)` collects change lists.
4. `CommitMessageGenerator` or `AIClient` produces the commit message (AI preferred if enabled).
5. `ChangelogManager.update_changelog()` writes a placeholder entry and `git index add` adds it.
6. `GitOperationsManager.stage_changes()` stages all changed files.
7. `GitOperationsManager.create_commit()` creates the commit.
8. `ChangelogManager.replace_commit_hash()` swaps the placeholder hash, and the server amends the commit to include the updated `CHANGELOG.md`.
9. If `confirm_push` is true, `GitOperationsManager.push_to_remote()` pushes; changelog push status is updated when push succeeds.

Design rationale / important decisions

- Environment-driven configuration: `ServerConfig.from_env()` centralizes runtime configuration and enables running the server under different environments (MCP client, CI, local dev).
- AI fallback: AI generation is convenient but not required — the code intentionally falls back to deterministic heuristics so the tool remains usable offline or without a key.
- Changelog amend flow: to have `CHANGELOG.md` included in the same commit, a placeholder is written first and then replaced after commit — this is why the server stages and amends the commit.
- SSH-first remote handling: `FORCE_SSH_ONLY` is true by default; remote HTTPS URLs are rejected unless configured otherwise to avoid embedding credentials.

Files worth inspecting when changing behavior

- `server.py` — orchestration and error handling
- `message_generator.py` — commit type/scope heuristics
- `ai_client.py` — SDK usage and prompt shape
- `changelog_manager.py` — formatting and amend flow
- `git_operations.py` — staging/commit/push mechanics and error handling

Testing and examples

- Integration tests: `tests/test_integration.py` exercises end-to-end behavior including changelog updates.
- Unit tests for message logic: `tests/test_message_generator.py`.

If you plan to change APIs or the `CHANGELOG.md` format, update tests and the amend flow in `server.py` accordingly.
