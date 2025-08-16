"""
Professional Git repository operations with comprehensive error handling.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from git import Repo, InvalidGitRepositoryError, GitCommandError
from loguru import logger


@dataclass
class FileChange:
    """Represents a single file change."""
    
    file_path: str
    change_type: str  # 'M', 'A', 'D', 'R', 'C', etc.
    diff_content: str
    lines_added: int = 0
    lines_removed: int = 0
    
    @property
    def is_modified(self) -> bool:
        return self.change_type == 'M'
    
    @property
    def is_added(self) -> bool:
        return self.change_type == 'A'
    
    @property
    def is_deleted(self) -> bool:
        return self.change_type == 'D'
    
    @property
    def scope(self) -> Optional[str]:
        """Extract conventional commit scope from file path."""
        parts = self.file_path.split('/')
        return parts[0] if len(parts) > 1 else None


@dataclass
class RepositoryState:
    """Represents the current state of the git repository."""
    
    has_changes: bool
    staged_files: List[FileChange]
    unstaged_files: List[FileChange]
    untracked_files: List[str]
    current_branch: str
    remote_branch: Optional[str]
    commits_ahead: int = 0
    commits_behind: int = 0
    
    @property
    def all_changes(self) -> List[FileChange]:
        """Get all file changes (staged + unstaged)."""
        return self.staged_files + self.unstaged_files
    
    @property
    def total_files_changed(self) -> int:
        """Total number of files with changes."""
        return len(self.all_changes) + len(self.untracked_files)


class GitRepository:
    """Professional Git repository interface."""
    
    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize Git repository."""
        self.repo_path = repo_path or Path.cwd()
        self.repo: Optional[Repo] = None
        self._initialize_repo()
    
    def _initialize_repo(self) -> None:
        """Initialize the Git repository object."""
        try:
            self.repo = Repo(self.repo_path, search_parent_directories=True)
            logger.debug(f"Initialized Git repository at {self.repo.working_dir}")
        except InvalidGitRepositoryError:
            raise GitRepositoryError(f"Not a Git repository: {self.repo_path}")
    
    @property
    def is_valid(self) -> bool:
        """Check if this is a valid Git repository."""
        return self.repo is not None and not self.repo.bare
    
    def get_repository_state(self, max_diff_lines: int = 500) -> RepositoryState:
        """Get comprehensive repository state."""
        if not self.is_valid:
            raise GitRepositoryError("Invalid Git repository")
        
        try:
            # Get current branch info
            current_branch = self.repo.active_branch.name
            remote_branch = None
            commits_ahead = 0
            commits_behind = 0
            
            # Get remote tracking info
            try:
                remote_branch = self.repo.active_branch.tracking_branch()
                if remote_branch:
                    commits_ahead = len(list(self.repo.iter_commits(f'{remote_branch}..HEAD')))
                    commits_behind = len(list(self.repo.iter_commits(f'HEAD..{remote_branch}')))
                    remote_branch = remote_branch.name
            except Exception as e:
                logger.debug(f"Could not get remote tracking info: {e}")
            
            # Get file changes
            staged_files = self._get_staged_changes(max_diff_lines)
            unstaged_files = self._get_unstaged_changes(max_diff_lines)
            untracked_files = self.repo.untracked_files
            
            has_changes = bool(staged_files or unstaged_files or untracked_files)
            
            return RepositoryState(
                has_changes=has_changes,
                staged_files=staged_files,
                unstaged_files=unstaged_files,
                untracked_files=untracked_files,
                current_branch=current_branch,
                remote_branch=remote_branch,
                commits_ahead=commits_ahead,
                commits_behind=commits_behind
            )
            
        except Exception as e:
            logger.error(f"Failed to get repository state: {e}")
            raise GitRepositoryError(f"Failed to analyze repository: {e}")
    
    def _get_staged_changes(self, max_lines: int) -> List[FileChange]:
        """Get staged file changes."""
        changes = []
        
        try:
            # Get staged changes (index vs HEAD)
            diffs = self.repo.index.diff('HEAD')
            
            for diff in diffs:
                file_path = diff.a_path or diff.b_path
                change_type = self._get_change_type(diff)
                diff_content = self._get_diff_content(diff, max_lines)
                
                changes.append(FileChange(
                    file_path=file_path,
                    change_type=change_type,
                    diff_content=diff_content,
                    lines_added=diff.a_blob.size if diff.a_blob else 0,
                    lines_removed=diff.b_blob.size if diff.b_blob else 0
                ))
                
        except Exception as e:
            logger.warning(f"Failed to get staged changes: {e}")
        
        return changes
    
    def _get_unstaged_changes(self, max_lines: int) -> List[FileChange]:
        """Get unstaged file changes."""
        changes = []
        
        try:
            # Get unstaged changes (working tree vs index)
            diffs = self.repo.index.diff(None)
            
            for diff in diffs:
                file_path = diff.a_path or diff.b_path
                change_type = self._get_change_type(diff)
                diff_content = self._get_diff_content(diff, max_lines)
                
                changes.append(FileChange(
                    file_path=file_path,
                    change_type=change_type,
                    diff_content=diff_content
                ))
                
        except Exception as e:
            logger.warning(f"Failed to get unstaged changes: {e}")
        
        return changes
    
    def _get_change_type(self, diff) -> str:
        """Extract change type from git diff."""
        if diff.new_file:
            return 'A'  # Added
        elif diff.deleted_file:
            return 'D'  # Deleted
        elif diff.renamed_file:
            return 'R'  # Renamed
        elif diff.copied_file:
            return 'C'  # Copied
        else:
            return 'M'  # Modified
    
    def _get_diff_content(self, diff, max_lines: int) -> str:
        """Extract and limit diff content."""
        try:
            if diff.a_blob and diff.b_blob:
                diff_text = diff.a_blob.data_stream.read().decode('utf-8', errors='ignore')
                lines = diff_text.split('\n')
                if len(lines) > max_lines:
                    lines = lines[:max_lines] + [f"... (truncated, {len(lines) - max_lines} more lines)"]
                return '\n'.join(lines)
        except Exception as e:
            logger.debug(f"Failed to get diff content for {diff.a_path}: {e}")
        
        return ""
    
    def stage_files(self, file_paths: Optional[List[str]] = None) -> None:
        """Stage files for commit."""
        try:
            if file_paths:
                # Handle deleted and modified files separately
                existing_files = []
                deleted_files = []
                
                for file_path in file_paths:
                    if os.path.exists(file_path):
                        existing_files.append(file_path)
                    else:
                        # Check if it's a deleted file
                        try:
                            # Use git status to check if file is deleted
                            status = self.repo.git.status('--porcelain', file_path)
                            if status.strip().startswith('D '):
                                deleted_files.append(file_path)
                            else:
                                existing_files.append(file_path)
                        except GitCommandError:
                            existing_files.append(file_path)
                
                # Stage existing files
                if existing_files:
                    self.repo.index.add(existing_files)
                
                # Stage deleted files
                if deleted_files:
                    self.repo.git.add(deleted_files)
                
                logger.info(f"Staged {len(file_paths)} files")
            else:
                self.repo.git.add('--all')
                logger.info("Staged all changes")
        except GitCommandError as e:
            raise GitRepositoryError(f"Failed to stage files: {e}")
    
    def commit(self, message: str, author: Optional[str] = None) -> str:
        """Create a commit with the given message."""
        try:
            if author:
                commit = self.repo.index.commit(message, author=author)
            else:
                commit = self.repo.index.commit(message)
            
            logger.info(f"Created commit {commit.hexsha[:8]}: {message}")
            return commit.hexsha
            
        except GitCommandError as e:
            raise GitRepositoryError(f"Failed to create commit: {e}")
    
    def push(self, remote: str = "origin", branch: Optional[str] = None) -> None:
        """Push commits to remote repository."""
        try:
            if not branch:
                branch = self.repo.active_branch.name
            
            # Check if remote branch exists
            remote_ref = f"{remote}/{branch}"
            if remote_ref not in [ref.name for ref in self.repo.refs]:
                # Set upstream for new branch
                self.repo.git.push("--set-upstream", remote, branch)
                logger.info(f"Created upstream branch {remote}/{branch}")
            else:
                self.repo.git.push(remote, branch)
                logger.info(f"Pushed to {remote}/{branch}")
                
        except GitCommandError as e:
            raise GitRepositoryError(f"Failed to push: {e}")
    
    def get_recent_commits(self, count: int = 5) -> List[Dict[str, str]]:
        """Get recent commit messages for context."""
        commits = []
        
        try:
            for commit in self.repo.iter_commits(max_count=count):
                commits.append({
                    "hash": commit.hexsha[:8],
                    "message": commit.message.strip(),
                    "author": str(commit.author),
                    "date": commit.committed_datetime.isoformat()
                })
        except Exception as e:
            logger.warning(f"Failed to get recent commits: {e}")
        
        return commits


class GitRepositoryError(Exception):
    """Custom exception for Git repository operations."""
    pass