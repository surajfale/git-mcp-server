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

- [-] 10. Implement configuration management for multi-mode deployment


  - [x] 10.1 Create configuration module in `config.py`



    - Write `ServerConfig` dataclass with all configuration fields (transport, HTTP, auth, TLS, repository, monitoring)
    - Implement `from_env()` class method to load configuration from environment variables
    - Add validation logic for configuration values (e.g., port ranges, file paths)
    - Support loading from `.env` file using python-dotenv
    - _Requirements: 6.1, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 10.2 Write unit tests for configuration










    - Create `tests/test_config.py` with tests for environment variable loading
    - Test configuration validation and error handling
    - _Requirements: 7.1, 7.5_

- [x] 11. Implement authentication and security layer




  - [x] 11.1 Create authentication module in `auth.py`


    - Write `TokenValidator` class for bearer token validation
    - Implement JWT token support with expiration checking
    - Write `verify_token()` function for FastAPI dependency injection
    - Add rate limiting logic (token bucket algorithm)
    - _Requirements: 6.3, 6.4_
  
  - [x] 11.2 Write unit tests for authentication






    - Create `tests/test_auth.py` with tests for token validation
    - Test JWT token generation and verification
    - Test rate limiting behavior
    - _Requirements: 6.3, 6.4_
-

- [ ] 12. Implement Repository Manager for remote Git access

  - [x] 12.1 Create RepositoryManager class in `repository_manager.py`



    - Write `get_or_clone_repository()` method to clone repos to workspace
    - Implement `get_local_repository()` method for existing local repos
    - Write `cleanup_workspace()` method to remove cloned repos
    - Implement `configure_ssh_key()` method for SSH authentication setup
    - Add support for HTTPS authentication with username/password and tokens
    - Implement workspace locking for concurrent access control
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  
  - [x] 12.2 Write unit tests for RepositoryManager






    - Create `tests/test_repository_manager.py` with mocked Git operations
    - Test repository cloning with SSH and HTTPS
    - Test workspace cleanup and locking
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 13. Implement HTTP/SSE transport layer




  - [x] 13.1 Create HTTP server in `http_server.py`


    - Initialize FastAPI application with CORS middleware
    - Implement `/health` endpoint for health checks
    - Implement `/mcp/tools/git_commit_and_push` POST endpoint with authentication
    - Implement `/mcp/sse` GET endpoint for Server-Sent Events
    - Add error handling middleware for consistent error responses
    - Integrate authentication dependency on protected endpoints
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.2, 7.3, 7.4, 9.2, 9.3, 9.5_
  
  - [x] 13.2 Create transport abstraction in `transport.py`


    - Write `TransportHandler` base class for transport abstraction
    - Implement `StdioTransport` class for local mode
    - Implement `HttpTransport` class for remote mode
    - Add transport factory function to select appropriate transport
    - _Requirements: 6.1, 6.2, 6.5_
  
  - [x] 13.3 Write integration tests for HTTP server









    - Create `tests/test_http_server.py` with httpx test client
    - Test health check endpoint
    - Test authenticated and unauthenticated requests
    - Test CORS headers
    - Test SSE connection
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.2, 7.3_

- [x] 14. Update main server to support dual-mode operation



  - [x] 14.1 Refactor `server.py` for stdio mode


    - Extract core tool logic into reusable functions
    - Keep FastMCP integration for stdio transport
    - Ensure server can run independently in stdio mode
    - _Requirements: 6.5_
  
  - [x] 14.2 Create unified entry point in `__main__.py`


    - Write `main()` function that reads configuration
    - Implement mode selection logic (stdio vs http)
    - Call appropriate server runner based on transport mode
    - Add logging setup and error handling
    - _Requirements: 6.1, 6.5, 7.1, 7.5, 9.3_
  
  - [x] 14.3 Update tool implementation to work with both transports


    - Modify `git_commit_and_push` to work with RepositoryManager
    - Add support for remote repository URLs in addition to local paths
    - Ensure error handling works consistently across transports
    - _Requirements: 6.1, 6.5, 8.1, 8.5_

- [ ] 15. Create Docker containerization
  - [ ] 15.1 Write Dockerfile
    - Create multi-stage Dockerfile with Python 3.11 slim base
    - Install system dependencies (git, openssh-client)
    - Copy application code and install Python dependencies
    - Create non-root user for security
    - Set environment variables and expose port 8000
    - Define CMD to run server in HTTP mode
    - _Requirements: 9.1_
  
  - [ ] 15.2 Create docker-compose.yml
    - Define service configuration for local testing
    - Add environment variables for configuration
    - Mount volumes for SSH keys and workspace
    - Configure port mapping and restart policy
    - _Requirements: 9.1_
  
  - [ ] 15.3 Create .env.example file
    - Document all environment variables with descriptions
    - Provide example values for each configuration option
    - Include comments explaining usage
    - _Requirements: 7.1_

- [ ] 16. Create deployment configurations
  - [ ] 16.1 Create Kubernetes manifests in `deployment/kubernetes/`
    - Write `deployment.yaml` with container spec, resource limits, and environment variables
    - Write `service.yaml` for load balancer configuration
    - Write `ingress.yaml` for external access with TLS
    - Create `secrets.yaml.example` for sensitive configuration
    - _Requirements: 9.1, 9.2, 9.4_
  
  - [ ] 16.2 Create Cloud Run configuration in `deployment/cloud-run/`
    - Write `service.yaml` for Cloud Run deployment
    - Document deployment commands in README
    - _Requirements: 9.1, 9.2, 9.4_
  
  - [ ] 16.3 Create systemd service in `deployment/systemd/`
    - Write `git-commit-mcp.service` unit file
    - Document installation and setup instructions
    - _Requirements: 9.1_

- [ ] 17. Update documentation for remote hosting
  - [ ] 17.1 Update README.md with deployment guides
    - Add "Deployment" section with overview of options
    - Document Docker deployment with examples
    - Document Cloud Run deployment steps
    - Document Kubernetes deployment steps
    - Document VPS deployment with systemd
    - Add client configuration examples for both modes
    - _Requirements: All remote hosting requirements_
  
  - [ ] 17.2 Create deployment troubleshooting guide
    - Document common deployment issues and solutions
    - Add authentication troubleshooting steps
    - Include network and firewall configuration tips
    - _Requirements: 6.3, 6.4, 7.5, 8.4_
  
  - [ ]* 17.3 Add API documentation
    - Document HTTP endpoints with request/response examples
    - Add authentication header format
    - Include error response formats
    - _Requirements: 6.1, 6.2, 6.3_

- [ ]* 18. Add monitoring and observability
  - [ ]* 18.1 Implement metrics endpoint
    - Add `/metrics` endpoint with Prometheus-compatible metrics
    - Track request counts, latencies, and error rates
    - Track Git operation metrics (commits, pushes, failures)
    - _Requirements: 9.5_
  
  - [ ]* 18.2 Enhance logging
    - Add structured logging with JSON format
    - Include request IDs for tracing
    - Log all Git operations with outcomes
    - Add audit logging for security events
    - _Requirements: 9.3_

- [ ]* 19. Performance optimization and testing
  - [ ]* 19.1 Implement repository caching
    - Add caching layer for cloned repositories
    - Implement TTL-based cache eviction
    - Add cache warming for frequently accessed repos
    - _Requirements: 8.5, 9.4_
  
  - [ ]* 19.2 Add load testing
    - Create load test scripts using locust or k6
    - Test concurrent client connections
    - Measure performance under load
    - _Requirements: 7.4_
  
  - [ ]* 19.3 Add end-to-end remote deployment tests
    - Test Docker container deployment
    - Test authentication flow
    - Test remote repository access
    - Verify health checks and metrics
    - _Requirements: All remote hosting requirements_
