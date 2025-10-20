"""Unit tests for CommitMessageGenerator component."""

import pytest
from unittest.mock import Mock
from git import Repo

from git_commit_mcp.message_generator import CommitMessageGenerator
from git_commit_mcp.models import ChangeSet


class TestCommitMessageGenerator:
    """Tests for CommitMessageGenerator component."""
    
    @pytest.fixture
    def generator(self):
        """Create a CommitMessageGenerator instance for testing."""
        return CommitMessageGenerator()
    
    @pytest.fixture
    def mock_repo(self):
        """Create a mock Git repository."""
        return Mock(spec=Repo)
    
    # Type Detection Tests
    
    def test_detect_commit_type_feat_for_new_source_files(self, generator):
        """Test that new files in source directories are detected as 'feat'."""
        changes = ChangeSet(added=['src/auth/login.py', 'src/auth/register.py'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'feat'
    
    def test_detect_commit_type_docs_for_markdown_files(self, generator):
        """Test that markdown files are detected as 'docs'."""
        changes = ChangeSet(modified=['README.md', 'docs/api.md'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'docs'
    
    def test_detect_commit_type_test_for_test_files(self, generator):
        """Test that test files are detected as 'test'."""
        changes = ChangeSet(modified=['tests/test_auth.py', 'tests/test_user.py'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'test'
    
    def test_detect_commit_type_chore_for_config_files(self, generator):
        """Test that configuration files are detected as 'chore'."""
        changes = ChangeSet(modified=['pyproject.toml', 'package.json'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'chore'
    
    def test_detect_commit_type_style_for_css_files(self, generator):
        """Test that CSS files are detected as 'style'."""
        changes = ChangeSet(modified=['styles/main.css', 'assets/theme.scss'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'style'
    
    def test_detect_commit_type_refactor_for_modifications_only(self, generator):
        """Test that only modifications without additions are detected as 'refactor'."""
        changes = ChangeSet(modified=['src/utils.py', 'src/helpers.py'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'refactor'
    
    def test_detect_commit_type_refactor_for_unknown_modifications(self, generator):
        """Test that unknown file modifications are detected as 'refactor'."""
        changes = ChangeSet(modified=['random_file.xyz'])
        commit_type = generator._detect_commit_type(changes)
        assert commit_type == 'refactor'
    
    # Scope Extraction Tests
    
    def test_extract_scope_from_single_directory(self, generator):
        """Test scope extraction from a single directory."""
        changes = ChangeSet(modified=['auth/login.py', 'auth/register.py'])
        scope = generator._extract_scope(changes)
        assert scope == 'auth'
    
    def test_extract_scope_from_src_subdirectory(self, generator):
        """Test that scope is extracted from subdirectory when first dir is 'src'."""
        changes = ChangeSet(modified=['src/auth/login.py', 'src/auth/register.py'])
        scope = generator._extract_scope(changes)
        assert scope == 'auth'
    
    def test_extract_scope_returns_most_common(self, generator):
        """Test that the most common scope is returned when multiple exist."""
        changes = ChangeSet(
            modified=['src/auth/login.py', 'src/auth/register.py', 'src/user/profile.py']
        )
        scope = generator._extract_scope(changes)
        assert scope == 'auth'
    
    def test_extract_scope_returns_empty_for_root_files(self, generator):
        """Test that root-level files return empty scope."""
        changes = ChangeSet(modified=['README.md', 'setup.py'])
        scope = generator._extract_scope(changes)
        assert scope == ''
    
    def test_extract_scope_skips_test_directories(self, generator):
        """Test that test directories are skipped for scope extraction."""
        changes = ChangeSet(modified=['tests/test_auth.py', 'src/auth/login.py'])
        scope = generator._extract_scope(changes)
        assert scope == 'auth'
    
    def test_extract_scope_normalizes_underscores(self, generator):
        """Test that underscores in scope are converted to hyphens."""
        changes = ChangeSet(modified=['src/user_auth/login.py'])
        scope = generator._extract_scope(changes)
        assert scope == 'user-auth'
    
    # Bullet Point Generation Tests
    
    def test_generate_bullet_points_for_added_files(self, generator):
        """Test bullet point generation for added files."""
        changes = ChangeSet(added=['src/auth.py', 'src/user.py'])
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 2
        assert bullets[0] == '- Add auth.py'
        assert bullets[1] == '- Add user.py'
    
    def test_generate_bullet_points_for_deleted_files(self, generator):
        """Test bullet point generation for deleted files."""
        changes = ChangeSet(deleted=['src/old_auth.py', 'src/deprecated.py'])
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 2
        assert bullets[0] == '- Remove old_auth.py'
        assert bullets[1] == '- Remove deprecated.py'
    
    def test_generate_bullet_points_for_renamed_files(self, generator):
        """Test bullet point generation for renamed files."""
        changes = ChangeSet(renamed=[('src/old.py', 'src/new.py')])
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 1
        assert bullets[0] == '- Rename old.py to new.py'
    
    def test_generate_bullet_points_for_modified_files(self, generator):
        """Test bullet point generation for modified files."""
        changes = ChangeSet(modified=['src/auth.py', 'src/user.py'])
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 2
        assert bullets[0] == '- Update auth.py'
        assert bullets[1] == '- Update user.py'
    
    def test_generate_bullet_points_limits_to_max(self, generator):
        """Test that bullet points are limited to max_bullet_points (5 by default)."""
        changes = ChangeSet(
            added=['file1.py', 'file2.py', 'file3.py'],
            modified=['file4.py', 'file5.py', 'file6.py', 'file7.py']
        )
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 5
    
    def test_generate_bullet_points_respects_custom_max(self):
        """Test that custom max_bullet_points is respected."""
        generator = CommitMessageGenerator(max_bullet_points=3)
        changes = ChangeSet(added=['file1.py', 'file2.py', 'file3.py', 'file4.py'])
        bullets = generator._generate_bullet_points(changes)
        assert len(bullets) == 3
    
    def test_generate_bullet_points_prioritizes_added_over_modified(self, generator):
        """Test that added files are prioritized over modified files."""
        changes = ChangeSet(
            added=['new1.py', 'new2.py'],
            modified=['mod1.py', 'mod2.py']
        )
        bullets = generator._generate_bullet_points(changes)
        assert bullets[0] == '- Add new1.py'
        assert bullets[1] == '- Add new2.py'
    
    # Message Generation Tests
    
    def test_generate_message_with_scope(self, generator, mock_repo):
        """Test full message generation with scope."""
        changes = ChangeSet(added=['src/auth/login.py'])
        message = generator.generate_message(changes, mock_repo)
        
        assert message.startswith('feat(auth):')
        assert '- Add login.py' in message
    
    def test_generate_message_without_scope(self, generator, mock_repo):
        """Test full message generation without scope."""
        changes = ChangeSet(modified=['README.md'])
        message = generator.generate_message(changes, mock_repo)
        
        assert message.startswith('docs:')
        assert 'README.md' in message.lower() or 'documentation' in message.lower()
    
    def test_generate_message_includes_bullet_points(self, generator, mock_repo):
        """Test that generated message includes bullet points."""
        changes = ChangeSet(
            added=['file1.py', 'file2.py'],
            modified=['file3.py']
        )
        message = generator.generate_message(changes, mock_repo)
        
        assert '- Add file1.py' in message
        assert '- Add file2.py' in message
        assert '- Update file3.py' in message
    
    def test_generate_message_limits_summary_lines(self, mock_repo):
        """Test that summary is limited to max_summary_lines."""
        generator = CommitMessageGenerator(max_summary_lines=1)
        changes = ChangeSet(added=['src/auth/login.py'])
        message = generator.generate_message(changes, mock_repo)
        
        # Split by double newline to separate header from bullets
        parts = message.split('\n\n')
        header = parts[0]
        
        # Header should be a single line
        assert '\n' not in header
    
    def test_generate_message_format_structure(self, generator, mock_repo):
        """Test that message follows conventional commit format structure."""
        changes = ChangeSet(added=['src/auth/login.py', 'src/auth/register.py'])
        message = generator.generate_message(changes, mock_repo)
        
        lines = message.split('\n')
        
        # First line should be the header (type(scope): description)
        assert ':' in lines[0]
        
        # Should have an empty line before bullet points
        assert lines[1] == ''
        
        # Subsequent lines should be bullet points
        for line in lines[2:]:
            assert line.startswith('- ')
    
    def test_generate_message_with_mixed_changes(self, generator, mock_repo):
        """Test message generation with multiple types of changes."""
        changes = ChangeSet(
            added=['src/new_feature.py'],
            modified=['src/existing.py'],
            deleted=['src/old.py']
        )
        message = generator.generate_message(changes, mock_repo)
        
        # Should detect as feat due to new file in src
        assert message.startswith('feat')
        
        # Should include all change types in bullets
        assert '- Add new_feature.py' in message
        assert '- Remove old.py' in message
        assert '- Update existing.py' in message
