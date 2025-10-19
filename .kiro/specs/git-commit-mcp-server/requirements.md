# Requirements Document

## Introduction

This document specifies the requirements for a Model Context Protocol (MCP) server that automates Git commit workflows. The server will track changes, generate conventional commit messages, handle commits, manage push operations with user confirmation, and maintain a changelog file.

## Glossary

- **MCP Server**: The Model Context Protocol server application that provides Git commit automation tools
- **Conventional Commit**: A commit message format following the Conventional Commits specification (type(scope): description)
- **Change Tracker**: The component that identifies modified, added, and deleted files since the last commit
- **Commit Message Generator**: The component that creates structured commit messages based on detected changes
- **Changelog Manager**: The component that maintains the CHANGELOG.md file with commit history
- **User Confirmation**: An interactive prompt requiring explicit user approval before executing push operations

## Requirements

### Requirement 1

**User Story:** As a developer, I want the MCP server to automatically track all changes since the last commit, so that I don't have to manually identify modified files.

#### Acceptance Criteria

1. WHEN the user invokes the commit tool, THE Change Tracker SHALL identify all modified files in the working directory
2. WHEN the user invokes the commit tool, THE Change Tracker SHALL identify all newly added files in the working directory
3. WHEN the user invokes the commit tool, THE Change Tracker SHALL identify all deleted files in the working directory
4. WHEN the user invokes the commit tool, THE Change Tracker SHALL compare the current state against the last commit reference
5. WHEN no changes exist since the last commit, THE MCP Server SHALL return a message indicating no changes to commit

### Requirement 2

**User Story:** As a developer, I want the system to generate conventional commit messages automatically, so that my commit history follows consistent formatting standards.

#### Acceptance Criteria

1. WHEN changes are detected, THE Commit Message Generator SHALL create a commit message following the conventional commit format
2. WHEN generating the commit message, THE Commit Message Generator SHALL limit the summary to a maximum of 2 lines
3. WHEN generating the commit message, THE Commit Message Generator SHALL include a maximum of 5 bullet points describing the changes
4. WHEN generating the commit message, THE Commit Message Generator SHALL analyze file changes to determine the appropriate commit type (feat, fix, chore, docs, etc.)
5. WHEN multiple change types exist, THE Commit Message Generator SHALL select the most significant type as the primary commit type

### Requirement 3

**User Story:** As a developer, I want the system to commit all tracked changes automatically, so that I can streamline my commit workflow.

#### Acceptance Criteria

1. WHEN a commit message is generated, THE MCP Server SHALL stage all tracked changes using git add
2. WHEN changes are staged, THE MCP Server SHALL create a commit with the generated message
3. WHEN the commit operation fails, THE MCP Server SHALL return an error message with the failure reason
4. WHEN the commit succeeds, THE MCP Server SHALL return the commit hash and summary
5. WHEN untracked files exist, THE MCP Server SHALL exclude them from the commit operation

### Requirement 4

**User Story:** As a developer, I want to approve push operations before they execute, so that I maintain control over what gets pushed to the remote repository.

#### Acceptance Criteria

1. WHEN a commit is created successfully, THE MCP Server SHALL prompt the user for push confirmation
2. WHEN the user approves the push, THE MCP Server SHALL execute git push to the current branch
3. WHEN the user declines the push, THE MCP Server SHALL skip the push operation and notify the user
4. WHEN the push operation fails, THE MCP Server SHALL return an error message with the failure reason
5. WHEN the push succeeds, THE MCP Server SHALL return a confirmation message with the branch name

### Requirement 5

**User Story:** As a developer, I want the system to maintain a changelog file automatically, so that I have a readable history of all commits and pushes.

#### Acceptance Criteria

1. WHEN a commit is created, THE Changelog Manager SHALL append an entry to the CHANGELOG.md file
2. WHEN creating a changelog entry, THE Changelog Manager SHALL include the commit date and time
3. WHEN creating a changelog entry, THE Changelog Manager SHALL include the commit hash
4. WHEN creating a changelog entry, THE Changelog Manager SHALL include the commit message
5. WHEN creating a changelog entry, THE Changelog Manager SHALL indicate whether the commit was pushed to remote
6. WHEN the CHANGELOG.md file does not exist, THE Changelog Manager SHALL create it with appropriate headers
7. WHEN appending to CHANGELOG.md, THE Changelog Manager SHALL maintain reverse chronological order (newest first)
