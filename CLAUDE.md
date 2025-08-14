# Smart Git Commit Tool - Development Guide

This document provides context for AI assistants working on the Smart Git Commit Tool project.

## Project Overview

An intelligent bash script that analyzes git changes and generates meaningful commit messages using AI via Ollama. The tool supports both local and remote Ollama setups with automatic performance optimizations for different platforms.

## Architecture

### Core Components

1. **setup** - Interactive setup script for configuration
2. **smart-commit.sh** - Main commit message generation script
3. **Environment-based configuration** - Uses shell environment variables
4. **Platform-specific optimizations** - Different behavior for macOS/Linux/remote

### Key Files

- `setup` - Handles Ollama installation, configuration, and environment setup
- `smart-commit.sh` - Main script with dual-mode operation (optimized/full)
- `README.md` - User documentation
- `CLAUDE.md` - This development guide

## Setup Script (`setup`)

### Features
- **OS Detection**: Automatically detects macOS/Linux
- **Installation Options**: 
  1. Local Ollama (with automatic installation)
  2. Remote Ollama (connect to existing server)
  3. Keep current configuration
- **Idempotent Operations**: Safe to re-run, skips completed steps
- **Cross-platform Compatibility**: Uses `grep -v` instead of `sed -i` for shell profile editing

### Key Functions
- `check_ollama_installed()` - Detects if Ollama is available
- `check_ollama_running()` - Tests if Ollama service is responding
- `check_qwen3_model()` - Verifies qwen3:8b model availability
- `install_ollama()` - Handles installation via Homebrew/curl
- `setup_local_ollama()` - Complete local setup with optimization flags
- `setup_remote_ollama()` - Remote server configuration

### Environment Variables Set
- `OLLAMA_API_URL` - Server endpoint (localhost:11434 or remote IP)
- `OLLAMA_MODEL` - AI model to use (default: qwen3:8b)
- `SMART_COMMIT_MACOS_LOCAL` - Performance optimization flag (macOS local only)

## Smart Commit Script (`smart-commit.sh`)

### Dual-Mode Operation

The script operates in two modes based on environment detection:

#### Optimized Mode (macOS Local)
- **Trigger**: `SMART_COMMIT_MACOS_LOCAL=true` AND not using `--full` flag
- **Function**: `generate_truncated_commit_message()`
- **Progressive Truncation**: 
  - Small files (<4KB): Full diff
  - Medium files (4-7KB): 150 lines
  - Large files (>7KB): Smart truncation (80 lines + key patterns)
- **Prompt**: Simplified, focused instructions (~4,000-7,000 chars)
- **Performance**: ~15-25 seconds on M3 Pro
- **Timeout**: 60 seconds

#### Full Mode (Linux/Remote/--full flag)
- **Trigger**: All other configurations OR `--full` flag
- **Function**: `generate_commit_message()` (original)
- **Diff Limit**: 200 lines (full analysis)
- **Prompt**: Verbose, detailed instructions (~8,500+ chars)
- **Performance**: ~27 seconds on AMD 6800XT, timeout on M3 Pro
- **Timeout**: 120 seconds

### Key Functions

#### Analysis Functions
- `get_git_diff()` - Extracts and formats git changes for multi-file commits
- `get_file_diff()` - Extracts diff for single file (atomic commits)
- `get_smart_truncation()` - Progressive truncation for large files (macOS)
- `analyze_file_changes()` - Counts additions/deletions per file
- `check_git_repo()` / `check_git_status()` - Validation functions

#### Message Generation
- `generate_commit_message()` - Full analysis with verbose prompt
- `generate_truncated_commit_message()` - Optimized for mobile GPUs with progressive truncation
- Automatic fallbacks for API failures
- Multiple extraction strategies for AI responses

#### Workflow Functions
- `stage_changes()` - Stages all changes (traditional mode)
- `commit_changes()` - Interactive commit with confirmation (traditional mode)
- `handle_atomic_commits()` - Creates one commit per file with validation
- `validate_commits()` - Review and edit commits before pushing
- `edit_commit_message()` - Interactive commit message editing
- `push_changes()` - Handles upstream branch creation

### Command Line Interface
- `--dry-run` - Preview mode, no commits
- `--full` - Force detailed analysis (bypasses optimization)
- `--atomic` - Create one commit per modified file with validation
- `--help` - Usage information

## Performance Characteristics

### Platform Performance
- **M3 Pro (optimized)**: 15-25 seconds ✅
- **M3 Pro (full)**: 120+ seconds (timeout) ❌
- **AMD 6800XT (full)**: ~27 seconds ✅
- **M4 Max (estimated)**: 8-20 seconds ✅

### Optimization Strategy
The key insight is that **prompt complexity**, not diff size, drives processing time:
- **Simple prompt** (6,000 chars): Works on mobile GPUs
- **Verbose prompt** (8,500+ chars): Requires desktop-class GPUs

## Configuration Management

### Environment Priority
1. Command line environment override
2. Shell profile variables (set by setup)
3. Script defaults

### Shell Profile Locations
- **Linux**: `~/.bashrc`
- **macOS**: `~/.zshrc`

### Idempotent Updates
The setup script uses `grep -v` for cross-platform environment variable updates:
```bash
grep -v "^export $var_name=" "$SHELL_PROFILE" > "$SHELL_PROFILE.tmp" && mv "$SHELL_PROFILE.tmp" "$SHELL_PROFILE"
```

## Logging and Debugging

### Log Location
- `~/.cache/smart-commit.log` (overwritten each run)
- `$XDG_CACHE_HOME/smart-commit.log` (if XDG_CACHE_HOME set)
- `/tmp/smart-commit.log` (fallback)

### Key Log Information
- Prompt sizes and processing times
- API request/response details
- Message extraction strategies
- Error conditions and fallbacks

## AI Model Integration

### Ollama API Usage
- **Endpoint**: `/api/generate`
- **Model**: qwen3:8b (recommended)
- **Format**: JSON with `prompt` and `stream: false`
- **Response**: Extracts commit message from `.response` field

### Message Extraction Strategies
1. Conventional commit pattern with scope: `feat(scope):`
2. Conventional commit without scope: `feat:`
3. Any line containing conventional commit types
4. Intelligent fallbacks based on diff content

### Prompt Engineering
- **Optimized**: Focused instructions, essential guidance only
- **Full**: Comprehensive examples, edge cases, detailed rules
- Both produce conventional commit format: `type(scope): description`

## Development Guidelines

### Code Style
- Bash best practices with proper error handling
- Extensive logging for debugging
- Cross-platform compatibility (macOS/Linux)
- Idempotent operations where possible

### Testing Approach
- Test on different platforms (M1/M2/M3, Intel, AMD)
- Verify both optimized and full modes
- Test setup script idempotency
- Validate with various diff sizes and types

### Performance Considerations
- Monitor prompt sizes and processing times
- Consider GPU memory limitations on mobile hardware
- Balance accuracy vs speed for different use cases
- Provide escape hatches (`--full` for maximum accuracy)

## Common Issues and Solutions

### Setup Issues
- **Homebrew detection**: Check `command -v brew`
- **Service startup**: systemctl vs manual nohup on different platforms
- **Model download**: Requires internet and ~5GB space

### Performance Issues
- **Timeouts on mobile GPUs**: Use optimized mode automatically
- **Memory constraints**: Truncate context appropriately
- **Network latency**: Adjust timeouts for remote servers

### Compatibility Issues
- **Shell profiles**: Different locations on macOS vs Linux
- **sed syntax**: Use grep/mv instead of sed -i for portability
- **Service management**: systemctl vs manual process management

## Future Enhancements

### Potential Improvements
- Support for more AI models (Claude, GPT-4, etc.)
- Configurable optimization thresholds
- Repository-specific configuration
- Integration with git hooks
- Commit message templates and customization

### Architecture Considerations
- Plugin system for different AI providers
- Configuration file support (beyond environment variables)
- Better cross-platform service management
- Automated performance tuning based on hardware detection

## Dependencies

### Required
- **bash** - Shell environment
- **git** - Version control operations
- **curl** - API communication
- **jq** - JSON parsing
- **ollama** - AI model runtime (installed by setup)

### Optional
- **homebrew** - Preferred installation method on macOS
- **systemctl** - Service management on Linux

This tool demonstrates effective cross-platform bash scripting with AI integration, automatic performance optimization, and user-friendly setup automation.