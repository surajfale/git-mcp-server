"""Commit message generation component following Conventional Commits specification."""

from typing import List, Dict, Set
from pathlib import Path
from git import Repo

from git_commit_mcp.models import ChangeSet


class CommitMessageGenerator:
    """Generates conventional commit messages based on detected changes.
    
    This component analyzes file changes to determine the appropriate commit type,
    extract scope from directory structure, and create formatted commit messages
    following the Conventional Commits specification.
    """
    
    # Commit type priority (higher index = higher priority)
    COMMIT_TYPE_PRIORITY = ['chore', 'style', 'test', 'refactor', 'docs', 'fix', 'feat']
    
    # File patterns for commit type detection
    TYPE_PATTERNS = {
        'docs': {
            'extensions': {'.md', '.txt', '.rst', '.adoc'},
            'paths': {'docs/', 'doc/', 'documentation/'},
            'files': {'README.md', 'CHANGELOG.md', 'LICENSE', 'CONTRIBUTING.md'}
        },
        'test': {
            'extensions': set(),
            'paths': {'test/', 'tests/', '__tests__/', 'spec/', 'specs/'},
            'files': set()
        },
        'chore': {
            'extensions': {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'},
            'paths': {'.github/', '.gitlab/', 'config/', 'configs/'},
            'files': {'pyproject.toml', 'setup.py', 'package.json', 'Makefile', '.gitignore'}
        },
        'style': {
            'extensions': {'.css', '.scss', '.sass', '.less'},
            'paths': {'styles/', 'css/', 'assets/'},
            'files': set()
        }
    }
    
    def __init__(self, max_bullet_points: int = 5, max_summary_lines: int = 2):
        """Initialize the commit message generator.
        
        Args:
            max_bullet_points: Maximum number of bullet points to include
            max_summary_lines: Maximum number of lines for the summary
        """
        self.max_bullet_points = max_bullet_points
        self.max_summary_lines = max_summary_lines
    
    def generate_message(self, changes: ChangeSet, repo: Repo) -> str:
        """Generate a conventional commit message from detected changes.
        
        Creates a commit message with:
        - Commit type and optional scope
        - Short description (max 2 lines)
        - Bullet points describing changes (max 5)
        
        Args:
            changes: ChangeSet containing all file changes
            repo: GitPython Repo object for additional context
            
        Returns:
            Formatted conventional commit message
        """
        commit_type = self._detect_commit_type(changes)
        scope = self._extract_scope(changes)
        bullet_points = self._generate_bullet_points(changes)
        
        # Build the commit header
        if scope:
            header = f"{commit_type}({scope}): "
        else:
            header = f"{commit_type}: "
        
        # Create a short description based on the changes
        description = self._create_description(changes, commit_type, repo)
        
        # Ensure description fits within max_summary_lines
        description_lines = description.split('\n')
        if len(description_lines) > self.max_summary_lines:
            description_lines = description_lines[:self.max_summary_lines]
        description = '\n'.join(description_lines)
        
        # Build the full message
        message_parts = [header + description]
        
        # Add empty line before bullet points if they exist
        if bullet_points:
            message_parts.append('')
            message_parts.extend(bullet_points)
        
        return '\n'.join(message_parts)
    
    def _detect_commit_type(self, changes: ChangeSet) -> str:
        """Analyze file paths to determine the appropriate commit type.
        
        Determines commit type based on file patterns:
        - feat: New files in source directories
        - fix: Bug-related changes (heuristic-based)
        - docs: Documentation files
        - test: Test files
        - style: Style/CSS files
        - refactor: Modifications without new files
        - chore: Configuration and build files
        
        Args:
            changes: ChangeSet containing all file changes
            
        Returns:
            Commit type string (feat, fix, docs, chore, etc.)
        """
        type_scores: Dict[str, int] = {t: 0 for t in self.COMMIT_TYPE_PRIORITY}
        
        all_files = (
            changes.modified + 
            changes.added + 
            changes.deleted + 
            [new_path for _, new_path in changes.renamed]
        )
        
        for file_path in all_files:
            path_lower = file_path.lower()
            path_obj = Path(file_path)
            
            # Check against type patterns
            for commit_type, patterns in self.TYPE_PATTERNS.items():
                # Check file extensions
                if path_obj.suffix in patterns['extensions']:
                    type_scores[commit_type] += 1
                
                # Check path prefixes
                for path_prefix in patterns['paths']:
                    if path_lower.startswith(path_prefix) or f'/{path_prefix}' in path_lower:
                        type_scores[commit_type] += 2
                
                # Check specific filenames
                if path_obj.name in patterns['files']:
                    type_scores[commit_type] += 2
        
        # Special logic for feat vs refactor
        if changes.added:
            # New files in source directories suggest a feature
            for file_path in changes.added:
                path_lower = file_path.lower()
                if any(src in path_lower for src in ['src/', 'lib/', 'app/', 'core/']):
                    # Check if it's not a test or doc file
                    if not any(test in path_lower for test in ['test', 'spec', 'doc']):
                        type_scores['feat'] += 3
        
        # If only modifications and no additions, lean toward refactor
        if changes.modified and not changes.added and not changes.deleted:
            type_scores['refactor'] += 1
        
        # Deprioritize 'test' if there are significant source file changes
        source_file_changes = sum(1 for f in changes.modified + changes.added 
                                 if any(src in f.lower() for src in ['src/', 'lib/', 'app/']) 
                                 and 'test' not in f.lower())
        test_file_changes = sum(1 for f in changes.modified + changes.added 
                               if 'test' in f.lower())
        
        if source_file_changes > 0 and source_file_changes >= test_file_changes:
            # More or equal source changes than test changes
            # Reduce test score to let source changes determine the type
            type_scores['test'] = max(0, type_scores['test'] - 2)
        
        # Find the type with the highest score
        max_score = max(type_scores.values())
        
        if max_score == 0:
            # Default to chore if no patterns matched
            return 'chore'
        
        # Return the highest priority type with the max score
        for commit_type in reversed(self.COMMIT_TYPE_PRIORITY):
            if type_scores[commit_type] == max_score:
                return commit_type
        
        return 'chore'
    
    def _extract_scope(self, changes: ChangeSet) -> str:
        """Extract scope from directory structure.
        
        Analyzes file paths to determine a common scope:
        - Uses root-level directory names
        - Returns empty string if no clear scope
        - Prefers the most common directory among changes
        
        Args:
            changes: ChangeSet containing all file changes
            
        Returns:
            Scope string or empty string if unclear
        """
        all_files = (
            changes.modified + 
            changes.added + 
            changes.deleted + 
            [new_path for _, new_path in changes.renamed]
        )
        
        if not all_files:
            return ''
        
        # Extract first-level directories
        scopes: Dict[str, int] = {}
        
        for file_path in all_files:
            parts = Path(file_path).parts
            
            # Skip if file is in root
            if len(parts) <= 1:
                continue
            
            # Get the first directory (or second if first is 'src', 'lib', etc.)
            first_dir = parts[0]
            
            # If first directory is a common source directory, use the next level
            if first_dir in {'src', 'lib', 'app', 'core', 'pkg'} and len(parts) > 2:
                scope = parts[1]
            else:
                scope = first_dir
            
            # Skip common non-scope directories
            if scope in {'test', 'tests', 'docs', 'doc', '__pycache__', '.git'}:
                continue
            
            scopes[scope] = scopes.get(scope, 0) + 1
        
        if not scopes:
            return ''
        
        # Return the most common scope
        most_common_scope = max(scopes.items(), key=lambda x: x[1])[0]
        
        # Clean up the scope (remove special characters, make lowercase)
        most_common_scope = most_common_scope.replace('_', '-').replace(' ', '-').lower()
        
        return most_common_scope
    
    def _generate_bullet_points(self, changes: ChangeSet) -> List[str]:
        """Create bullet points describing the changes.
        
        Generates up to max_bullet_points bullet points with format:
        "Action verb + file/component + brief description"
        
        Priority:
        1. Added files (Add ...)
        2. Deleted files (Remove ...)
        3. Renamed files (Rename ... to ...)
        4. Modified files (Update ...)
        
        Args:
            changes: ChangeSet containing all file changes
            
        Returns:
            List of bullet point strings (with "- " prefix)
        """
        bullets: List[str] = []
        
        # Process added files
        for file_path in changes.added[:self.max_bullet_points]:
            file_name = Path(file_path).name
            bullets.append(f"- Add {file_name}")
            if len(bullets) >= self.max_bullet_points:
                return bullets
        
        # Process deleted files
        for file_path in changes.deleted:
            if len(bullets) >= self.max_bullet_points:
                break
            file_name = Path(file_path).name
            bullets.append(f"- Remove {file_name}")
        
        # Process renamed files
        for old_path, new_path in changes.renamed:
            if len(bullets) >= self.max_bullet_points:
                break
            old_name = Path(old_path).name
            new_name = Path(new_path).name
            bullets.append(f"- Rename {old_name} to {new_name}")
        
        # Process modified files
        for file_path in changes.modified:
            if len(bullets) >= self.max_bullet_points:
                break
            file_name = Path(file_path).name
            bullets.append(f"- Update {file_name}")
        
        return bullets
    
    def _analyze_diff_for_keywords(self, repo: Repo, changes: ChangeSet) -> List[str]:
        """Analyze diff content to extract meaningful keywords about what changed.
        
        Args:
            repo: GitPython Repo object
            changes: ChangeSet containing all file changes
            
        Returns:
            List of keywords found in the diff
        """
        keywords = []
        
        try:
            # Get the diff for staged changes
            diff_text = repo.git.diff('--cached', '--unified=0')
            
            # Look for common patterns that indicate what was changed
            patterns = {
                'caching': ['cache', 'cached', 'caching', 'ttl', 'evict'],
                'authentication': ['auth', 'token', 'credential', 'login', 'password'],
                'logging': ['log', 'logger', 'logging'],
                'configuration': ['config', 'setting', 'option'],
                'error handling': ['error', 'exception', 'try', 'catch', 'raise'],
                'testing': ['test', 'assert', 'mock', 'fixture'],
                'documentation': ['doc', 'readme', 'comment'],
                'API': ['endpoint', 'route', 'api', 'request', 'response'],
                'database': ['db', 'database', 'query', 'sql'],
                'performance': ['optimize', 'performance', 'speed', 'fast'],
                'security': ['security', 'secure', 'vulnerability', 'sanitize'],
                'validation': ['validate', 'validation', 'check', 'verify'],
                'refactoring': ['refactor', 'restructure', 'reorganize'],
                'bug fix': ['fix', 'bug', 'issue', 'problem', 'resolve'],
            }
            
            diff_lower = diff_text.lower()
            
            for keyword, terms in patterns.items():
                if any(term in diff_lower for term in terms):
                    keywords.append(keyword)
            
            # Look for function/class definitions to understand what was added
            if 'def ' in diff_text or 'class ' in diff_text:
                import re
                # Find new function/class names
                new_defs = re.findall(r'^\+.*?(?:def|class)\s+(\w+)', diff_text, re.MULTILINE)
                if new_defs:
                    # Take first few function/class names
                    keywords.extend(new_defs[:2])
            
        except Exception:
            # If diff analysis fails, return empty list
            pass
        
        return keywords[:3]  # Return top 3 keywords
    
    def _create_description(self, changes: ChangeSet, commit_type: str, repo: Repo) -> str:
        """Create a short description for the commit header.
        
        Generates a concise description based on the type and nature of changes.
        
        Args:
            changes: ChangeSet containing all file changes
            commit_type: The detected commit type
            repo: GitPython Repo object for diff analysis
            
        Returns:
            Short description string (1-2 lines)
        """
        total_files = changes.total_files()
        
        # Analyze diff for keywords
        keywords = self._analyze_diff_for_keywords(repo, changes)
        
        # Create type-specific descriptions with keywords
        if commit_type == 'feat':
            if keywords:
                # Use keywords to describe the feature
                keyword_str = ', '.join(keywords[:2])
                return f"Implement {keyword_str}"
            elif changes.added:
                # Focus on what was added
                first_file = Path(changes.added[0]).stem.replace('_', ' ').replace('-', ' ')
                if len(changes.added) == 1:
                    return f"Add {first_file}"
                else:
                    return f"Add {first_file} and {len(changes.added) - 1} more"
            return "Add new functionality"
        
        elif commit_type == 'fix':
            if keywords:
                keyword_str = ' '.join(keywords[:2])
                return f"Fix {keyword_str}"
            return f"Fix issues in {total_files} file{'s' if total_files != 1 else ''}"
        
        elif commit_type == 'docs':
            if keywords:
                return f"Update documentation for {keywords[0]}"
            return "Update documentation"
        
        elif commit_type == 'test':
            if keywords and 'testing' not in keywords:
                # Describe what's being tested
                return f"Add tests for {keywords[0]}"
            return "Update tests"
        
        elif commit_type == 'style':
            return "Update styles"
        
        elif commit_type == 'refactor':
            if keywords:
                keyword_str = ' and '.join(keywords[:2])
                return f"Refactor {keyword_str}"
            # Try to be more specific about what was refactored
            if changes.modified:
                file_names = [Path(f).stem.replace('_', ' ') for f in changes.modified[:2]]
                if len(file_names) == 1:
                    return f"Refactor {file_names[0]}"
                else:
                    return f"Refactor {file_names[0]} and {file_names[1]}"
            return f"Refactor {total_files} file{'s' if total_files != 1 else ''}"
        
        elif commit_type == 'chore':
            if any('package' in f.lower() or 'pyproject' in f.lower() for f in changes.modified + changes.added):
                return "Update dependencies"
            if keywords:
                return f"Update {keywords[0]}"
            return "Update configuration"
        
        # Default fallback with keywords if available
        if keywords:
            return f"Update {keywords[0]}"
        return f"Update {total_files} file{'s' if total_files != 1 else ''}"
