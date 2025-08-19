"""
Core Smart Commit engine that orchestrates all components.
"""

import asyncio
import time
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
            optimized_mode=self.settings.performance.macos_local_mode,
            settings=self.settings
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
        commit_message = await self._generate_traditional_commit_message(repo_state)
        
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
                    
                    # Enhanced new file context for better AI understanding
                    file_type_info = self._analyze_new_file_type(item_path, content)
                    enhanced_context = self._enhance_new_file_context(untracked_item, repo_state)
                    
                    diff_content = f"--- /dev/null\n+++ b/{untracked_item}\n"
                    diff_content += f"+NEW FILE: {untracked_item}\n"
                    diff_content += f"+FILE TYPE: {file_type_info['type']}\n"
                    diff_content += f"+PURPOSE: {file_type_info['description']}\n"
                    diff_content += f"+CONTEXT: {enhanced_context}\n"
                    diff_content += f"+CONTENT PREVIEW:\n"
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
    
    async def _generate_traditional_commit_message(self, repo_state: RepositoryState) -> str:
        """Generate a commit message for traditional (multi-file) commits."""
        from smart_commit.utils.message_extractor import MessageExtractor
        
        # Create message extractor instance
        message_extractor = MessageExtractor()
        
        # Generate message for all changes
        prompt = self.prompt_builder.build_commit_prompt(
            repo_state=repo_state,
            file_context=None
        )
        
        logger.debug(f"Generating traditional commit message for {len(repo_state.all_changes)} files")
        
        response = await self.ai_backend.call_with_retry(
            prompt,
            max_retries=self.settings.ai.max_retries
        )
        
        commit_message = message_extractor.extract_commit_message(response.content)
        
        if commit_message:
            logger.debug(f"Generated traditional commit message: {commit_message}")
            return commit_message
        else:
            logger.warning("Failed to extract traditional commit message")
            raise ValueError("Failed to extract commit message")
    
    async def _generate_commit_message(self, file_change: FileChange) -> str:
        """Generate a commit message for a single file change."""
        from smart_commit.utils.message_extractor import MessageExtractor
        
        # Create message extractor instance
        message_extractor = MessageExtractor()
        
        # Check if this is a large diff that will be truncated
        # Get original diff length from Git (before truncation)
        try:
            original_diff = self.git_repo.repo.git.diff("HEAD", "--", file_change.file_path)
            original_lines = len(original_diff.split('\n')) if original_diff else 0
            
            if original_lines > self.settings.git.truncation_threshold:
                self.console.show_truncation_notice(
                    file_change.file_path, 
                    original_lines, 
                    self.settings.git.max_diff_lines
                )
        except Exception as e:
            logger.debug(f"Could not get original diff length for {file_change.file_path}: {e}")
        
        # Generate message for this specific file
        logger.info(f"🔍 FILE CHANGE OBJECT FOR {file_change.file_path}:")
        logger.info(f"📊 Change type: {file_change.change_type}")
        logger.info(f"📈 Diff content length: {len(file_change.diff_content) if file_change.diff_content else 0}")
        logger.info(f"📋 Diff content preview: {file_change.diff_content[:100] if file_change.diff_content else 'None'}...")
        
        prompt = self.prompt_builder.build_commit_prompt(
            repo_state=None,  # Not needed for single file
            file_context=file_change
        )
        
        logger.debug(f"Generating commit message for {file_change.file_path}")
        
        response = await self.ai_backend.call_with_retry(
            prompt,
            max_retries=self.settings.ai.max_retries
        )
        
        commit_message = message_extractor.extract_commit_message(response.content)
        
        if commit_message:
            logger.debug(f"Generated message for {file_change.file_path}: {commit_message}")
            return commit_message
        else:
            logger.warning(f"Failed to extract commit message for {file_change.file_path}")
            raise ValueError("Failed to extract commit message")
    
    async def _generate_atomic_commit_messages(self, file_changes: List[FileChange]) -> List[Dict[str, str]]:
        """Generate commit messages for each file change."""
        commit_messages = []
        total_start_time = time.time()
        
        self.console.console.print(f"\n[bold blue]Generating commit messages for {len(file_changes)} files...[/bold blue]")
        
        for i, file_change in enumerate(file_changes, 1):
            file_start_time = time.time()
            self.console.console.print(f"\n[cyan]Processing file {i}/{len(file_changes)}:[/cyan] {file_change.file_path}")
            
            try:
                # Time the AI call specifically
                ai_start_time = time.time()
                message = await self._generate_commit_message(file_change)
                ai_duration = time.time() - ai_start_time
                
                file_duration = time.time() - file_start_time
                total_duration = time.time() - total_start_time
                
                self.console.console.print(f"  ✅ Generated in {ai_duration:.2f}s (file: {file_duration:.2f}s, total: {total_duration:.2f}s)")
                
                commit_messages.append({
                    "file_path": file_change.file_path,
                    "message": message,
                    "ai_time": ai_duration,
                    "total_time": file_duration
                })
                
            except Exception as e:
                file_duration = time.time() - file_start_time
                total_duration = time.time() - total_start_time
                
                self.console.console.print(f"  ❌ Failed in {file_duration:.2f}s (file: {file_duration:.2f}s, total: {total_duration:.2f}s)")
                logger.debug(f"Failed to generate message for {file_change.file_path}: {e}")
                
                # Generate intelligent fallback
                fallback_message = self._generate_intelligent_fallback(file_change)
                commit_messages.append({
                    "file_path": file_change.file_path,
                    "message": fallback_message,
                    "ai_time": 0,
                    "total_time": file_duration
                })
        
        total_duration = time.time() - total_start_time
        self.console.console.print(f"\n[bold green]✅ All commit messages generated in {total_duration:.2f}s total[/bold green]")
        
        return commit_messages
    
    def _generate_intelligent_fallback(self, file_change: FileChange) -> str:
        """Generate an intelligent fallback commit message based on file context."""
        file_path = file_change.file_path
        change_type = file_change.change_type
        
        # Use the PromptBuilder to get the proper scope
        scope = self.prompt_builder._analyze_scope(file_path)
        
        # Analyze the file path to determine appropriate commit type and scope
        if 'install' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'install'}): update installation configuration"
            elif change_type == 'A':
                return f"feat({scope or 'install'}): add new installation feature"
            elif change_type == 'D':
                return f"chore({scope or 'install'}): remove deprecated installation code"
        
        elif 'llamacpp' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'ai'}): resolve llamacpp backend issues"
            elif change_type == 'A':
                return f"feat({scope or 'ai'}): add new llamacpp functionality"
        
        elif 'prompts' in file_path.lower():
            if change_type == 'M':
                return f"refactor({scope or 'utils'}): improve prompt generation logic"
            elif change_type == 'A':
                return f"feat({scope or 'utils'}): add new prompt templates"
        
        elif 'message_extractor' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'utils'}): resolve message extraction issues"
            elif change_type == 'A':
                return f"feat({scope or 'utils'}): add new message extraction features"
        
        elif 'base.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'ai'}): improve backend base functionality"
            elif change_type == 'A':
                return f"feat({scope or 'ai'}): add new backend features"
        
        elif 'cli.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'core'}): improve command-line interface"
            elif change_type == 'A':
                return f"feat({scope or 'core'}): add new CLI options"
        
        elif 'core.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'core'}): improve core application logic"
            elif change_type == 'A':
                return f"feat({scope or 'core'}): add new core functionality"
        
        elif 'repository.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'git'}): improve git operations handling"
            elif change_type == 'A':
                return f"feat({scope or 'git'}): add new git operation features"
        
        elif 'console.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'ui'}): improve console output handling"
            elif change_type == 'A':
                return f"feat({scope or 'ui'}): add new console features"
        
        elif 'settings.py' in file_path.lower():
            if change_type == 'M':
                return f"fix({scope or 'config'}): update configuration settings"
            elif change_type == 'A':
                return f"feat({scope or 'config'}): add new configuration options"
        
        # Generic fallback based on change type with proper scope
        if change_type == 'M':
            # Remove file extension for cleaner scope
            filename = file_path.split('/')[-1]
            clean_filename = filename.replace('.py', '').replace('.sh', '').replace('.md', '')
            return f"fix({scope or 'smart_commit'}): update {clean_filename}"
        elif change_type == 'A':
            filename = file_path.split('/')[-1]
            clean_filename = filename.replace('.py', '').replace('.sh', '').replace('.md', '')
            return f"feat({scope or 'smart_commit'}): add {clean_filename}"
        elif change_type == 'D':
            filename = file_path.split('/')[-1]
            clean_filename = filename.replace('.py', '').replace('.sh', '').replace('.md', '')
            return f"chore({scope or 'smart_commit'}): remove {clean_filename}"
        else:
            filename = file_path.split('/')[-1]
            clean_filename = filename.replace('.py', '').replace('.sh', '').replace('.md', '')
            return f"update({scope or 'smart_commit'}): {clean_filename}"
    
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
                top_level = parts[0]
                
                # Check if this top-level directory already exists in git
                if len(parts) > 1:  # This is a file/directory inside a parent directory
                    if self._directory_exists_in_git(top_level):
                        # Parent directory exists, so add the specific nested item
                        # This will be processed as an individual file/directory change
                        top_level_items.add(file_path)
                        continue
                
                # Either it's a top-level file or a completely new directory
                top_level_items.add(top_level)
        
        return sorted(list(top_level_items))

    def _directory_exists_in_git(self, directory: str) -> bool:
        """Check if a directory already exists in git (tracked or has tracked content)."""
        try:
            repo = self.git_repo.repo
            if not repo:
                return False
            
            # Check if the directory itself is tracked
            try:
                # Try to get the tree object for this directory
                tree = repo.tree()
                for item in tree.traverse():
                    if item.path == directory or item.path.startswith(f"{directory}/"):
                        return True
            except:
                pass
            
            # Check if there are any tracked files in this directory
            tracked_files = [f for f in repo.tree().traverse() if f.path.startswith(f"{directory}/")]
            if tracked_files:
                return True
            
            # Check if the directory exists in the working tree (even if untracked)
            # but has tracked content from previous commits
            working_dir = Path(self.git_repo.repo_path) / directory
            if working_dir.exists() and working_dir.is_dir():
                # Check if any files in this directory are tracked
                for item in working_dir.rglob('*'):
                    if item.is_file():
                        try:
                            # Check if this file is tracked in git
                            repo.git.ls_files(str(item.relative_to(self.git_repo.repo_path)))
                            return True
                        except:
                            # File is not tracked, continue checking others
                            continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Could not check if directory {directory} exists in git: {e}")
            return False

    def _analyze_new_file_type(self, file_path: Path, content: str) -> Dict[str, str]:
        """Analyze new file to determine appropriate commit type and description."""
        file_info = {
            'extension': file_path.suffix.lower(),
            'is_documentation': file_path.suffix.lower() in ['.md', '.txt', '.rst', '.adoc'],
            'is_script': file_path.suffix.lower() in ['.py', '.sh', '.js', '.ts', '.rb', '.php'],
            'is_config': file_path.suffix.lower() in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'],
            'is_data': file_path.suffix.lower() in ['.csv', '.xml', '.sql', '.db'],
            'content_preview': content[:200] if content else ''
        }
        
        # Determine commit type based on analysis
        if file_info['is_documentation']:
            return {'type': 'docs', 'description': 'documentation'}
        elif file_info['is_script']:
            return {'type': 'feat', 'description': 'new script/utility'}
        elif file_info['is_config']:
            return {'type': 'chore', 'description': 'configuration'}
        elif file_info['is_data']:
            return {'type': 'feat', 'description': 'data file'}
        else:
            return {'type': 'feat', 'description': 'new file'}

    def _enhance_new_file_context(self, file_path: str, repo_state: RepositoryState) -> str:
        """Add context about where the new file fits in the project."""
        try:
            # Get existing directories from the repository
            existing_dirs = set()
            if self.git_repo.repo:
                try:
                    tree = self.git_repo.repo.tree()
                    for item in tree.traverse():
                        if item.type == 'tree':  # Directory
                            existing_dirs.add(item.path)
                except:
                    pass
            
            # Get the parent directory of the new file
            parent_dir = file_path.split('/')[0] if '/' in file_path else 'root'
            
            # Check if this is adding to an existing directory structure
            if parent_dir in existing_dirs:
                context = f"Adding new content to existing {parent_dir} directory"
            else:
                context = f"Creating new {parent_dir} directory structure"
            
            # Add more context based on file type
            if file_path.endswith('.md'):
                context += " (documentation)"
            elif file_path.endswith('.py'):
                context += " (Python script)"
            elif file_path.endswith('.sh'):
                context += " (shell script)"
            
            return context
            
        except Exception as e:
            logger.debug(f"Could not enhance new file context for {file_path}: {e}")
            return "new file addition"


class SmartCommitError(Exception):
    """Custom exception for Smart Commit operations."""
    pass