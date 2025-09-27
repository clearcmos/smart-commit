# Smart Commit v2.1.0 - Development Guide

This document provides context for AI assistants working on the Smart Git Commit Tool v2.1.0 Python rewrite.

## Project Overview

A complete rewrite of the intelligent bash script in professional Python, featuring enterprise-grade architecture, beautiful CLI interface, and production-ready code quality. The tool analyzes git changes and generates meaningful commit messages using dual AI backends (Ollama and llama.cpp) with automatic detection and cross-platform support.

## Architecture

### Core Philosophy
- **Single Responsibility**: Each module has a clear, focused purpose
- **Dependency Injection**: All components are loosely coupled via interfaces
- **Async/Await**: All I/O operations use modern async patterns
- **Type Safety**: Full type hints and mypy compliance
- **Error Handling**: Comprehensive error handling with custom exceptions

### Project Structure

```
smart_commit/
├── __init__.py              # Package initialization and exports
├── cli.py                   # Typer-based CLI with Rich integration
├── core.py                  # Main application engine and orchestration
├── config/
│   ├── __init__.py
│   └── settings.py          # Pydantic settings with validation
├── ai_backends/
│   ├── __init__.py
│   ├── base.py              # Abstract backend interface
│   ├── ollama.py            # Ollama implementation
│   ├── llamacpp.py          # llama.cpp implementation
│   └── factory.py           # Backend factory with auto-detection
├── git_ops/
│   ├── __init__.py
│   └── repository.py        # Git operations with GitPython
├── ui/
│   ├── __init__.py
│   └── console.py           # Rich-based console interface
└── utils/
    ├── __init__.py
    ├── message_extractor.py  # AI response processing
    └── prompts.py            # Prompt engineering and templates
```

## Key Components

### 1. CLI Interface (`cli.py`)
- **Framework**: Typer with Rich markup support
- **Pattern**: Callback-based with default action
- **Features**: 
  - Default action is atomic commits
  - Branch protection for main/master branches
  - AI-generated branch names with interactive editing
  - Global options apply to default action
  - Subcommands for configuration and testing
  - Automatic help generation with examples

#### CLI Design Pattern
```python
@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context, ...):
    """Main command with global options."""
    if ctx.invoked_subcommand is None:
        # Run default action (commit workflow)
        asyncio.run(_run_commit(...))

@app.command()
def config(...):
    """Configuration subcommand."""
    pass
```

### 2. Core Engine (`core.py`)
- **Class**: `SmartCommit` - Main application orchestrator
- **Pattern**: Facade pattern coordinating all subsystems
- **Responsibilities**:
  - Initialize and coordinate all components
  - Manage application lifecycle
  - Handle both traditional and atomic commit workflows (atomic is default)
  - Branch protection and AI-powered branch name generation
  - Interactive branch selection and creation
  - Error handling and user feedback

#### Key Methods
```python
async def initialize() -> None:
    """Initialize AI backend and validate setup."""

async def run_traditional_commit(dry_run: bool, force_branch: bool, new_branch_name: str, switch_to_branch: str) -> None:
    """Single commit workflow with branch protection."""

async def run_atomic_commits(dry_run: bool, force_branch: bool, new_branch_name: str, switch_to_branch: str) -> None:
    """Atomic commits workflow (one per file) - default behavior."""

async def _check_branch_protection(new_branch_name: str, switch_to_branch: str) -> str:
    """Check branch protection and handle accordingly."""

async def _generate_branch_name(file_changes: List[FileChange]) -> str:
    """Generate AI-powered branch name based on changes."""
```

### 3. Configuration System (`config/settings.py`)
- **Framework**: Pydantic v2 with BaseSettings
- **Features**:
  - Environment variable support with prefix
  - Nested configuration objects
  - Validation with custom validators
  - Legacy migration from bash version
  - Cross-platform paths

#### Configuration Structure
```python
class Settings(BaseSettings):
    ai: AISettings              # AI backend configuration
    git: GitSettings            # Git operation settings
    ui: UISettings              # User interface preferences
    performance: PerformanceSettings  # Optimization settings
```

#### Environment Variable Mapping
- `SC_AI__API_URL` → `settings.ai.api_url`
- `SC_AI__MODEL` → `settings.ai.model`
- `SC_AI__BACKEND_TYPE` → `settings.ai.backend_type`
- `SC_GIT__PROTECTED_BRANCHES` → `settings.git.protected_branches`
- `SC_GIT__ATOMIC_MODE` → `settings.git.atomic_mode` (default: true)
- Legacy: `OLLAMA_API_URL` → automatically migrated

### 4. AI Backend System (`ai_backends/`)

#### Abstract Interface (`base.py`)
```python
class AIBackend(ABC):
    @abstractmethod
    async def call_api(self, prompt: str) -> AIResponse:
        """Call the AI API with retry logic."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check backend health."""
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models."""
```

#### Backend Implementations
- **OllamaBackend**: Uses `/api/generate` endpoint
- **LlamaCppBackend**: Uses `/v1/completions` (OpenAI-compatible)
- **Factory Pattern**: Auto-detection via health checks

#### Auto-Detection Strategy
1. Check explicit `AI_BACKEND_TYPE` setting
2. Probe `/health` endpoint (llama.cpp)
3. Probe `/api/tags` endpoint (Ollama)
4. Fallback to configured default

### 5. Git Operations (`git_ops/repository.py`)
- **Library**: GitPython for robust Git operations
- **Pattern**: Repository pattern with rich error handling
- **Features**:
  - Comprehensive repository state analysis
  - File change tracking with metadata
  - Smart diff truncation for large files
  - Remote tracking and push operations

#### Key Data Classes
```python
@dataclass
class FileChange:
    file_path: str
    change_type: str  # 'M', 'A', 'D', 'R', 'C'
    diff_content: str
    lines_added: int
    lines_removed: int
    
    @property
    def scope(self) -> Optional[str]:
        """Extract conventional commit scope from file path."""

@dataclass
class RepositoryState:
    has_changes: bool
    staged_files: List[FileChange]
    unstaged_files: List[FileChange]
    untracked_files: List[str]
    current_branch: str
    remote_branch: Optional[str]
    commits_ahead: int
    commits_behind: int
```

### 6. User Interface (`ui/console.py`)
- **Framework**: Rich for beautiful terminal output
- **Features**:
  - Colored output with consistent theming
  - Progress bars and spinners
  - Interactive prompts and confirmations
  - Table-based data display
  - Syntax highlighting for diffs

#### UI Components
```python
def show_atomic_commits_preview(self, commits: List[Dict[str, str]]) -> None:
    """Show atomic commits in beautiful table format."""

def prompt_atomic_commits_approval(self, commit_count: int) -> str:
    """Interactive approval workflow."""

def show_progress_bar(self, total: int, description: str):
    """Progress tracking for multi-step operations."""
```

### 7. Message Processing (`utils/`)

#### Message Extractor (`message_extractor.py`)
- **Purpose**: Extract and clean commit messages from AI responses
- **Strategies**: Multiple extraction patterns with fallbacks
- **Features**:
  - Markdown cleaning (removes code blocks)
  - Conventional commit pattern matching with flexible whitespace
  - Smart truncation with word boundaries
  - Intelligent fallbacks for malformed responses

#### Validation Features
- **Flexible regex patterns**: `\s*` for colon spacing tolerance
- **Enhanced AI response handling**: Supports various conventional commit formats
- **Improved success rates**: High validation success rate for commit messages
- **Enhanced whitespace tolerance**: Handles AI responses with or without spaces after colons

#### Prompt Builder (`prompts.py`)
- **Purpose**: Generate optimized prompts for different scenarios
- **Modes**: 
  - Optimized mode (fast, for macOS local)
  - Detailed mode (comprehensive analysis)
- **Context**: File-specific vs repository-wide prompts

## Workflow Patterns

### Atomic Commits Workflow (Default)
1. **Initialize**: Load settings, create AI backend, validate Git repo
2. **Branch Protection**: Check if on protected branch (main/master)
   - If protected: Prompt user to create new branch, switch branch, or force commit
   - Generate AI-powered branch name if creating new branch
   - Interactive branch name editing with validation
3. **Analyze**: Get all changed files individually  
4. **Generate**: Create commit message for each file in parallel
5. **Preview**: Show all proposed commits in table format
6. **Approve**: Interactive workflow with editing capability
7. **Commit**: Create individual commits sequentially
8. **Push**: Push all commits together

### Traditional Commit Workflow (Non-Atomic)
1. **Initialize**: Load settings, create AI backend, validate Git repo
2. **Branch Protection**: Same as atomic workflow
3. **Analyze**: Get repository state, file changes, recent commits
4. **Stage**: Auto-stage files if configured
5. **Generate**: Create single commit message using AI backend
6. **Preview**: Show message with Rich formatting
7. **Confirm**: Interactive approval (if enabled)
8. **Commit**: Create Git commit
9. **Push**: Push to remote (if configured)

### Error Handling Strategy
- **Custom Exceptions**: `SmartCommitError` for application errors
- **Graceful Degradation**: Fallbacks for AI failures
- **User Feedback**: Rich error messages with context
- **Logging**: Comprehensive logging with Loguru

## Configuration Management

### Settings Hierarchy
1. **Command-line arguments** (highest priority)
2. **Environment variables** (`SC_*` prefix)
3. **Configuration file** (`~/.config/smart-commit/config.json`)
4. **Defaults** (lowest priority)

### Cross-Platform Support
- **Config Directory**: 
  - Linux/macOS: `~/.config/smart-commit/`
  - Windows: `%APPDATA%\smart-commit\`
- **Cache Directory**:
  - Linux/macOS: `~/.cache/smart-commit/`
  - Windows: `%LOCALAPPDATA%\smart-commit\`

### Legacy Migration
- Automatic detection of bash version environment variables
- Conversion of `OLLAMA_*` to `SC_AI__*` format
- Backend type detection from legacy settings
- Performance flag migration

## Performance Optimization

### Current Performance Features
- **High Validation Success Rate**: Reliable commit message generation
- **Optimized Processing**: Efficient atomic commit handling
- **Enhanced Error Recovery**: Robust handling of AI response variations
- **Improved User Experience**: Consistent and reliable operation

### Async Architecture
- All I/O operations use `async/await`
- Parallel message generation for atomic commits
- Non-blocking UI updates during long operations

### Memory Management
- Streaming JSON parsing for large responses
- Intelligent diff truncation
- Connection pooling with aiohttp

### Platform-Specific Optimizations
- **macOS Local Mode**: Simplified prompts for mobile GPUs
- **Adaptive Timeouts**: Based on content complexity
- **Progressive Truncation**: Smart content reduction

## Testing and Quality

### Code Quality Tools
- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **ruff**: Fast linting
- **pytest**: Testing framework with coverage

### Testing Strategy
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Mock Testing**: AI backend mocking for reliable tests
- **Configuration Tests**: Settings validation testing

## Installation and Deployment

### Package Structure
- **pyproject.toml**: Modern Python packaging
- **Entry Points**: CLI commands (`smart-commit`, `sc`)
- **Dependencies**: Clearly defined with version constraints
- **Development Dependencies**: Separate dev requirements

### Installation Methods
1. **Automated Installer**: `python3 install.py`
   - Creates virtual environment
   - Installs dependencies
   - Migrates configuration
   - Creates shell integration
2. **pip install**: Direct installation
3. **pipx install**: Isolated installation

### Distribution
- **PyPI Ready**: Proper metadata and classifiers
- **Cross-Platform**: Windows, macOS, Linux support
- **Python Versions**: 3.9+ support

## Development Guidelines

### Code Style
- **Type Hints**: All functions must have type annotations
- **Docstrings**: Google-style docstrings for all public APIs
- **Error Handling**: Use custom exceptions with context
- **Logging**: Use structured logging with appropriate levels
- **Async**: Prefer async/await for I/O operations

### Adding New Features

#### New AI Backend
1. Implement `AIBackend` abstract class
2. Add health check logic
3. Register in `BackendFactory`
4. Add configuration options
5. Write tests with mocking

#### New Configuration Option
1. Add to appropriate settings class
2. Update environment variable mapping
3. Add validation if needed
4. Update documentation
5. Consider migration path

#### New CLI Command
1. Add to `cli.py` with Typer decorators
2. Implement async handler function
3. Add help text and examples
4. Update main documentation

### Testing New Components
```python
# Example test structure
class TestAIBackend:
    async def test_health_check(self, mock_backend):
        result = await mock_backend.health_check()
        assert result is True
    
    async def test_api_call_with_retry(self, mock_backend):
        response = await mock_backend.call_with_retry("test prompt")
        assert response.content != ""
```

## Common Issues and Solutions

### Development Issues

**Import Errors**:
- Ensure virtual environment is activated
- Check that package is installed in development mode (`pip install -e .`)
- Verify Python path includes project directory

**Type Checking Failures**:
- Run `mypy smart_commit/` to check types
- Ensure all functions have proper type hints
- Use `# type: ignore` sparingly with comments

**Async/Await Issues**:
- Ensure async functions are awaited
- Use `asyncio.run()` for top-level async calls
- Don't mix sync and async code without proper handling

### Configuration Issues

**Settings Not Loading**:
- Check environment variable names (`SC_` prefix)
- Verify configuration file location
- Use `smart-commit config --show` to debug

**Backend Detection Failures**:
- Test individual backends with `smart-commit test --all`
- Check health endpoints manually with curl
- Verify API URLs and ports

### Performance Issues

**Slow Message Generation**:
- Check AI backend response times
- Consider using optimized mode
- Verify network connectivity to AI servers

**Memory Usage**:
- Check diff size limits in configuration
- Monitor log file size
- Consider reducing max_diff_lines setting

## Future Enhancements

### Planned Features
- **Additional AI Backends**: OpenAI, Anthropic Claude
- **Plugin System**: External backend plugins
- **Configuration UI**: Web-based configuration interface
- **Git Hooks Integration**: Pre-commit hook support
- **Template System**: Customizable commit message templates

### Architecture Improvements
- **Caching System**: Intelligent prompt and response caching
- **Metrics Collection**: Usage analytics and performance monitoring
- **Configuration Validation**: Schema-based config validation
- **Multi-Repository Support**: Workspace-level configuration

### Quality Improvements
- **Comprehensive Testing**: High test coverage
- **Documentation**: API documentation with Sphinx
- **Performance Benchmarking**: Automated performance testing
- **Security Audit**: Dependency vulnerability scanning

This architecture provides a solid foundation for future development while maintaining the core functionality that makes the tool valuable.