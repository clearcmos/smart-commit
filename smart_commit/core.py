"""
Core Smart Commit engine that orchestrates all components.
"""

import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from .config.settings import Settings
from .git_ops.repository import GitRepository, FileChange, RepositoryState, GitRepositoryError
from .ai_backends.factory import BackendFactory
from .ai_backends.base import AIBackend
from .utils.message_extractor import message_extractor
from .utils.prompts import PromptBuilder
from .ui.console import SmartCommitConsole


class SmartCommit:
    """Core Smart Commit application engine."""
    
    def __init__(self, settings: Optional[Settings] = None, repo_path: Optional[Path] = None):
        """Initialize Smart Commit with settings and repository."""
        self.settings = settings or Settings()
        self.git_repo = GitRepository(repo_path)
        self.console = SmartCommitConsole(self.settings)
        self.ai_backend: Optional[AIBackend] = None
        self.prompt_builder = PromptBuilder(
            character_limit=self.settings.performance.character_limit,
            optimized_mode=self.settings.performance.macos_local_mode
        )
        
        logger.info("Smart Commit initialized")
    
    async def initialize(self) -> None:
        """Initialize AI backend and validate setup."""
        logger.info("Initializing Smart Commit...")
        
        # Validate Git repository
        if not self.git_repo.is_valid:
            raise SmartCommitError("Not a valid Git repository")
        
        # Initialize AI backend
        try:
            self.ai_backend = await BackendFactory.create_backend(self.settings)
            logger.info(f"Initialized {self.ai_backend.backend_type} backend")
        except Exception as e:
            raise SmartCommitError(f"Failed to initialize AI backend: {e}")
        
        # Test AI backend connection
        if not await self.ai_backend.health_check():
            raise SmartCommitError(f"AI backend health check failed. Check your {self.ai_backend.backend_type} server.")
    
    async def run_traditional_commit(self, dry_run: bool = False) -> None:
        """Run traditional single commit workflow."""
        logger.info(f"Running traditional commit workflow (dry_run={dry_run})")
        
        # Get repository state
        repo_state = self.git_repo.get_repository_state(self.settings.git.max_diff_lines)
        
        if not repo_state.has_changes:
            self.console.print_warning("No changes detected in repository")
            return
        
        # Show repository status
        self.console.print_repository_status(repo_state)
        self.console.print_file_changes(repo_state.all_changes, "Pending Changes")
        
        # Stage files if needed
        if self.settings.git.auto_stage and repo_state.unstaged_files:
            if not dry_run:
                with self.console.show_progress_spinner("Staging changes"):
                    self.git_repo.stage_files()
                    await asyncio.sleep(0.5)  # Brief pause for UX
                self.console.print_success("Staged all changes")
        
        # Generate commit message
        commit_message = await self._generate_commit_message(repo_state)
        
        if not commit_message:
            self.console.print_error("Failed to generate commit message")
            return
        
        # Show preview
        self.console.show_commit_message_preview(commit_message)
        
        if dry_run:
            self.console.print_info("Dry run complete - no commit created")
            return
        
        # Confirm and commit
        if self.settings.ui.interactive:
            if not self.console.confirm_action("Create commit with this message?"):
                self.console.print_info("Commit cancelled")
                return
        
        # Create commit
        with self.console.show_progress_spinner("Creating commit"):
            commit_hash = self.git_repo.commit(commit_message)
            await asyncio.sleep(0.5)
        
        self.console.print_success(f"Created commit {commit_hash[:8]}")
        
        # Push if configured
        if self.settings.git.auto_push:
            await self._push_commits()
    
    async def run_atomic_commits(self, dry_run: bool = False) -> None:
        """Run atomic commits workflow (one commit per file)."""
        logger.info(f"Running atomic commits workflow (dry_run={dry_run})")
        
        # Get repository state
        repo_state = self.git_repo.get_repository_state(self.settings.git.max_diff_lines)
        
        if not repo_state.has_changes:
            self.console.print_warning("No changes detected in repository")
            return
        
        # Show repository status
        self.console.print_repository_status(repo_state)
        
        # Get all files to process (tracked changes + untracked files)
        files_to_process = repo_state.all_changes.copy()
        
        # Add untracked files/directories as top-level units (like bash version)
        top_level_untracked = self._get_top_level_untracked(repo_state.untracked_files)
        
        for untracked_item in top_level_untracked:
            try:
                item_path = Path(self.git_repo.repo_path) / untracked_item
                
                if item_path.is_file():
                    # Handle single file
                    with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    diff_content = f"--- /dev/null\n+++ b/{untracked_item}\n"
                    for line in content.splitlines():
                        diff_content += f"+{line}\n"
                    
                    file_change = FileChange(
                        file_path=untracked_item,
                        change_type='A',
                        diff_content=diff_content,
                        lines_added=len(content.splitlines()),
                        lines_removed=0
                    )
                    files_to_process.append(file_change)
                    
                elif item_path.is_dir():
                    # Handle directory as a unit
                    # Get summary of files in directory
                    all_files = list(item_path.rglob('*'))
                    py_files = [f for f in all_files if f.suffix == '.py']
                    total_files = len([f for f in all_files if f.is_file()])
                    
                    # Create summary diff for directory
                    diff_content = f"--- /dev/null\n+++ b/{untracked_item}/\n"
                    diff_content += f"+New directory with {total_files} files\n"
                    if py_files:
                        diff_content += f"+Python package: {len(py_files)} Python files\n"
                    
                    file_change = FileChange(
                        file_path=untracked_item,
                        change_type='A',
                        diff_content=diff_content,
                        lines_added=total_files,
                        lines_removed=0
                    )
                    files_to_process.append(file_change)
                    
            except Exception as e:
                logger.warning(f"Failed to process untracked item {untracked_item}: {e}")
        
        if not files_to_process:
            self.console.print_warning("No files found for atomic commits")
            return
        
        self.console.print_file_changes(files_to_process, "Files for Atomic Commits")
        
        # Generate commit messages for all files
        proposed_commits = await self._generate_atomic_commit_messages(files_to_process)
        
        if not proposed_commits:
            self.console.print_error("Failed to generate commit messages")
            return
        
        # Show preview and get approval
        self.console.show_atomic_commits_preview(proposed_commits)
        
        if dry_run:
            self.console.print_info("Dry run complete - no commits created")
            return
        
        # Get user approval
        if self.settings.ui.interactive:
            approval = await self._handle_atomic_commits_approval(proposed_commits)
            if not approval:
                self.console.print_info("Atomic commits cancelled")
                return
            proposed_commits = approval
        
        # Create commits
        created_commits = await self._create_atomic_commits(proposed_commits)
        
        if created_commits:
            self.console.show_commit_summary(created_commits)
            
            # Push if configured
            if self.settings.git.auto_push:
                await self._push_commits()
    
    async def _generate_commit_message(self, repo_state: RepositoryState) -> Optional[str]:
        """Generate commit message for repository state."""
        with self.console.show_progress_spinner("Generating commit message"):
            try:
                # Get recent commits for context
                recent_commits = self.git_repo.get_recent_commits(3)
                
                # Build prompt
                prompt = self.prompt_builder.build_commit_prompt(
                    repo_state=repo_state,
                    recent_commits=recent_commits
                )
                
                # Call AI backend
                response = await self.ai_backend.call_with_retry(
                    prompt, 
                    max_retries=self.settings.ai.max_retries
                )
                
                # Extract commit message
                commit_message = message_extractor.extract_commit_message(response.content)
                
                if commit_message:
                    logger.info(f"Generated commit message: {commit_message}")
                    return commit_message
                else:
                    logger.warning("Failed to extract commit message from AI response")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to generate commit message: {e}")
                return None
    
    async def _generate_atomic_commit_messages(self, files: List[FileChange]) -> List[Dict[str, str]]:
        """Generate commit messages for each file in atomic mode."""
        proposed_commits = []
        
        with self.console.show_progress_bar(len(files), "Generating commit messages") as progress:
            task = progress.add_task("Processing files...", total=len(files))
            
            for file_change in files:
                try:
                    # Generate message for this specific file
                    prompt = self.prompt_builder.build_commit_prompt(
                        repo_state=None,  # Not needed for single file
                        file_context=file_change
                    )
                    
                    response = await self.ai_backend.call_with_retry(
                        prompt,
                        max_retries=self.settings.ai.max_retries
                    )
                    
                    commit_message = message_extractor.extract_commit_message(response.content)
                    
                    if commit_message:
                        proposed_commits.append({
                            "file_path": file_change.file_path,
                            "message": commit_message,
                            "change_type": file_change.change_type
                        })
                        logger.debug(f"Generated message for {file_change.file_path}: {commit_message}")
                    else:
                        logger.warning(f"Failed to generate message for {file_change.file_path}")
                        # Add fallback message
                        fallback_msg = f"{file_change.change_type.lower()}: update {file_change.file_path}"
                        proposed_commits.append({
                            "file_path": file_change.file_path,
                            "message": fallback_msg,
                            "change_type": file_change.change_type
                        })
                    
                except Exception as e:
                    logger.error(f"Failed to generate message for {file_change.file_path}: {e}")
                    # Add error fallback
                    fallback_msg = f"update: {file_change.file_path}"
                    proposed_commits.append({
                        "file_path": file_change.file_path,
                        "message": fallback_msg,
                        "change_type": file_change.change_type
                    })
                
                progress.advance(task)
                await asyncio.sleep(0.1)  # Brief pause for responsiveness
        
        return proposed_commits
    
    async def _handle_atomic_commits_approval(self, proposed_commits: List[Dict[str, str]]) -> Optional[List[Dict[str, str]]]:
        """Handle user approval and editing of atomic commits."""
        while True:
            choice = self.console.prompt_atomic_commits_approval(len(proposed_commits))
            
            if choice == "approve":
                return proposed_commits
            elif choice == "cancel":
                return None
            elif choice.startswith("edit_"):
                # Edit specific commit
                index = int(choice.split("_")[1]) - 1
                if 0 <= index < len(proposed_commits):
                    commit = proposed_commits[index]
                    new_message = self.console.prompt_commit_message_edit(
                        commit["message"],
                        commit["file_path"]
                    )
                    if new_message:
                        proposed_commits[index]["message"] = new_message
                    
                    # Show updated preview
                    self.console.show_atomic_commits_preview(proposed_commits)
    
    async def _create_atomic_commits(self, proposed_commits: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Create individual commits for each file."""
        created_commits = []
        
        with self.console.show_progress_bar(len(proposed_commits), "Creating commits") as progress:
            task = progress.add_task("Committing files...", total=len(proposed_commits))
            
            for commit_data in proposed_commits:
                try:
                    file_path = commit_data["file_path"]
                    message = commit_data["message"]
                    
                    # Stage only this file
                    self.git_repo.stage_files([file_path])
                    
                    # Create commit
                    commit_hash = self.git_repo.commit(message)
                    
                    created_commits.append({
                        "file_path": file_path,
                        "message": message,
                        "hash": commit_hash
                    })
                    
                    logger.info(f"Created commit {commit_hash[:8]} for {file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to commit {commit_data['file_path']}: {e}")
                    self.console.print_error(f"Failed to commit {commit_data['file_path']}: {e}")
                
                progress.advance(task)
                await asyncio.sleep(0.1)
        
        return created_commits
    
    async def _push_commits(self) -> None:
        """Push commits to remote repository."""
        try:
            with self.console.show_progress_spinner("Pushing to remote"):
                self.git_repo.push()
                await asyncio.sleep(0.5)
            
            self.console.print_success("Successfully pushed commits to remote")
            
        except GitRepositoryError as e:
            self.console.print_error(f"Failed to push: {e}")
            logger.error(f"Push failed: {e}")
    
    async def test_ai_backend(self) -> bool:
        """Test AI backend connectivity and functionality."""
        if not self.ai_backend:
            await self.initialize()
        
        try:
            with self.console.show_progress_spinner("Testing AI backend"):
                # Test health check
                health_ok = await self.ai_backend.health_check()
                if not health_ok:
                    self.console.print_error("AI backend health check failed")
                    return False
                
                # Test simple API call
                test_prompt = "Generate a test commit message for: Added a new file"
                response = await self.ai_backend.call_api(test_prompt)
                
                if response.content:
                    self.console.print_success("AI backend test successful")
                    self.console.print_info(f"Test response: {response.content[:50]}...")
                    return True
                else:
                    self.console.print_error("AI backend returned empty response")
                    return False
                    
        except Exception as e:
            self.console.print_error(f"AI backend test failed: {e}")
            return False
    
    def show_configuration(self) -> None:
        """Show current configuration."""
        self.console.console.print("[bold blue]Smart Commit Configuration[/bold blue]")
        self.console.console.print()
        
        # AI Settings
        self.console.console.print("[bold]AI Backend:[/bold]")
        self.console.console.print(f"  Type: {self.settings.ai.backend_type}")
        self.console.console.print(f"  URL: {self.settings.ai.api_url}")
        self.console.console.print(f"  Model: {self.settings.ai.model}")
        self.console.console.print(f"  Timeout: {self.settings.ai.timeout}s")
        self.console.console.print()
        
        # Git Settings
        self.console.console.print("[bold]Git Settings:[/bold]")
        self.console.console.print(f"  Auto-stage: {self.settings.git.auto_stage}")
        self.console.console.print(f"  Auto-push: {self.settings.git.auto_push}")
        self.console.console.print(f"  Max diff lines: {self.settings.git.max_diff_lines}")
        self.console.console.print()
        
        # Performance Settings
        self.console.console.print("[bold]Performance:[/bold]")
        self.console.console.print(f"  Character limit: {self.settings.performance.character_limit}")
        self.console.console.print(f"  macOS optimization: {self.settings.performance.macos_local_mode}")
        self.console.console.print()
    
    def _get_top_level_untracked(self, untracked_files: List[str]) -> List[str]:
        """Get top-level untracked items (files and directories), not recursive."""
        top_level_items = set()
        
        for file_path in untracked_files:
            # Get the first path component
            parts = file_path.split('/')
            if parts:
                top_level_items.add(parts[0])
        
        return sorted(list(top_level_items))


class SmartCommitError(Exception):
    """Custom exception for Smart Commit operations."""
    pass