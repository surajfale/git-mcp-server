# Git Commit MCP Server - Architecture Flow

## End-to-End Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant AI as AI Assistant (Kiro)
    participant MCP as MCP Server
    participant CT as Change Tracker
    participant MG as Message Generator
    participant GO as Git Operations
    participant CL as Changelog Manager
    participant Git as Git Repository

    User->>AI: "Commit my changes"
    AI->>MCP: Call git_commit_and_push(repository_path=".", confirm_push=false)
    
    Note over MCP: Workflow starts
    
    MCP->>CT: get_changes(repo)
    CT->>Git: Check git status
    Git-->>CT: Modified, Added, Deleted files
    CT-->>MCP: ChangeSet{modified, added, deleted, renamed}
    
    alt No changes detected
        MCP-->>AI: {success: false, message: "No changes to commit"}
        AI-->>User: "No changes to commit"
    else Changes detected
        MCP->>MG: generate_message(changes)
        
        Note over MG: Analyze file paths
        MG->>MG: detect_commit_type()<br/>(feat, fix, docs, etc.)
        MG->>MG: extract_scope()<br/>(from directory structure)
        MG->>MG: generate_bullet_points()<br/>(max 5 points)
        
        MG-->>MCP: Conventional commit message
        
        MCP->>GO: stage_changes(repo, changes)
        GO->>Git: git add [files]
        Git-->>GO: Files staged
        
        MCP->>GO: create_commit(repo, message)
        GO->>Git: git commit -m "message"
        Git-->>GO: Commit hash (abc1234)
        GO-->>MCP: commit_hash
        
        MCP->>CL: update_changelog(hash, message, pushed=false)
        CL->>CL: Check if CHANGELOG.md exists
        
        alt CHANGELOG.md missing
            CL->>CL: create_changelog_if_missing()
        end
        
        CL->>CL: Format entry with timestamp, hash, [LOCAL]
        CL->>Git: Append to CHANGELOG.md
        Git-->>CL: File updated
        CL-->>MCP: changelog_updated=true
        
        MCP-->>AI: {success: true, commit_hash: "abc1234",<br/>commit_message: "...", files_changed: 3,<br/>pushed: false, changelog_updated: true}
        
        AI-->>User: "✅ Committed 3 files [abc1234]<br/>feat(auth): Add user authentication<br/><br/>Would you like to push to remote?"
        
        User->>AI: "Yes, push it"
        AI->>MCP: Call git_commit_and_push(confirm_push=true)
        
        Note over MCP: Push workflow
        
        MCP->>GO: get_current_branch(repo)
        GO->>Git: Get active branch
        Git-->>GO: "main"
        
        MCP->>GO: push_to_remote(repo)
        GO->>Git: git push origin main
        
        alt Push successful
            Git-->>GO: Push successful
            GO-->>MCP: PushResult{success: true}
            
            MCP->>CL: update_changelog(hash, message, pushed=true)
            CL->>Git: Update entry to [PUSHED]
            
            MCP-->>AI: {success: true, pushed: true,<br/>message: "Pushed to origin/main"}
            AI-->>User: "✅ Successfully pushed to origin/main!"
        else Push failed
            Git-->>GO: Error (auth/network/no remote)
            GO-->>MCP: PushResult{success: false, error: "..."}
            MCP-->>AI: {success: false, error: "Push failed: ..."}
            AI-->>User: "❌ Push failed: [error details]"
        end
    end
```

## Component Architecture

```mermaid
graph TB
    subgraph "AI Assistant (Kiro)"
        User[User Request]
        AI[AI Assistant]
    end
    
    subgraph "MCP Server"
        Server[server.py<br/>FastMCP Server]
        
        subgraph "Core Components"
            CT[Change Tracker<br/>change_tracker.py]
            MG[Message Generator<br/>message_generator.py]
            GO[Git Operations<br/>git_operations.py]
            CL[Changelog Manager<br/>changelog_manager.py]
        end
        
        Models[Data Models<br/>models.py<br/>ChangeSet, CommitResult]
    end
    
    subgraph "Git Repository"
        GitRepo[.git/]
        Files[Working Directory]
        Changelog[CHANGELOG.md]
    end
    
    User -->|"Commit my changes"| AI
    AI -->|MCP Protocol| Server
    
    Server --> CT
    Server --> MG
    Server --> GO
    Server --> CL
    
    CT -.->|uses| Models
    MG -.->|uses| Models
    GO -.->|uses| Models
    
    CT -->|reads| GitRepo
    GO -->|writes| GitRepo
    GO -->|writes| Files
    CL -->|writes| Changelog
    
    Server -->|response| AI
    AI -->|result| User
    
    style Server fill:#4A90E2
    style CT fill:#7ED321
    style MG fill:#F5A623
    style GO fill:#D0021B
    style CL fill:#BD10E0
```

## Commit Type Detection Logic

```mermaid
flowchart TD
    Start[Analyze File Changes] --> CheckPath{Check File Path}
    
    CheckPath -->|tests/, __tests__/| Test[Type: test]
    CheckPath -->|docs/, *.md| Docs[Type: docs]
    CheckPath -->|*.css, *.scss| Style[Type: style]
    CheckPath -->|config files| Chore[Type: chore]
    CheckPath -->|Other| CheckChange{Check Change Type}
    
    CheckChange -->|New files in src/| Feat[Type: feat]
    CheckChange -->|Modified files| CheckKeywords{Check for<br/>bug keywords}
    
    CheckKeywords -->|Bug-related| Fix[Type: fix]
    CheckKeywords -->|No additions| Refactor[Type: refactor]
    CheckKeywords -->|Other| DefaultFeat[Type: feat]
    
    Test --> Priority
    Docs --> Priority
    Style --> Priority
    Chore --> Priority
    Feat --> Priority
    Fix --> Priority
    Refactor --> Priority
    DefaultFeat --> Priority
    
    Priority[Apply Priority:<br/>feat > fix > docs > style<br/>> refactor > test > chore] --> Result[Selected Type]
    
    style Feat fill:#7ED321
    style Fix fill:#D0021B
    style Docs fill:#4A90E2
    style Test fill:#F5A623
    style Chore fill:#9013FE
```

## Changelog Update Flow

```mermaid
flowchart TD
    Start[Update Changelog] --> Exists{CHANGELOG.md<br/>exists?}
    
    Exists -->|No| Create[Create file with<br/>template headers]
    Exists -->|Yes| Read[Read existing content]
    
    Create --> Format
    Read --> Format[Format new entry]
    
    Format --> Entry["Entry Format:<br/>### YYYY-MM-DD HH:MM:SS - hash [STATUS]<br/><br/>commit message<br/><br/>- bullet points"]
    
    Entry --> Status{Pushed?}
    Status -->|Yes| Pushed["Status: [PUSHED]"]
    Status -->|No| Local["Status: [LOCAL]"]
    
    Pushed --> Insert
    Local --> Insert[Insert after<br/>'## [Unreleased]']
    
    Insert --> Write[Write to file]
    Write --> Done[✅ Changelog Updated]
    
    style Create fill:#7ED321
    style Format fill:#4A90E2
    style Write fill:#F5A623
    style Done fill:#7ED321
```

## Data Flow

```mermaid
graph LR
    subgraph Input
        RP[repository_path]
        CP[confirm_push]
    end
    
    subgraph Processing
        CS[ChangeSet<br/>modified: []<br/>added: []<br/>deleted: []<br/>renamed: []]
        
        CM[Commit Message<br/>type: feat<br/>scope: auth<br/>description: ...<br/>bullets: []]
        
        CR[CommitResult<br/>success: true<br/>commit_hash: abc1234<br/>files_changed: 3<br/>pushed: false<br/>changelog_updated: true]
    end
    
    subgraph Output
        Response[JSON Response<br/>to AI Assistant]
    end
    
    RP --> CS
    CS --> CM
    CM --> CR
    CP --> CR
    CR --> Response
    
    style CS fill:#4A90E2
    style CM fill:#F5A623
    style CR fill:#7ED321
```

## Error Handling Flow

```mermaid
flowchart TD
    Start[Operation] --> Try{Try Operation}
    
    Try -->|Success| Success[Return Success]
    Try -->|Error| CheckError{Error Type?}
    
    CheckError -->|Not a Git Repo| E1[Return: Not a git repository]
    CheckError -->|No Changes| E2[Return: No changes to commit]
    CheckError -->|Commit Failed| E3[Return: Commit failed + reason]
    CheckError -->|No Remote| E4[Return: No remote configured]
    CheckError -->|Auth Failed| E5[Return: Authentication failed]
    CheckError -->|Network Error| E6[Return: Network error, retry]
    CheckError -->|Changelog Error| E7[Log warning, continue]
    
    E1 --> ErrorResponse[Error Response<br/>to AI Assistant]
    E2 --> ErrorResponse
    E3 --> ErrorResponse
    E4 --> ErrorResponse
    E5 --> ErrorResponse
    E6 --> ErrorResponse
    E7 --> Success
    
    Success --> End[End]
    ErrorResponse --> End
    
    style Success fill:#7ED321
    style ErrorResponse fill:#D0021B
    style E7 fill:#F5A623
```

## Key Features Summary

### 1. **Change Detection**
- Scans working directory for all changes
- Categorizes: modified, added, deleted, renamed
- Excludes untracked files from auto-commit

### 2. **Smart Message Generation**
- Analyzes file paths and extensions
- Determines commit type automatically
- Extracts scope from directory structure
- Generates up to 5 descriptive bullet points
- Follows Conventional Commits specification

### 3. **Git Operations**
- Stages all tracked changes
- Creates commit with generated message
- Handles push with user confirmation
- Comprehensive error handling

### 4. **Changelog Management**
- Creates CHANGELOG.md if missing
- Appends entries in reverse chronological order
- Tracks push status ([PUSHED] vs [LOCAL])
- Maintains professional format

### 5. **MCP Integration**
- Exposes `git_commit_and_push` tool
- Returns structured JSON responses
- Enables natural language Git workflows
- Works with any MCP-compatible AI assistant

