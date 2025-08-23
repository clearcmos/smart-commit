"""
Beautiful CLI interface using Typer with Rich integration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from loguru import logger

from .core import SmartCommit, SmartCommitError
from .config.settings import Settings
from .ai_backends.factory import BackendFactory


# Create Typer app
app = typer.Typer(
    name="smart-commit",
    help="AI-powered Git commit message generator with dual backend support",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=False  # Allow default command
)

# Global console for error handling
console = Console()


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None):
    """Setup logging configuration."""
    logger.remove()  # Remove default handler
    
    # Console logging with colors
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # File logging
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="1 MB",
            retention="7 days"
        )


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", 
        help="Preview commit message without creating commit"
    ),
    atomic: bool = typer.Option(
        False, "--atomic", "-a",
        help="Create one commit per modified file"
    ),
    no_push: bool = typer.Option(
        False, "--no-push", "-np",
        help="Create commits but don't push to remote"
    ),
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to configuration file"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Enable verbose logging"
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d",
        help="Enable debug logging (includes verbose)"
    ),
    repo_path: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Git repository path (default: current directory)"
    ),
    version: bool = typer.Option(
        False, "--version",
        help="Show version information"
    )
):
    """
    AI-powered Git commit message generator with dual backend support.
    
    [bold blue]Examples:[/bold blue]
    
    [green]smart-commit[/green]                           # Standard commit workflow
    [green]smart-commit --dry-run[/green]                 # Preview without committing  
    [green]smart-commit --atomic[/green]                  # One commit per file
    [green]smart-commit --atomic --dry-run[/green]        # Preview atomic commits
    [green]smart-commit --atomic --no-push[/green]        # Create commits without pushing
    [green]smart-commit --atomic --verbose[/green]        # Verbose logging
    [green]smart-commit --atomic --debug[/green]          # Full debug logging
    [green]smart-commit config --show[/green]             # Show configuration
    [green]smart-commit test[/green]                      # Test AI backend
    [green]smart-commit cache-stats[/green]               # Show cache performance
    [green]smart-commit clear-cache[/green]               # Clear scope cache
    
    [bold blue]Flags:[/bold blue]
    [green]--no-push[/green]                              # Create commits but don't push to remote
    """
    if version:
        from . import __version__
        console.print(f"[bold blue]Smart Commit[/bold blue] version [green]{__version__}[/green]")
        return
    
    # If no subcommand was called, run the default commit workflow
    if ctx.invoked_subcommand is None:
        asyncio.run(_run_commit(dry_run, atomic, no_push, config_file, verbose, debug, repo_path))


@app.command()
def config(
    show: bool = typer.Option(
        False, "--show", "-s",
        help="Show current configuration"
    ),
    backend_type: Optional[str] = typer.Option(
        None, "--backend", "-b",
        help="Set AI backend type (ollama, llamacpp, auto)"
    ),
    api_url: Optional[str] = typer.Option(
        None, "--url", "-u", 
        help="Set AI API URL"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Set AI model name"
    ),
    save: bool = typer.Option(
        False, "--save", 
        help="Save configuration to file"
    )
):
    """
    Manage Smart Commit configuration.
    
    [bold blue]Examples:[/bold blue]
    
    [green]smart-commit config --show[/green]                                    # Show current config
    [green]smart-commit config --backend ollama --save[/green]                  # Set backend to Ollama
    [green]smart-commit config --url http://localhost:8080 --backend llamacpp[/green] # Configure llama.cpp
    """
    asyncio.run(_run_config(show, backend_type, api_url, model, save))


@app.command()
def cache_stats():
    """Show scope cache performance statistics."""
    try:
        from smart_commit.core import SmartCommit
        import asyncio
        
        async def show_cache_stats():
            smart_commit = SmartCommit()
            await smart_commit.initialize()
            
            if hasattr(smart_commit.ai_backend, 'get_cache_stats'):
                stats = smart_commit.ai_backend.get_cache_stats()
                
                console.print("\n[bold blue]Scope Cache Statistics[/bold blue]")
                console.print(f"Cache Size: {stats['cache_size']}")
                console.print(f"Max Size: {stats['max_size']}")
                console.print(f"Cache Hits: {stats['cache_hits']}")
                console.print(f"Cache Misses: {stats['cache_misses']}")
                console.print(f"Hit Rate: {stats['hit_rate']:.1%}")
                
                if stats['cache_hits'] > 0:
                    console.print(f"\n[green]Performance: Cache is working efficiently![/green]")
                else:
                    console.print(f"\n[yellow]Performance: Cache is still warming up...[/yellow]")
            else:
                console.print("[yellow]Cache statistics not available for this backend[/yellow]")
        
        asyncio.run(show_cache_stats())
        
    except Exception as e:
        console.print(f"[red]Error getting cache stats: {e}[/red]")


@app.command()
def clear_cache():
    """Clear the scope cache."""
    try:
        from smart_commit.core import SmartCommit
        import asyncio
        
        async def clear_scope_cache():
            smart_commit = SmartCommit()
            await smart_commit.initialize()
            
            if hasattr(smart_commit.ai_backend, 'clear_scope_cache'):
                smart_commit.ai_backend.clear_scope_cache()
                console.print("[green]Scope cache cleared successfully![/green]")
            else:
                console.print("[yellow]Cache clearing not available for this backend[/yellow]")
        
        asyncio.run(clear_scope_cache())
        
    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")


@app.command()
def test(
    backend: Optional[str] = typer.Option(
        None, "--backend", "-b",
        help="Test specific backend (ollama, llamacpp)"
    ),
    all_backends: bool = typer.Option(
        False, "--all", "-a",
        help="Test all available backends"
    )
):
    """
    Test AI backend connectivity and functionality.
    
    [bold blue]Examples:[/bold blue]
    
    [green]smart-commit test[/green]                      # Test configured backend
    [green]smart-commit test --backend ollama[/green]     # Test Ollama specifically  
    [green]smart-commit test --all[/green]                # Test all backends
    """
    asyncio.run(_run_test(backend, all_backends))




async def _run_commit(
    dry_run: bool, 
    atomic: bool, 
    no_push: bool,
    config_file: Optional[Path],
    verbose: bool,
    debug: bool,
    repo_path: Optional[Path]
):
    """Run commit command."""
    try:
        # Load settings
        if config_file:
            settings = Settings.from_file(config_file)
        else:
            settings = Settings()
        
        # Setup logging - debug overrides verbose
        if debug:
            log_level = "DEBUG"
        elif verbose:
            log_level = "INFO"
        else:
            log_level = settings.ui.log_level
        setup_logging(log_level, settings.log_file)
        
        # Create and initialize Smart Commit
        smart_commit = SmartCommit(settings, repo_path)
        smart_commit.console.print_banner()
        
        # Show backend info
        await smart_commit.initialize()
        smart_commit.console.show_ai_backend_info(
            smart_commit.ai_backend.backend_type,
            smart_commit.ai_backend.api_url,
            smart_commit.ai_backend.model
        )
        
        # Override auto_push setting if --no-push flag is used
        if no_push:
            smart_commit.settings.git.auto_push = False
            smart_commit.console.print_info("Auto-push disabled (--no-push flag used)")
        
        # Run appropriate workflow
        if atomic:
            await smart_commit.run_atomic_commits(dry_run)
        else:
            await smart_commit.run_traditional_commit(dry_run)
            
    except SmartCommitError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        console.print(f"[red]Unexpected error:[/red] {e}")
        raise typer.Exit(1)


async def _run_config(
    show: bool,
    backend_type: Optional[str],
    api_url: Optional[str], 
    model: Optional[str],
    save: bool
):
    """Run config command."""
    try:
        settings = Settings()
        
        # Show current configuration
        if show:
            smart_commit = SmartCommit(settings)
            smart_commit.show_configuration()
            return
        
        # Update settings
        config_changed = False
        
        if backend_type:
            if backend_type not in ["ollama", "llamacpp", "auto"]:
                console.print(f"[red]Invalid backend type:[/red] {backend_type}")
                console.print("Valid options: ollama, llamacpp, auto")
                raise typer.Exit(1)
            settings.ai.backend_type = backend_type
            config_changed = True
            console.print(f"[green]Set backend type to:[/green] {backend_type}")
        
        if api_url:
            settings.ai.api_url = api_url
            config_changed = True
            console.print(f"[green]Set API URL to:[/green] {api_url}")
        
        if model:
            settings.ai.model = model
            config_changed = True
            console.print(f"[green]Set model to:[/green] {model}")
        
        # Save if requested
        if save and config_changed:
            config_path = settings.config_dir / "config.json"
            settings.save_to_file(config_path)
            console.print(f"[green]Configuration saved to:[/green] {config_path}")
        elif config_changed:
            console.print("[yellow]Use --save to persist these changes[/yellow]")
        
        if not config_changed:
            console.print("[yellow]No configuration changes made[/yellow]")
            console.print("Use [green]--show[/green] to see current configuration")
            
    except Exception as e:
        console.print(f"[red]Configuration error:[/red] {e}")
        raise typer.Exit(1)


async def _run_test(backend: Optional[str], all_backends: bool):
    """Run test command."""
    try:
        settings = Settings()
        
        if all_backends:
            # Test all backend types
            console.print("[bold blue]Testing all AI backends...[/bold blue]")
            results = await BackendFactory.test_all_backends(settings)
            
            for backend_type, status in results.items():
                status_text = "[green]✓ Available[/green]" if status else "[red]✗ Unavailable[/red]"
                console.print(f"  {backend_type.title()}: {status_text}")
        
        elif backend:
            # Test specific backend
            if backend not in BackendFactory.list_supported_backends():
                console.print(f"[red]Unsupported backend:[/red] {backend}")
                console.print(f"Supported: {', '.join(BackendFactory.list_supported_backends())}")
                raise typer.Exit(1)
            
            # Temporarily override backend type
            test_settings = Settings()
            test_settings.ai.backend_type = backend
            
            smart_commit = SmartCommit(test_settings)
            success = await smart_commit.test_ai_backend()
            
            if not success:
                raise typer.Exit(1)
        
        else:
            # Test configured backend with enhanced diagnostics
            smart_commit = SmartCommit(settings)
            
            console.print("[bold blue]Testing configured AI backend...[/bold blue]")
            
            # Basic backend test
            success = await smart_commit.test_ai_backend()
            
            if success and hasattr(smart_commit.ai_backend, 'test_connection'):
                console.print("\n[bold blue]Running detailed connection diagnostics...[/bold blue]")
                try:
                    connection_results = await smart_commit.ai_backend.test_connection()
                    
                    console.print("\n[bold]Connection Test Results:[/bold]")
                    console.print(f"  Health Check: {'✅' if connection_results['health_check'] else '❌'}")
                    console.print(f"  Model List: {'✅' if connection_results['model_list'] else '❌'}")
                    console.print(f"  Completion Test: {'✅' if connection_results['completion_test'] else '❌'}")
                    console.print(f"  Response Quality: {connection_results['response_quality']}")
                    
                    if connection_results['response_quality'] == 'poor':
                        console.print("\n[yellow]Warning:[/yellow] Response quality is poor. This may cause commit message generation issues.")
                        console.print("Consider checking your remote server configuration or model loading.")
                    
                except Exception as e:
                    console.print(f"[yellow]Detailed diagnostics failed:[/yellow] {e}")
            
            if not success:
                raise typer.Exit(1)
                
    except Exception as e:
        console.print(f"[red]Test failed:[/red] {e}")
        raise typer.Exit(1)


def main():
    """Main entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()