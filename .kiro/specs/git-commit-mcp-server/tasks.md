# Implementation Plan

- [x] 1. Set up project structure and dependencies




  - Create directory structure: `src/git_commit_mcp/` with `__init__.py`, `server.py`, `models.py`, `change_tracker.py`, `message_generator.py`, `git_operations.py`, `changelog_manager.py`
  - Create `pyproject.toml` with project metadata and dependencies (fastmcp, gitpython)
  - Create `README.md` with installation and usage instructions
  - _Requirements: All requirements depend on proper project setup_

- [x] 2. Implement data models and configuration




  - [x] 2.1 Create data models in `models.py`


    - Write `ChangeSet` dataclass with fields for modified, added, deleted, and renamed files
    - Write `CommitResult` dataclass for tool response structure
    - Write `ServerConfig` dataclass for configuration settings
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [x] 2.2 Write unit tests for data models






    - Create `tests/test_models.py` with tests for ChangeSet methods (is_empty, total_files)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Implement Change Tracker component






  - [x] 3.1 Create ChangeTracker class in `change_tracker.py`



    - Write `get_changes()` method that uses GitPython to detect modified files via `repo.index.diff(None)`
    - Implement logic to identify added files using `repo.untracked_files`
    - Implement logic to identify deleted files from diff output
    - Implement logic to identify renamed files
    - Return populated ChangeSet object
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 3.2 Write unit tests for ChangeTracker





    - Create `tests/test_change_tracker.py` with mock repository tests
    - Test scenarios: modified only, added only, deleted only, mixed changes, no changes
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. Implement Commit Message Generator component




  - [x] 4.1 Create CommitMessageGenerator class in `message_generator.py`


    - Write `_detect_commit_type()` method that analyzes file paths to determine type (feat, fix, docs, chore, etc.)
    - Write `_extract_scope()` method that extracts scope from directory structure
    - Write `_generate_bullet_points()` method that creates up to 5 bullet points from changes
    - Write `generate_message()` method that combines type, scope, and bullets into conventional commit format
    - Ensure summary is limited to 2 lines maximum
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  -

  - [x] 4.2 Write unit tests for CommitMessageGenerator





    - Create `tests/test_message_generator.py` with tests for type detection, scope extraction, and message formatting
    - Test bullet point limiting to 5 items
    - Test summary line limiting to 2 lines
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Implement Git Operations Manager component




  - [x] 5.1 Create GitOperationsManager class in `git_operations.py`


    - Write `stage_changes()` method using `repo.index.add()` to stage files from ChangeSet
    - Write `create_commit()` method using `repo.index.commit()` to create commit with message
    - Write `get_current_branch()` method to retrieve active branch name
    - Write `push_to_remote()` method using `repo.remote().push()` to push to remote
    - Implement error handling for each operation (InvalidGitRepositoryError, GitCommandError)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.2, 4.4, 4.5_
  

  - [x] 5.2 Write unit tests for GitOperationsManager









    - Create `tests/test_git_operations.py` with mocked GitPython operations
    - Test staging, committing, and pushing with success and failure scenarios
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.2, 4.4, 4.5_

- [x] 6. Implement Changelog Manager component




  - [x] 6.1 Create ChangelogManager class in `changelog_manager.py`


    - Write `create_changelog_if_missing()` method that creates CHANGELOG.md with template headers
    - Write `update_changelog()` method that appends new entry with timestamp, commit hash, message, and push status
    - Implement logic to insert entries after "## [Unreleased]" section in reverse chronological order
    - Format entries with date, short hash, push status indicator ([PUSHED] or [LOCAL])
    - Handle file I/O errors gracefully
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  -

  - [x] 6.2 Write unit tests for ChangelogManager










    - Create `tests/test_changelog_manager.py` with tests for file creation and entry appending
    - Test format consistency and chronological ordering
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 7. Implement main MCP server with tool integration




  - [x] 7.1 Create FastMCP server in `server.py`


    - Initialize FastMCP instance with server name "git-commit-server"
    - Define `git_commit_and_push` tool with parameters: `repository_path` (optional, default "."), `confirm_push` (bool, default False)
    - Implement tool workflow: instantiate components, call ChangeTracker, generate message, stage and commit, handle push based on confirm_push flag, update changelog
    - Return CommitResult as dictionary with all required fields
    - Implement comprehensive error handling for all failure scenarios
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  
  - [x] 7.2 Add entry point configuration


    - Update `pyproject.toml` to include script entry point for running the server
    - Add `__main__.py` if needed for direct module execution
    - _Requirements: All requirements_

- [x] 8. Create documentation and examples





  - [x] 8.1 Write comprehensive README.md


    - Document installation instructions using uv/uvx
    - Provide MCP configuration example for mcp.json
    - Include usage examples showing how AI assistants interact with the tool
    - Document the conventional commit format used
    - Add troubleshooting section for common issues
    - _Requirements: All requirements_
  

  - [x] 8.2 Add inline code documentation

    - Add docstrings to all classes and methods
    - Include type hints throughout the codebase
    - _Requirements: All requirements_
- [x] 9. Integration testing and validation




  - Create `tests/test_integration.py` with end-to-end workflow tests
  - Set up test Git repository fixture
  - Test complete workflow: make changes → invoke tool → verify commit → verify changelog
  - Test MCP protocol compliance
  - _Requirements: All requirements_

- [x] 10. Simplify configuration for stdio-only mode

  - [x] 10.1 Simplify configuration module in `config.py`
    - Simplified `ServerConfig` dataclass to stdio-only fields
    - Removed HTTP, auth, TLS, CORS settings
    - Kept essential fields: repo path, bullet points, changelog, workspace, Git credentials, logging
    - Implement `from_env()` class method to load configuration from environment variables
    - Add validation logic for configuration values
    - Support loading from `.env` file using python-dotenv
  
  - [x] 10.2 Write unit tests for configuration
    - Create `tests/test_config.py` with tests for environment variable loading
    - Test configuration validation and error handling

- [REMOVED] 11. Authentication and security layer (HTTP-only feature removed)

- [x] 12. Repository Manager for Git access

  - [x] 12.1 Create RepositoryManager class in `repository_manager.py`
    - Write `get_or_clone_repository()` method to clone repos to workspace
    - Implement `get_local_repository()` method for existing local repos
    - Write `cleanup_workspace()` method to remove cloned repos
    - Implement `configure_ssh_key()` method for SSH authentication setup
    - Add support for HTTPS authentication with username/password and tokens
    - Implement workspace locking for concurrent access control
  
  - [x] 12.2 Write unit tests for RepositoryManager
    - Create `tests/test_repository_manager.py` with mocked Git operations
    - Test repository cloning with SSH and HTTPS
    - Test workspace cleanup and locking

- [REMOVED] 13. HTTP/SSE transport layer (removed for stdio-only focus)

- [x] 14. Simplify main server for stdio-only operation

  - [x] 14.1 Keep `server.py` for stdio mode
    - Core tool logic in reusable functions
    - FastMCP integration for stdio transport
    - Server runs in stdio mode only
  
  - [x] 14.2 Simplify entry point in `__main__.py`
    - Write `main()` function that reads configuration
    - Removed mode selection logic (stdio only)
    - Call stdio server runner
    - Add logging setup and error handling
  
  - [x] 14.3 Tool implementation for stdio transport
    - `git_commit_and_push` works with RepositoryManager
    - Support for remote repository URLs in addition to local paths
    - Consistent error handling

- [REMOVED] 15. Docker containerization for Railway (removed)

- [REMOVED] 16. Railway deployment configuration (removed)

- [REMOVED] 17. Railway hosting documentation (removed)

- [x] 18. Prepare for PyPI publication

  - [x] 18.1 Update pyproject.toml for PyPI
    - Add proper metadata (author, license, keywords, classifiers)
    - Add project URLs (homepage, repository, issues, documentation)
    - Keep core dependencies (FastMCP, GitPython, python-dotenv)
    - _Requirements: 8.1, 8.2, 8.4_
  
  - [x] 18.2 Create LICENSE file
    - Add MIT license
    - _Requirements: 8.4_
  
  - [x] 18.3 Create MANIFEST.in
    - Include README.md, LICENSE, pyproject.toml
    - Include all source files
    - _Requirements: 8.1_
  
  - [x] 18.4 Build and validate package
    - Install build tools (build, twine)
    - Build distribution packages (wheel and sdist)
    - Verify package with twine check
    - Test installation with uvx
    - _Requirements: 8.1, 8.3, 8.5_
