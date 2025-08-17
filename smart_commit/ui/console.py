"""
Beautiful console interface with Rich components.
"""

from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree
from rich.text import Text
from rich.theme import Theme
from rich import box
import time

from ..git_ops.repository import FileChange, RepositoryState
from ..config.settings import Settings


class SmartCommitConsole:
    """Professional console interface for Smart Commit."""
    
    def __init__(self, settings: Settings):
        """Initialize console with settings."""
        self.settings = settings
        self._setup_styles()
        self.console = Console(
            color_system="auto" if settings.ui.use_colors else None,
            force_terminal=True,
            theme=self.theme
        )
    
    def _setup_styles(self) -> None:
        """Setup custom styles for consistent theming."""
        self.styles = {
            "title": "bold blue",
            "success": "bold green",
            "warning": "bold yellow", 
            "error": "bold red",
            "info": "blue",
            "muted": "dim",
            "file_added": "green",
            "file_modified": "yellow",
            "file_deleted": "red",
            "commit_hash": "dim cyan",
            "commit_type": "bold magenta",
            "scope": "cyan",
        }
        
        # Create Rich theme
        self.theme = Theme(self.styles)
    
    def print_banner(self) -> None:
        """Print application banner."""
        banner = Panel.fit(
            "[bold blue]Smart Commit v2.0[/bold blue]\n"
            "[dim]AI-powered Git commit message generator[/dim]",
            box=box.ROUNDED,
            style="blue"
        )
        self.console.print(banner)
        self.console.print()
    
    def print_repository_status(self, repo_state: RepositoryState) -> None:
        """Print repository status information."""
        # Branch information
        branch_info = f"[bold]{repo_state.current_branch}[/bold]"
        if repo_state.remote_branch:
            if repo_state.commits_ahead > 0:
                branch_info += f" [yellow]↑{repo_state.commits_ahead}[/yellow]"
            if repo_state.commits_behind > 0:
                branch_info += f" [red]↓{repo_state.commits_behind}[/red]"
        
        self.console.print(f"[blue]Branch:[/blue] {branch_info}")
        
        # Changes summary
        if repo_state.has_changes:
            changes_text = []
            if repo_state.staged_files:
                changes_text.append(f"[green]{len(repo_state.staged_files)} staged[/green]")
            if repo_state.unstaged_files:
                changes_text.append(f"[yellow]{len(repo_state.unstaged_files)} unstaged[/yellow]")
            if repo_state.untracked_files:
                changes_text.append(f"[red]{len(repo_state.untracked_files)} untracked[/red]")
            
            self.console.print(f"[blue]Changes:[/blue] {', '.join(changes_text)}")
        else:
            self.console.print("[blue]Changes:[/blue] [muted]No changes detected[/muted]")
        
        self.console.print()
    
    def print_file_changes(self, changes: List[FileChange], title: str = "File Changes") -> None:
        """Print detailed file changes in a table."""
        if not changes:
            return
        
        table = Table(title=title, box=box.SIMPLE_HEAD)
        table.add_column("Status", style="bold", width=8)
        table.add_column("File", style="bold")
        table.add_column("Changes", justify="right", style="muted")
        
        for change in changes[:10]:  # Limit display
            # Status with color
            status_style = {
                'M': "file_modified",
                'A': "file_added", 
                'D': "file_deleted",
                'R': "yellow",
                'C': "blue"
            }.get(change.change_type, "")
            
            status_text = {
                'M': "Modified",
                'A': "Added",
                'D': "Deleted", 
                'R': "Renamed",
                'C': "Copied"
            }.get(change.change_type, change.change_type)
            
            # Change summary
            if change.lines_added or change.lines_removed:
                changes_summary = f"+{change.lines_added} -{change.lines_removed}"
            else:
                changes_summary = "—"
            
            table.add_row(
                f"[{status_style}]{status_text}[/{status_style}]",
                change.file_path,
                changes_summary
            )
        
        if len(changes) > 10:
            table.add_row("...", f"[muted]and {len(changes) - 10} more files[/muted]", "")
        
        self.console.print(table)
        self.console.print()
    
    def show_truncation_notice(self, file_path: str, original_lines: int, truncated_lines: int) -> None:
        """Show notice when large files are truncated for AI analysis."""
        
        if original_lines > truncated_lines:
            notice = Panel(
                f"[bold yellow]Large file detected:[/bold yellow] {file_path}\n"
                f"[dim]Showing {truncated_lines:,} of {original_lines:,} lines for AI analysis[/dim]\n"
                f"[dim]Commit message will focus on the most significant changes[/dim]",
                title="📝 Diff Truncation Notice",
                border_style="yellow",
                box=box.ROUNDED
            )
            self.console.print(notice)
            self.console.print()
    
    def show_ai_backend_info(self, backend_type: str, api_url: str, model: str) -> None:
        """Show AI backend information."""
        backend_panel = Panel(
            f"[bold]{backend_type.title()}[/bold] @ {api_url}\n"
            f"Model: [cyan]{model}[/cyan]",
            title="AI Backend",
            box=box.ROUNDED,
            style="blue"
        )
        self.console.print(backend_panel)
        self.console.print()
    
    def show_commit_message_preview(self, message: str, file_path: Optional[str] = None) -> None:
        """Show commit message preview."""
        title = f"Generated Commit Message"
        if file_path:
            title += f" - {file_path}"
        
        # Parse commit message for syntax highlighting
        if ':' in message:
            parts = message.split(':', 1)
            prefix = parts[0].strip()
            description = parts[1].strip()
            
            # Highlight conventional commit format
            formatted_message = f"[commit_type]{prefix}[/commit_type]: {description}"
        else:
            formatted_message = message
        
        message_panel = Panel(
            formatted_message,
            title=title,
            box=box.ROUNDED,
            style="green"
        )
        self.console.print(message_panel)
        self.console.print()
    
    def show_atomic_commits_preview(self, commits: List[Dict[str, str]]) -> None:
        """Show atomic commits preview in a beautiful format."""
        self.console.print("[bold blue]Proposed Atomic Commits[/bold blue]")
        self.console.print()
        
        table = Table(box=box.SIMPLE_HEAD)
        table.add_column("#", style="bold cyan", width=4)
        table.add_column("File", style="bold", width=40)
        table.add_column("Commit Message", style="green", width=120, no_wrap=True)  # Increased width to 120
        
        for i, commit in enumerate(commits, 1):
            # Handle long commit messages by wrapping them properly
            message = commit["message"]
            if len(message) > 110:  # Increased from 75 to 110 for better display
                # Split long messages at word boundaries
                words = message.split()
                lines = []
                current_line = ""
                
                for word in words:
                    if len(current_line + " " + word) <= 110:  # Increased from 75 to 110
                        current_line += (" " + word) if current_line else word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                
                if current_line:
                    lines.append(current_line)
                
                # First row with file path
                table.add_row(
                    str(i),
                    commit["file_path"],
                    lines[0] if lines else message
                )
                
                # Additional rows for long messages
                for line in lines[1:]:
                    table.add_row("", "", line)
            else:
                table.add_row(
                    str(i),
                    commit["file_path"],
                    message
                )
        
        self.console.print(table)
        self.console.print()
    
    def prompt_atomic_commits_approval(self, commit_count: int) -> str:
        """Prompt for atomic commits approval."""
        options_text = (
            "[bold yellow]Options:[/bold yellow]\n"
            "  [green]ENTER[/green] - Accept all messages and create commits\n"
            f"  [cyan]1-{commit_count}[/cyan] - Edit specific commit message\n"
            "  [red]c[/red] - Cancel (no commits will be made)"
        )
        
        self.console.print(Panel(options_text, title="Choose Action", style="yellow"))
        
        while True:
            choice = Prompt.ask(
                f"Your choice",
                choices=[""] + [str(i) for i in range(1, commit_count + 1)] + ["c", "C"],
                default="",
                show_choices=False
            )
            
            if choice == "":
                return "approve"
            elif choice.lower() == "c":
                return "cancel"
            elif choice.isdigit() and 1 <= int(choice) <= commit_count:
                return f"edit_{choice}"
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
    
    def prompt_commit_message_edit(self, current_message: str, file_path: str) -> Optional[str]:
        """Prompt user to edit a commit message."""
        self.console.print(f"\n[bold blue]Editing commit for:[/bold blue] [yellow]{file_path}[/yellow]")
        self.console.print(f"[bold]Current message:[/bold] {current_message}")
        
        new_message = Prompt.ask("Enter new commit message", default=current_message)
        return new_message if new_message != current_message else None
    
    def confirm_action(self, message: str, default: bool = True) -> bool:
        """Get user confirmation for an action."""
        return Confirm.ask(message, default=default)
    
    def show_progress_spinner(self, description: str):
        """Create a progress spinner context manager."""
        return self.console.status(f"[blue]{description}...[/blue]", spinner="dots")
    
    def show_progress_bar(self, total: int, description: str = "Processing"):
        """Create a progress bar for multiple operations."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=True
        )
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        self.console.print(f"[success]✓ {message}[/success]")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.console.print(f"[warning]⚠ {message}[/warning]")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        self.console.print(f"[error]✗ {message}[/error]")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        self.console.print(f"[info]ℹ {message}[/info]")
    
    def show_commit_summary(self, commits: List[Dict[str, Any]]) -> None:
        """Show summary of created commits."""
        self.console.print("[bold green]Commits Created Successfully![/bold green]")
        self.console.print()
        
        for i, commit in enumerate(commits, 1):
            commit_hash = commit.get("hash", "")[:8]
            file_path = commit.get("file_path", "")
            message = commit.get("message", "")
            
            self.console.print(
                f"[bold cyan]{i}.[/bold cyan] "
                f"[commit_hash]{commit_hash}[/commit_hash] "
                f"[muted]{file_path}[/muted]"
            )
            self.console.print(f"   {message}")
        
        self.console.print()
    
    def show_recent_commits(self, commits: List[Dict[str, str]]) -> None:
        """Show recent commits for context."""
        if not commits:
            return
        
        self.console.print("[bold blue]Recent Commits (for context):[/bold blue]")
        
        for commit in commits[:3]:
            hash_short = commit.get("hash", "")
            message = commit.get("message", "")
            self.console.print(f"  [commit_hash]{hash_short}[/commit_hash] {message}")
        
        self.console.print()
    
    def show_diff_preview(self, diff_content: str, max_lines: int = 20) -> None:
        """Show diff content with syntax highlighting."""
        if not diff_content:
            return
        
        lines = diff_content.split('\n')
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f"... ({len(lines) - max_lines} more lines)"]
        
        diff_text = '\n'.join(lines)
        
        # Use Rich syntax highlighting for diff
        syntax = Syntax(
            diff_text,
            "diff",
            theme="monokai",
            line_numbers=False,
            word_wrap=True
        )
        
        self.console.print(Panel(syntax, title="Changes", style="blue"))
        self.console.print()