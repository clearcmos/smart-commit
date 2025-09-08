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
from rich.live import Live
import time
import sys
import os
import asyncio

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
    
    def show_atomic_commits_preview(self, commits: List[Dict[str, str]], selected_index: int = -1, editing_index: int = -1) -> Table:
        """Show atomic commits preview with optional highlighting and inline editing."""
        table = Table(box=box.SIMPLE_HEAD, expand=True)
        table.add_column("#", style="bold cyan", width=4)
        table.add_column("File", style="bold", ratio=1)
        table.add_column("Commit Message", style="green", ratio=2)
        
        for i, commit in enumerate(commits, 1):
            if i - 1 == editing_index:
                # Editing row - show actual editing state  
                table.add_row(
                    f"[yellow bold]{i}[/yellow bold]",
                    f"[yellow]{commit['file_path']}[/yellow]", 
                    f"[black on white]{commit['message']}[/black on white]"
                )
            elif i - 1 == selected_index:
                # Highlighted row with different styling
                table.add_row(
                    f"[reverse bold cyan]{i}[/reverse bold cyan]",
                    f"[reverse bold]{commit['file_path']}[/reverse bold]", 
                    f"[reverse bold green]{commit['message']}[/reverse bold green]"
                )
            else:
                # Normal row
                table.add_row(
                    str(i),
                    commit["file_path"],
                    commit["message"]
                )
        
        return table
    
    def _inline_edit_commit_message(self, commits: List[Dict[str, str]], edit_index: int, current_index: int) -> Optional[str]:
        """Handle true inline editing directly in the table cell."""
        current_message = commits[edit_index]["message"]
        editing_message = current_message
        cursor_pos = len(current_message)
        
        while True:
            # Show table with current editing state
            self._display_table_with_inline_editing(commits, current_index, edit_index, editing_message, cursor_pos)
            
            try:
                char = self._get_char()
                
                if char == '\r' or char == '\n':  # Enter - confirm edit
                    return editing_message if editing_message != current_message else None
                
                elif char == '\x1b':  # Escape - cancel edit  
                    char += self._get_char()  # Get rest of escape sequence
                    if len(char) == 2:  # Simple ESC
                        return None
                    # For arrow keys in escape sequences, ignore for now
                    continue
                
                elif char == '\x7f' or char == '\b':  # Backspace
                    if cursor_pos > 0:
                        editing_message = editing_message[:cursor_pos-1] + editing_message[cursor_pos:]
                        cursor_pos -= 1
                
                elif char == '\x03':  # Ctrl+C - cancel
                    return None
                
                elif len(char) == 1 and ord(char) >= 32:  # Printable character
                    editing_message = editing_message[:cursor_pos] + char + editing_message[cursor_pos:]
                    cursor_pos += 1
                    
            except KeyboardInterrupt:
                return None
    
    def _display_table_with_inline_editing(self, commits: List[Dict[str, str]], selected_index: int, editing_index: int, editing_message: str = "", cursor_pos: int = 0):
        """Display table with real-time inline editing."""
        # Create a copy of commits with the editing message
        display_commits = commits.copy()
        if editing_index >= 0:
            display_commits[editing_index] = display_commits[editing_index].copy()
            # Show current editing state with cursor
            before_cursor = editing_message[:cursor_pos]
            after_cursor = editing_message[cursor_pos:]
            display_commits[editing_index]["message"] = f"{before_cursor}▋{after_cursor}"
        
        table_lines = len(commits) + 5
        
        # Generate the table with current editing state
        table = self.show_atomic_commits_preview(display_commits, selected_index, editing_index)
        
        # Clear and redraw table area  
        print(f"\033[{table_lines}A", end="")
        print("\033[0J", end="")  # Clear from cursor to end
        
        self.console.print(table, end="")
        print()
    
    def _get_char(self) -> str:
        """Get a single character from stdin without pressing Enter."""
        try:
            if os.name == 'nt':  # Windows
                import msvcrt
                return msvcrt.getch().decode('utf-8')
            else:  # Unix/Linux/macOS
                import termios, tty
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)  # Use setcbreak instead of cbreak
                    ch = sys.stdin.read(1)
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                return ch
        except (ImportError, OSError, AttributeError):
            # Fallback: use input() for systems without termios/msvcrt or in environments like IDEs
            self.console.print("[yellow]Interactive navigation not supported in this environment.[/yellow]")
            self.console.print("[yellow]Using simplified input mode...[/yellow]")
            return input("Press Enter to continue or 'c' to cancel: ")[0:1] or '\r'
    
    def interactive_atomic_commits_approval(self, commits: List[Dict[str, str]], start_index: int = 0) -> tuple[str, int]:
        """Interactive approval with arrow key navigation, fallback to simple mode if needed."""
        # Check if terminal supports interactive mode
        try:
            import termios, tty
            fd = sys.stdin.fileno()
            termios.tcgetattr(fd)  # Test if we can get terminal attributes
        except (ImportError, OSError, AttributeError, termios.error):
            # Fall back to simplified approval
            return self._simplified_approval(commits)
        
        selected_index = start_index  # Start with specified commit selected
        commit_count = len(commits)
        
        # Instructions panel
        instructions = Panel(
            "[bold yellow]Navigation:[/bold yellow]\n"
            "  [cyan]↑/↓[/cyan] - Navigate through commit messages\n"
            "  [green]ENTER[/green] - Edit selected commit message\n"
            "  [blue]TAB + ENTER[/blue] - Accept all and continue\n"
            "  [red]c[/red] - Cancel (no commits)",
            title="Interactive Commit Review",
            style="yellow"
        )
        
        # Clear screen and show initial state
        self.console.clear()
        self.console.print("\n[bold blue]Proposed Atomic Commits[/bold blue]\n")
        self.console.print(instructions)
        self.console.print()
        
        # Show initial table
        self._display_table_with_selection(commits, selected_index)
        
        last_update_time = time.time()
        
        while True:
            # Get user input
            try:
                char = self._get_char()
                
                if char == '\x1b':  # Escape sequence (arrow keys)
                    char += self._get_char()  # Get [
                    char += self._get_char()  # Get direction
                    
                    if char == '\x1b[A':  # Up arrow
                        new_index = max(0, selected_index - 1)
                        if new_index != selected_index:
                            selected_index = new_index
                            # Much lighter throttle since we're not clearing screen
                            current_time = time.time()
                            if current_time - last_update_time > 0.02:  # 20ms throttle
                                self._display_table_with_selection(commits, selected_index)
                                last_update_time = current_time
                    elif char == '\x1b[B':  # Down arrow  
                        new_index = min(commit_count - 1, selected_index + 1)
                        if new_index != selected_index:
                            selected_index = new_index
                            # Much lighter throttle since we're not clearing screen
                            current_time = time.time()
                            if current_time - last_update_time > 0.02:  # 20ms throttle
                                self._display_table_with_selection(commits, selected_index)
                                last_update_time = current_time
                
                elif char == '\r' or char == '\n':  # Enter key (try both)
                    # Enter inline editing mode
                    return "edit", selected_index
                
                elif char == '\t':  # Tab key - check for Tab+Enter
                    self.console.print("\n[yellow]Press ENTER to accept all commits...[/yellow]")
                    next_char = self._get_char()
                    if next_char == '\r' or next_char == '\n':  # Enter after Tab
                        return "approve", -1
                    # If not Enter, redraw table
                    self._display_table_with_selection(commits, selected_index)
                
                elif char.lower() == 'c':  # Cancel
                    return "cancel", -1
                
                elif char == '\x03':  # Ctrl+C
                    return "cancel", -1
                    
            except KeyboardInterrupt:
                return "cancel", -1
    
    def _display_table_with_selection(self, commits: List[Dict[str, str]], selected_index: int):
        """Display table with current selection using minimal cursor positioning."""
        # Use more efficient cursor positioning - only redraw the table area
        # Move to beginning of table, clear to end of screen, then redraw
        table_lines = len(commits) + 5
        
        # Generate the table content first (double buffering)
        table = self.show_atomic_commits_preview(commits, selected_index)
        
        # Now do minimal screen update - move cursor up and clear from there down
        print(f"\033[{table_lines}A", end="")  # Move cursor up
        print("\033[0J", end="")  # Clear from cursor to end of screen
        
        # Print the pre-generated table
        self.console.print(table, end="")
        print()  # Add final newline
    
    def _simplified_approval(self, commits: List[Dict[str, str]]) -> tuple[str, int]:
        """Simplified approval for environments that don't support interactive navigation."""
        self.console.print("\n[bold blue]Proposed Atomic Commits[/bold blue]\n")
        table = self.show_atomic_commits_preview(commits)
        self.console.print(table)
        self.console.print()
        
        options_text = (
            "[bold yellow]Options:[/bold yellow]\n"
            "  [green]ENTER[/green] - Accept all messages and create commits\n"
            f"  [cyan]1-{len(commits)}[/cyan] - Edit specific commit message\n"
            "  [red]c[/red] - Cancel (no commits will be made)"
        )
        
        self.console.print(Panel(options_text, title="Choose Action", style="yellow"))
        
        while True:
            choice = Prompt.ask(
                f"Your choice",
                choices=[""] + [str(i) for i in range(1, len(commits) + 1)] + ["c", "C"],
                default="",
                show_choices=False
            )
            
            if choice == "":
                return "approve", -1
            elif choice.lower() == "c":
                return "cancel", -1
            elif choice.isdigit() and 1 <= int(choice) <= len(commits):
                return "edit", int(choice) - 1
            else:
                self.console.print("[red]Invalid choice. Please try again.[/red]")
    
    def prompt_commit_message_edit(self, current_message: str, file_path: str) -> Optional[str]:
        """Prompt user to edit a commit message with pre-filled content."""
        self.console.print(f"\n[bold blue]Editing commit for:[/bold blue] [yellow]{file_path}[/yellow]")
        self.console.print(f"[muted]Use backspace to edit from the end, or clear and retype[/muted]\n")
        
        # Try using readline for pre-filled input if available
        try:
            import readline
            
            def prefill_input(prompt_text: str, prefill_text: str) -> str:
                def hook():
                    readline.insert_text(prefill_text)
                    readline.redisplay()
                
                readline.set_pre_input_hook(hook)
                try:
                    result = input(prompt_text)
                finally:
                    readline.set_pre_input_hook()
                return result
            
            new_message = prefill_input(f"Commit message ({current_message}): ", current_message)
            
        except (ImportError, OSError):
            # Fallback: show current message and ask for new one
            self.console.print(f"[bold]Current message:[/bold] {current_message}")
            new_message = Prompt.ask(
                "[bold]New commit message (or press ENTER to keep current)[/bold]",
                default=current_message
            )
        
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
    
    def show_security_scan_results(self, scan_result: Dict[str, Any]) -> None:
        """Display security scan results."""
        if not scan_result["scanner_available"]:
            return
        
        if not scan_result["scan_performed"]:
            self.print_warning("Security scan skipped due to error")
            return
        
        if not scan_result["secrets_found"]:
            self.print_success("Security scan passed - no secrets detected")
            return
        
        # Show security warning
        self.console.print()
        self.console.print("[bold red]🔒 Security Alert: Potential secrets detected![/bold red]")
        
        # Create table for findings
        table = Table(
            title="Security Scan Results",
            box=box.ROUNDED,
            title_style="bold red"
        )
        table.add_column("File", style="bold")
        table.add_column("Line", style="cyan")
        table.add_column("Detector", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Preview", style="dim")
        
        for finding in scan_result["findings"]:
            status = "✅ Verified" if finding["verified"] else "⚠️ Unverified"
            preview = finding["raw"][:50] + "..." if len(finding["raw"]) > 50 else finding["raw"]
            
            table.add_row(
                finding["file"],
                str(finding["line"]),
                finding["detector"],
                status,
                preview
            )
        
        self.console.print(table)
        self.console.print()
    
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
    
    def prompt_branch_protection_choice(self, options: List[str]) -> int:
        """Prompt user to choose from branch protection options."""
        from rich.prompt import IntPrompt
        
        self.console.print("\n[bold yellow]Choose an option:[/bold yellow]")
        for i, option in enumerate(options):
            style = "green" if i == 0 else "blue"
            self.console.print(f"  [{i}] [{style}]{option}[/{style}]")
        
        while True:
            try:
                choice = IntPrompt.ask(
                    "Enter your choice",
                    default=0,
                    choices=[str(i) for i in range(len(options))]
                )
                return choice
            except (KeyboardInterrupt, EOFError):
                return len(options) - 1  # Return cancel option
    
    def edit_branch_name(self, suggested_name: str) -> Optional[str]:
        """Edit branch name with validation using Rich input."""
        import re
        
        self.console.print(f"\n[green]Suggested branch name:[/green] {suggested_name}")
        
        while True:
            try:
                branch_name = Prompt.ask(
                    "Edit branch name (or press Enter to use suggestion)",
                    default=suggested_name
                )
                
                # Validate branch name
                if not branch_name:
                    return None
                
                # Check for invalid characters
                if re.search(r'[^\w/.-]', branch_name):
                    self.console.print("[red]Error:[/red] Branch name contains invalid characters. Use only letters, numbers, hyphens, underscores, slashes, and periods.")
                    continue
                
                # Check for spaces
                if ' ' in branch_name:
                    self.console.print("[red]Error:[/red] Branch name cannot contain spaces. Use hyphens instead.")
                    continue
                
                # Check length (Git's actual limit is 255 chars, but keep it reasonable)
                if len(branch_name) > 100:
                    self.console.print("[red]Error:[/red] Branch name is too long (max 100 characters for readability).")
                    continue
                
                # Check for valid format
                if not re.match(r'^[\w.-]+(/[\w.-]+)*$', branch_name):
                    self.console.print("[red]Error:[/red] Invalid branch name format. Use format: type/description")
                    continue
                
                return branch_name
                
            except (KeyboardInterrupt, EOFError):
                return None
    
    def select_existing_branch(self, branches: List[str]) -> Optional[str]:
        """Select from existing branches with interactive interface."""
        if not branches:
            return None
        
        self.console.print("\n[bold blue]Available branches:[/bold blue]")
        
        for i, branch in enumerate(branches[:10]):  # Limit to 10 most recent
            self.console.print(f"  [{i}] [cyan]{branch}[/cyan]")
        
        if len(branches) > 10:
            self.console.print(f"  ... and {len(branches) - 10} more branches")
        
        while True:
            try:
                from rich.prompt import IntPrompt
                choice = IntPrompt.ask(
                    "Select branch",
                    choices=[str(i) for i in range(min(len(branches), 10))]
                )
                return branches[choice]
            except (KeyboardInterrupt, EOFError):
                return None