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
            # Use git status --porcelain to get the actual staged status
            # This is more reliable than trying to interpret GitPython diffs
            status_output = self.repo.git.status('--porcelain')
            for line in status_output.split('\n'):
                if line.strip():
                    status_code = line[:2]
                    file_path = line[3:]
                    
                    if status_code.startswith('A'):  # Staged addition
                        # This is a staged addition
                        change_type = 'A'  # Added
                        
                        # Get the file content for the diff
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                lines = content.split('\n')
                                if len(lines) > max_lines:
                                    lines = lines[:max_lines] + [f"... (truncated, {len(lines) - max_lines} more lines)"]
                                diff_content = "\n".join(lines)
                        except Exception:
                            diff_content = f"Added file: {file_path}"
                        
                        changes.append(FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            diff_content=diff_content,
                            lines_added=len(content.split('\n')) if 'content' in locals() else 0,
                            lines_removed=0
                        ))
                    elif status_code.startswith('M'):  # Staged modification
                        # This is a staged modification
                        change_type = 'M'  # Modified
                        
                        # Get the diff between HEAD and the staged version
                        try:
                            diff_output = self.repo.git.diff('HEAD', '--', file_path)
                            diff_content = diff_output
                        except Exception:
                            diff_content = f"Modified file: {file_path}"
                        
                        changes.append(FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            diff_content=diff_content,
                            lines_added=0,
                            lines_removed=0
                        ))
                    elif status_code.startswith('D'):  # Staged deletion
                        # This is a staged deletion
                        change_type = 'D'  # Deleted
                        diff_content = f"Deleted file: {file_path}"
                        
                        changes.append(FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            diff_content=diff_content,
                            lines_added=0,
                            lines_removed=0
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
    
    def _get_diff_content(self, diff, max_lines: int = 500) -> str:
        """Get the diff content for a file change."""
        try:
            file_path = diff.a_path or diff.b_path
            logger.info(f"🔍 GETTING DIFF FOR: {file_path}")
            
            if not file_path:
                logger.warning(f"❌ No file path in diff: {diff}")
                return ""
            
            # Get the actual git diff output
            diff_output = ""  # Initialize diff_output for all cases
            
            # Determine change type from the GitPython diff object
            if diff.new_file:
                change_type = "A"  # Added
            elif diff.deleted_file:
                change_type = "D"  # Deleted
            elif diff.renamed_file:
                change_type = "R"  # Renamed
            elif diff.copied_file:
                change_type = "C"  # Copied
            else:
                change_type = "M"  # Modified
                
            logger.info(f"📊 Change type: {change_type}")
            
            if change_type == "M":  # Modified
                # For modified files, get the diff between working tree and last commit
                logger.info(f"🔍 Executing: git diff HEAD -- {file_path}")
                diff_output = self.repo.git.diff("HEAD", "--", file_path)
                logger.info(f"📊 Git diff output length: {len(diff_output)} characters")
                logger.info(f"📈 Git diff first 100 chars: {diff_output[:100]}...")
            elif change_type == "A":  # Added
                # For added files, show the file content
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        lines = content.split("\n")
                        if len(lines) > max_lines:
                            lines = lines[:max_lines] + [f"... (truncated, {len(lines) - max_lines} more lines)"]
                        return "\n".join(lines)
                except Exception:
                    return f"Added file: {file_path}"
            elif change_type == "D":  # Deleted
                return f"Deleted file: {file_path}"
            else:
                return f"Changed file: {file_path}"
            
            # Process diff output
            logger.info(f"🔍 Processing diff output: {len(diff_output)} characters")
            if diff_output:
                # Return raw diff content - let the prompt builder handle truncation
                return diff_output
            else:
                logger.warning(f"❌ No diff output for {file_path}")
                return f"No diff output for {file_path}"
        except Exception as e:
            logger.error(f"❌ Failed to get diff content for {diff.a_path if hasattr(diff, 'a_path') else 'unknown'}: {e}")
            return f"Error getting diff: {e}"    
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
    
    def create_and_switch_branch(self, branch_name: str) -> None:
        """Create a new branch and switch to it."""
        try:
            # Create and checkout new branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logger.info(f"Created and switched to branch '{branch_name}'")
        except GitCommandError as e:
            raise GitRepositoryError(f"Failed to create branch '{branch_name}': {e}")
    
    def switch_branch(self, branch_name: str) -> None:
        """Switch to an existing branch."""
        try:
            # Get the branch reference and checkout
            branch = self.repo.heads[branch_name]
            branch.checkout()
            logger.info(f"Switched to branch '{branch_name}'")
        except (GitCommandError, IndexError) as e:
            raise GitRepositoryError(f"Failed to switch to branch '{branch_name}': {e}")


class GitRepositoryError(Exception):
    """Custom exception for Git repository operations."""
    pass