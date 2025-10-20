"""Repository manager for handling Git repository access and authentication."""

import hashlib
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal, Optional, Dict
from dataclasses import dataclass, field
from threading import Lock
from datetime import datetime, timedelta

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError


@dataclass
class GitCredentials:
    """Credentials for Git repository authentication.
    
    Attributes:
        auth_type: Type of authentication (ssh, https, or token)
        username: Username for HTTPS authentication
        password: Password for HTTPS authentication
        ssh_key: Path to SSH private key file
        token: Personal access token for HTTPS authentication
    """
    auth_type: Literal["ssh", "https", "token"]
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None
    token: Optional[str] = None
    
    def validate(self) -> None:
        """Validate that required credentials are provided for the auth type.
        
        Raises:
            ValueError: If required credentials are missing
        """
        if self.auth_type == "ssh":
            if not self.ssh_key:
                raise ValueError("SSH authentication requires ssh_key")
        elif self.auth_type == "https":
            if not self.username or not self.password:
                raise ValueError("HTTPS authentication requires username and password")
        elif self.auth_type == "token":
            if not self.token:
                raise ValueError("Token authentication requires token")


@dataclass
class CachedRepository:
    """Cached repository metadata.
    
    Attributes:
        repo: GitPython Repo object
        repo_id: Unique identifier for the repository
        repo_url: Original repository URL
        last_accessed: Timestamp of last access
        access_count: Number of times this repository has been accessed
    """
    repo: Repo
    repo_id: str
    repo_url: str
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    
    def update_access(self) -> None:
        """Update access metadata."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the cached repository has expired.
        
        Args:
            ttl_seconds: Time-to-live in seconds
            
        Returns:
            True if expired, False otherwise
        """
        return (time.time() - self.last_accessed) > ttl_seconds


class RepositoryManager:
    """Manages Git repository access for both local and remote repositories.
    
    This component handles:
    - Cloning remote repositories to a workspace
    - Accessing existing local repositories
    - Managing SSH and HTTPS authentication
    - Workspace cleanup
    - Concurrent access control via locking
    - Repository caching with TTL-based eviction
    
    Attributes:
        workspace_dir: Directory where remote repositories are cloned
        cache_ttl_seconds: Time-to-live for cached repositories in seconds
        max_cache_size: Maximum number of repositories to keep in cache
        _locks: Dictionary of locks for concurrent access control
        _lock_manager: Lock for managing the locks dictionary
        _cache: Dictionary of cached repositories
        _cache_lock: Lock for cache operations
    """
    
    def __init__(
        self, 
        workspace_dir: str = "/tmp/git-workspaces",
        cache_ttl_seconds: int = 3600,  # 1 hour default
        max_cache_size: int = 50
    ):
        """Initialize the repository manager.
        
        Args:
            workspace_dir: Directory for cloning remote repositories
            cache_ttl_seconds: Time-to-live for cached repositories (default: 3600s/1h)
            max_cache_size: Maximum number of repositories in cache (default: 50)
        """
        self.workspace_dir = Path(workspace_dir)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_cache_size = max_cache_size
        
        # Locks for concurrent access control
        self._locks: dict[str, Lock] = {}
        self._lock_manager = Lock()
        
        # Repository cache
        self._cache: Dict[str, CachedRepository] = {}
        self._cache_lock = Lock()
    
    def _get_repo_lock(self, repo_id: str) -> Lock:
        """Get or create a lock for a specific repository.
        
        Args:
            repo_id: Unique identifier for the repository
            
        Returns:
            Lock object for the repository
        """
        with self._lock_manager:
            if repo_id not in self._locks:
                self._locks[repo_id] = Lock()
            return self._locks[repo_id]
    
    def _generate_repo_id(self, repo_url: str) -> str:
        """Generate a unique identifier for a repository URL.
        
        Uses SHA256 hash of the URL to create a filesystem-safe identifier.
        
        Args:
            repo_url: URL of the Git repository
            
        Returns:
            Unique identifier string
        """
        return hashlib.sha256(repo_url.encode()).hexdigest()[:16]
    
    def _get_repo_path(self, repo_url: str) -> Path:
        """Get the local path where a repository should be cloned.
        
        Args:
            repo_url: URL of the Git repository
            
        Returns:
            Path object for the repository directory
        """
        repo_id = self._generate_repo_id(repo_url)
        return self.workspace_dir / repo_id
    
    def _evict_expired_cache_entries(self) -> int:
        """Remove expired entries from the cache.
        
        Returns:
            Number of entries evicted
        """
        evicted = 0
        with self._cache_lock:
            expired_keys = [
                repo_id for repo_id, cached_repo in self._cache.items()
                if cached_repo.is_expired(self.cache_ttl_seconds)
            ]
            
            for repo_id in expired_keys:
                del self._cache[repo_id]
                evicted += 1
        
        return evicted
    
    def _evict_lru_cache_entries(self) -> int:
        """Evict least recently used cache entries if cache is full.
        
        Returns:
            Number of entries evicted
        """
        evicted = 0
        with self._cache_lock:
            if len(self._cache) >= self.max_cache_size:
                # Sort by last accessed time (oldest first)
                sorted_entries = sorted(
                    self._cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                # Remove oldest entries to make room
                num_to_remove = len(self._cache) - self.max_cache_size + 1
                for repo_id, _ in sorted_entries[:num_to_remove]:
                    del self._cache[repo_id]
                    evicted += 1
        
        return evicted
    
    def _get_from_cache(self, repo_id: str) -> Optional[CachedRepository]:
        """Get a repository from cache if available and not expired.
        
        Args:
            repo_id: Unique identifier for the repository
            
        Returns:
            CachedRepository if found and valid, None otherwise
        """
        with self._cache_lock:
            cached_repo = self._cache.get(repo_id)
            
            if cached_repo:
                # Check if expired
                if cached_repo.is_expired(self.cache_ttl_seconds):
                    del self._cache[repo_id]
                    return None
                
                # Update access metadata
                cached_repo.update_access()
                return cached_repo
            
            return None
    
    def _add_to_cache(self, repo_id: str, repo_url: str, repo: Repo) -> None:
        """Add a repository to the cache.
        
        Args:
            repo_id: Unique identifier for the repository
            repo_url: Original repository URL
            repo: GitPython Repo object
        """
        # Evict expired entries first
        self._evict_expired_cache_entries()
        
        # Evict LRU entries if cache is full
        self._evict_lru_cache_entries()
        
        with self._cache_lock:
            cached_repo = CachedRepository(
                repo=repo,
                repo_id=repo_id,
                repo_url=repo_url
            )
            cached_repo.update_access()
            self._cache[repo_id] = cached_repo
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._cache_lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_cache_size,
                "ttl_seconds": self.cache_ttl_seconds,
                "total_access_count": sum(
                    cached.access_count for cached in self._cache.values()
                )
            }
    
    def clear_cache(self) -> int:
        """Clear all cached repositories.
        
        Returns:
            Number of entries cleared
        """
        with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def warm_cache(self, repo_urls: list[str], credentials: Optional[GitCredentials] = None) -> int:
        """Pre-load frequently accessed repositories into cache.
        
        Args:
            repo_urls: List of repository URLs to warm up
            credentials: Optional credentials for authentication
            
        Returns:
            Number of repositories successfully warmed
        """
        warmed = 0
        for repo_url in repo_urls:
            try:
                # This will clone/pull and add to cache
                self.get_or_clone_repository(repo_url, credentials)
                warmed += 1
            except (GitCommandError, ValueError):
                # Skip repositories that fail to clone
                continue
        
        return warmed
    
    def configure_ssh_key(self, ssh_key_path: str) -> None:
        """Configure SSH key for Git operations.
        
        Sets up the GIT_SSH_COMMAND environment variable to use the specified
        SSH key for Git operations.
        
        Args:
            ssh_key_path: Path to the SSH private key file
            
        Raises:
            FileNotFoundError: If the SSH key file doesn't exist
            ValueError: If the SSH key file is not readable
        """
        key_path = Path(ssh_key_path)
        
        if not key_path.exists():
            raise FileNotFoundError(f"SSH key file not found: {ssh_key_path}")
        
        if not key_path.is_file():
            raise ValueError(f"SSH key path is not a file: {ssh_key_path}")
        
        # Set GIT_SSH_COMMAND to use the specified key
        # Disable strict host key checking for automated operations
        os.environ["GIT_SSH_COMMAND"] = (
            f'ssh -i "{ssh_key_path}" '
            '-o StrictHostKeyChecking=no '
            '-o UserKnownHostsFile=/dev/null'
        )
    
    def _build_auth_url(
        self, 
        repo_url: str, 
        credentials: Optional[GitCredentials]
    ) -> str:
        """Build an authenticated URL for HTTPS Git operations.
        
        Args:
            repo_url: Original repository URL
            credentials: Git credentials for authentication
            
        Returns:
            URL with embedded credentials for HTTPS authentication
        """
        if not credentials:
            return repo_url
        
        # Only modify HTTPS URLs
        if not repo_url.startswith("https://"):
            return repo_url
        
        # Extract the URL without protocol
        url_without_protocol = repo_url.replace("https://", "")
        
        # Build authenticated URL based on auth type
        if credentials.auth_type == "https" and credentials.username and credentials.password:
            return f"https://{credentials.username}:{credentials.password}@{url_without_protocol}"
        elif credentials.auth_type == "token" and credentials.token:
            # For token auth, use token as username with empty password
            return f"https://{credentials.token}@{url_without_protocol}"
        
        return repo_url
    
    def get_or_clone_repository(
        self,
        repo_url: str,
        credentials: Optional[GitCredentials] = None
    ) -> Repo:
        """Get or clone a remote repository to the workspace.
        
        If the repository already exists in the cache and is not expired, it will
        be returned from cache. Otherwise, if it exists in the workspace, it will
        be updated (pulled). If it doesn't exist, it will be cloned.
        
        Args:
            repo_url: URL of the Git repository (SSH or HTTPS)
            credentials: Optional credentials for authentication
            
        Returns:
            GitPython Repo object for the cloned/existing repository
            
        Raises:
            GitCommandError: If clone or pull operation fails
            ValueError: If credentials are invalid
        """
        # Validate credentials if provided
        if credentials:
            credentials.validate()
        
        # Generate repository ID and path
        repo_id = self._generate_repo_id(repo_url)
        
        # Check cache first
        cached_repo = self._get_from_cache(repo_id)
        if cached_repo:
            return cached_repo.repo
        
        repo_path = self._get_repo_path(repo_url)
        
        # Acquire lock for this repository
        lock = self._get_repo_lock(repo_id)
        
        with lock:
            try:
                # Configure SSH if using SSH authentication
                if credentials and credentials.auth_type == "ssh" and credentials.ssh_key:
                    self.configure_ssh_key(credentials.ssh_key)
                
                # Check if repository already exists
                if repo_path.exists() and (repo_path / ".git").exists():
                    try:
                        # Repository exists, open it and pull latest changes
                        repo = Repo(repo_path)
                        
                        # Build authenticated URL if needed
                        auth_url = self._build_auth_url(repo_url, credentials)
                        
                        # Update remote URL with credentials if using HTTPS
                        if credentials and credentials.auth_type in ("https", "token"):
                            if repo.remotes:
                                repo.remotes[0].set_url(auth_url)
                        
                        # Pull latest changes
                        if repo.remotes:
                            origin = repo.remotes[0]
                            origin.pull()
                        
                        # Add to cache
                        self._add_to_cache(repo_id, repo_url, repo)
                        
                        return repo
                    except (InvalidGitRepositoryError, GitCommandError) as e:
                        # If opening/pulling fails, remove and re-clone
                        shutil.rmtree(repo_path, ignore_errors=True)
                
                # Clone the repository
                # Build authenticated URL if needed
                auth_url = self._build_auth_url(repo_url, credentials)
                
                repo = Repo.clone_from(auth_url, repo_path)
                
                # Add to cache
                self._add_to_cache(repo_id, repo_url, repo)
                
                return repo
                
            except GitCommandError as e:
                # Provide helpful error messages based on the error
                error_msg = str(e.stderr) if hasattr(e, 'stderr') else str(e)
                
                if "authentication failed" in error_msg.lower():
                    raise GitCommandError(
                        command=e.command if hasattr(e, 'command') else ['git', 'clone'],
                        status=e.status if hasattr(e, 'status') else 1,
                        stderr=(
                            f"Authentication failed for {repo_url}. "
                            "Please check your credentials."
                        )
                    ) from e
                elif "could not resolve host" in error_msg.lower():
                    raise GitCommandError(
                        command=e.command if hasattr(e, 'command') else ['git', 'clone'],
                        status=e.status if hasattr(e, 'status') else 1,
                        stderr=(
                            f"Could not resolve host for {repo_url}. "
                            "Please check the URL and network connection."
                        )
                    ) from e
                else:
                    raise GitCommandError(
                        command=e.command if hasattr(e, 'command') else ['git', 'clone'],
                        status=e.status if hasattr(e, 'status') else 1,
                        stderr=f"Failed to clone repository {repo_url}: {error_msg}"
                    ) from e
    
    def get_local_repository(self, repo_path: str) -> Repo:
        """Access an existing local Git repository.
        
        Args:
            repo_path: Path to the local Git repository
            
        Returns:
            GitPython Repo object for the repository
            
        Raises:
            InvalidGitRepositoryError: If the path is not a valid Git repository
            FileNotFoundError: If the path doesn't exist
        """
        path = Path(repo_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
        
        try:
            repo = Repo(path)
            return repo
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"Not a valid Git repository: {repo_path}"
            ) from e
    
    def cleanup_workspace(self, repo_id: str) -> None:
        """Remove a cloned repository from the workspace.
        
        Args:
            repo_id: Unique identifier for the repository (from _generate_repo_id)
            
        Raises:
            OSError: If removal fails due to permissions or other OS errors
        """
        repo_path = self.workspace_dir / repo_id
        
        # Acquire lock before cleanup
        lock = self._get_repo_lock(repo_id)
        
        with lock:
            if repo_path.exists():
                try:
                    shutil.rmtree(repo_path)
                except OSError as e:
                    raise OSError(
                        f"Failed to remove repository at {repo_path}: {e}"
                    ) from e
            
            # Remove from cache
            with self._cache_lock:
                if repo_id in self._cache:
                    del self._cache[repo_id]
            
            # Remove lock from dictionary
            with self._lock_manager:
                if repo_id in self._locks:
                    del self._locks[repo_id]
    
    def cleanup_all_workspaces(self) -> int:
        """Remove all cloned repositories from the workspace directory.
        
        Returns:
            Number of repositories cleaned up
            
        Raises:
            OSError: If removal fails due to permissions or other OS errors
        """
        count = 0
        
        if not self.workspace_dir.exists():
            return count
        
        for item in self.workspace_dir.iterdir():
            if item.is_dir():
                try:
                    shutil.rmtree(item)
                    count += 1
                except OSError:
                    # Continue cleaning up other directories even if one fails
                    pass
        
        # Clear cache
        self.clear_cache()
        
        # Clear all locks
        with self._lock_manager:
            self._locks.clear()
        
        return count
