# Smart Git Commit Tool - Development Guide

This document provides context for AI assistants working on the Smart Git Commit Tool project.

## Project Overview

An intelligent bash script that analyzes git changes and generates meaningful commit messages using AI. The tool supports dual backends (Ollama and llama.cpp) with automatic detection, local and remote setups, and platform-specific optimizations for different environments.

## Architecture

### Core Components

1. **setup** - Interactive setup script for dual backend configuration
2. **smart-commit.sh** - Main commit message generation script with AI backend abstraction
3. **Environment-based configuration** - Uses shell environment variables (new: AI_*, legacy: OLLAMA_*)
4. **Platform-specific optimizations** - Different behavior for macOS/Linux/remote setups
5. **Dual backend support** - Seamless Ollama and llama.cpp integration

### Key Files

- `setup` - Handles dual backend installation, configuration, and environment setup
- `smart-commit.sh` - Main script with dual backend support and dual-mode operation (optimized/full)
- `README.md` - User documentation with backend configuration guides
- `CLAUDE.md` - This development guide

## Setup Script (`setup`)

### Features
- **OS Detection**: Automatically detects macOS/Linux
- **Configuration Status Display**: Shows smart-commit command availability and validates AI environment variables
- **Platform-Specific Local Options**: 
  1. **macOS**: Local Ollama (with automatic installation and optimization)
  2. **Linux**: Local llama.cpp probe (detects existing installations, partial implementation)
- **Remote Backend Options**:
  1. Remote Windows Ollama server (port 11434)
  2. Remote Linux llama.cpp server (port 8080, auto-detects model)
  3. Keep current configuration with validation
- **Environment Variable Validation**: Checks all AI configuration variables are set and non-empty
- **Command Installation Management**: Always ensures smart-commit command is available system-wide
- **Idempotent Operations**: Safe to re-run, skips completed steps
- **Cross-platform Compatibility**: Uses `grep -v` instead of `sed -i` for shell profile editing
- **Backend Auto-Detection**: Probes server endpoints to determine backend type

### Key Functions

#### Ollama Functions
- `check_ollama_installed()` - Detects if Ollama is available
- `check_ollama_running()` - Tests if Ollama service is responding
- `check_qwen3_model()` - Verifies qwen3:8b model availability
- `install_ollama()` - Handles installation via Homebrew/curl
- `setup_local_macos_ollama()` - Complete macOS Ollama setup with optimization flags
- `setup_remote_ollama()` - Remote Windows Ollama server configuration

#### llama.cpp Functions
- `check_llamacpp_running()` - Detects running llama.cpp servers on common ports
- `get_llamacpp_model()` - Extracts model information from llama.cpp server
- `probe_llamacpp_installation()` - Comprehensive detection with user feedback
- `probe_llamacpp_installation_silent()` - Silent detection for configuration parsing
- `setup_local_linux_llamacpp()` - Linux llama.cpp probe and configuration
- `setup_remote_llamacpp()` - Remote Linux llama.cpp server configuration

#### Unified Setup Functions
- `setup_local_ollama()` - Platform dispatcher (macOS→Ollama, Linux→llama.cpp)
- `setup_remote_server()` - Remote backend selection (Windows Ollama vs Linux llama.cpp)

#### Validation and Installation Functions
- `check_smart_commit_installed()` - Detects if smart-commit command is available in PATH
- `validate_current_config()` - Validates AI environment variables are set and non-empty
- `install_smart_commit()` - Installs/updates smart-commit command system-wide with idempotent behavior
- `show_current_config()` - Enhanced status display including command availability and config validation

### Environment Variables Set

#### New Configuration System (v2.0+)
- `AI_API_URL` - AI server endpoint (localhost:11434 for Ollama, localhost:8080 for llama.cpp, or remote IP)
- `AI_MODEL` - AI model to use (qwen3:8b for Ollama, model path or auto-detected for llama.cpp)
- `AI_BACKEND_TYPE` - Backend type: "ollama" or "llamacpp" (auto-detected if not set)
- `SMART_COMMIT_MACOS_LOCAL` - Performance optimization flag (macOS local Ollama only)

#### Legacy Configuration (still supported)
- `OLLAMA_API_URL` - Server endpoint (automatically converted to AI_API_URL)
- `OLLAMA_MODEL` - AI model to use (automatically converted to AI_MODEL)

#### Migration and Compatibility
- Setup script creates new AI_* variables for all new configurations
- Legacy OLLAMA_* variables are detected and work seamlessly
- Backend auto-detection converts legacy configs to appropriate backend types
- No breaking changes for existing users

## Smart Commit Script (`smart-commit.sh`)

### Dual Backend Architecture

The script now features a dual backend architecture with automatic detection and API abstraction:

#### Backend Detection System
- **Auto-Detection Function**: `detect_backend_type()` runs at startup
- **Detection Strategy**: 
  1. Respects explicit `AI_BACKEND_TYPE` environment variable
  2. Tests server endpoints: `/health` for llama.cpp, `/api/tags` for Ollama
  3. Falls back to default if server is unreachable
- **Legacy Compatibility**: Automatically converts OLLAMA_* variables and detects backend type

#### API Abstraction Layer
- **Unified Interface**: `call_ai_api(prompt, timeout)` abstracts backend differences
- **Ollama Implementation**: `call_ollama_api()` uses `/api/generate` endpoint with native JSON
- **llama.cpp Implementation**: `call_llamacpp_api()` uses `/v1/completions` with OpenAI-compatible JSON
- **Model Handling**: Auto-detects model names for llama.cpp, uses direct names for Ollama
- **Error Handling**: Consistent timeout and error handling across both backends

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
- `generate_commit_message()` - Full analysis with verbose prompt (uses `call_ai_api()`)
- `generate_truncated_commit_message()` - Optimized for mobile GPUs with progressive truncation (uses `call_ai_api()`)
- **Backend Abstraction**: Both functions use unified `call_ai_api()` interface
- **Automatic fallbacks**: API failures gracefully fall back to truncated mode
- **Multiple extraction strategies**: Handles different AI response formats across backends

#### Workflow Functions
- `stage_changes()` - Stages all changes (traditional mode)
- `commit_changes()` - Interactive commit with confirmation (traditional mode)
- `handle_atomic_commits()` - Creates one commit per file with validation
- `validate_commits()` - Review and edit commits before pushing
- `edit_commit_message()` - Interactive commit message editing
- `push_changes()` - Handles upstream branch creation

### Command Line Interface
- `--dry-run` - Preview mode, no commits (works with both backends)
- `--full` - Force detailed analysis (bypasses optimization, works with both backends)
- `--atomic` - Create one commit per modified file with validation (works with both backends)
- `--help` - Usage information

## Dual Backend Implementation Details

### Architecture Decision
The implementation uses a **single script approach** rather than separate scripts for each backend:
- **95% shared logic**: Git analysis, truncation, validation, and workflow logic is identical
- **5% backend-specific**: Only API communication differs between Ollama and llama.cpp
- **Maintainability**: Single codebase is easier to maintain and update
- **User Experience**: One command interface regardless of backend

### Backend Abstraction Pattern
```bash
# High-level flow (same for both backends)
detect_backend_type()  # Auto-detect at startup
generate_commit_message() {
    # ... shared logic for analysis and truncation ...
    local raw_response=$(call_ai_api "$prompt" "$timeout")  # Backend abstraction
    # ... shared logic for extraction and validation ...
}

# Backend-specific implementations
call_ai_api() {
    case "$AI_BACKEND_TYPE" in
        "ollama") call_ollama_api "$prompt" "$timeout" ;;
        "llamacpp") call_llamacpp_api "$prompt" "$timeout" ;;
    esac
}
```

### Error Handling Strategy
- **Unified Timeouts**: Both backends use the same adaptive timeout system
- **Graceful Degradation**: API failures fall back to truncated mode
- **Consistent Logging**: Same log format for both backends
- **Error Recovery**: Connection failures are handled consistently

### Model Compatibility
- **Ollama**: Uses model names directly (qwen3:8b, llama3.2:1b)
- **llama.cpp**: Supports full model paths and auto-detection via `/v1/models`
- **Prompt Compatibility**: Same prompts work effectively across both backends
- **Output Consistency**: Both backends produce conventional commit format

## Performance Characteristics

### Platform Performance

#### macOS Performance (Ollama)
- **M3 Pro (optimized)**: 15-25 seconds ✅
- **M3 Pro (full)**: 120+ seconds (timeout) ❌
- **M4 Max (estimated)**: 8-20 seconds ✅

#### Linux Performance (llama.cpp)
- **AMD 6800XT**: ~27 seconds (full mode) ✅
- **NVIDIA RTX 4080**: ~20-30 seconds (estimated) ✅
- **CPU-only**: 60-120 seconds (depends on model size) ⚠️

#### Backend Performance Comparison
- **Ollama**: Better on macOS/mobile GPUs, optimized for Apple Silicon
- **llama.cpp**: Better on high-end desktop GPUs, more efficient with NVIDIA/AMD
- **Model Loading**: llama.cpp keeps model in memory, Ollama may need loading time
- **Concurrency**: Both support single requests well, llama.cpp better for multiple concurrent requests

### Optimization Strategy
The key insight is that **prompt complexity**, not diff size, drives processing time:
- **Simple prompt** (4,000-6,000 chars): Works on mobile GPUs (both backends)
- **Verbose prompt** (8,500+ chars): Requires desktop-class GPUs (both backends)
- **Backend Choice**: Choose based on hardware (Ollama for Apple Silicon, llama.cpp for desktop GPUs)

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
- Backend detection and configuration details
- Prompt sizes and processing times
- API request/response details (both Ollama and llama.cpp)
- Message extraction strategies across different backends
- Error conditions and fallbacks
- Model auto-detection results

## AI Model Integration

### Dual Backend Support

#### Ollama API Integration
- **Endpoint**: `/api/generate`
- **Models**: qwen3:8b (recommended), llama3.2:1b, qwen3:4b
- **Format**: JSON with `prompt` and `stream: false`
- **Response**: Extracts commit message from `.response` field
- **Implementation**: `call_ollama_api(prompt, timeout)`

#### llama.cpp API Integration
- **Endpoint**: `/v1/completions` (OpenAI-compatible)
- **Models**: Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf (recommended), CodeLlama variants
- **Format**: JSON with `prompt`, `max_tokens`, `temperature`, `stop`
- **Response**: Extracts commit message from `.choices[0].text` field
- **Implementation**: `call_llamacpp_api(prompt, timeout)`
- **Model Auto-Detection**: Queries `/v1/models` endpoint to detect loaded model

#### Backend Configuration Detection
- **Health Endpoints**: `/health` for llama.cpp, `/api/tags` for Ollama
- **Automatic Conversion**: Legacy OLLAMA_* variables automatically detect backend type
- **Fallback Strategy**: Defaults to specified backend if server unreachable

### Message Extraction Strategies
1. Conventional commit pattern with scope: `feat(scope):`
2. Conventional commit without scope: `feat:`
3. Any line containing conventional commit types
4. Intelligent fallbacks based on diff content
5. **Cross-Backend Compatibility**: Same extraction logic works for both backends

### Prompt Engineering
- **Optimized**: Focused instructions, essential guidance only (~4,000-7,000 chars)
- **Full**: Comprehensive examples, edge cases, detailed rules (~8,500+ chars)
- **Backend Agnostic**: Same prompts work effectively with both Ollama and llama.cpp
- **Output Format**: Both backends produce conventional commit format: `type(scope): description`

## Platform-Specific Setup Behavior

### macOS Local Setup
- **Full Implementation**: Complete automated Ollama installation and configuration
- **Package Manager**: Uses Homebrew if available, falls back to curl installer
- **Service Management**: Uses `nohup ollama serve` for background service
- **Model Download**: Automatically downloads qwen3:8b model (~5GB)
- **Optimization**: Sets `SMART_COMMIT_MACOS_LOCAL=true` for performance optimization
- **Backend**: Always uses Ollama (`AI_BACKEND_TYPE=ollama`)

### Linux Local Setup (Partial Implementation)
- **⚠️ Probe-Only Implementation**: Detects existing llama.cpp installations, no automatic installation
- **Detection Strategy**: Scans ports 8080, 8000, 3000 for llama.cpp servers
- **Model Auto-Detection**: Queries `/v1/models` endpoint to identify loaded model
- **User Warning**: Clear messaging about partial implementation status
- **Fallback Guidance**: Directs users to remote options if no installation detected
- **Backend**: Always uses llama.cpp (`AI_BACKEND_TYPE=llamacpp`)

#### Linux Local Detection Process
```bash
# 1. Warning display
echo "⚠ WARNING: Linux local deployment is partially implemented"
echo "   This will detect and use your existing llama.cpp installation"

# 2. Port scanning
for port in 8080 8000 3000; do
    if curl -s --max-time 3 "http://localhost:$port/health"; then
        # Found server, extract model info
    fi
done

# 3. Configuration
AI_API_URL="http://localhost:$detected_port"
AI_MODEL="$detected_model_path"  # or "auto-detected"
AI_BACKEND_TYPE="llamacpp"
```

### Remote Setup Options

#### Windows Ollama Server
- **Target**: Existing Windows machines running Ollama
- **Port**: 11434 (standard Ollama port)
- **Model**: qwen3:8b (user-specified)
- **Testing**: Probes `/api/tags` endpoint for connectivity
- **Backend**: Ollama (`AI_BACKEND_TYPE=ollama`)

#### Linux llama.cpp Server
- **Target**: Existing Linux machines running llama.cpp server
- **Port**: 8080 (default), user-configurable
- **Model**: Auto-detected from `/v1/models` endpoint
- **Testing**: Probes `/health` endpoint for connectivity
- **Backend**: llama.cpp (`AI_BACKEND_TYPE=llamacpp`)

### Setup Flow Decision Tree
```
./setup
├── Detect OS (macOS/Linux)
├── Show current configuration
└── Choice 1: Local AI
    ├── macOS → setup_local_macos_ollama()
    │   ├── Install Ollama (Homebrew/curl)
    │   ├── Start service (nohup)
    │   ├── Download qwen3:8b model
    │   └── Set optimization flags
    └── Linux → setup_local_linux_llamacpp()
        ├── Show partial implementation warning
        ├── Probe ports for llama.cpp
        ├── Auto-detect model
        └── Configure environment
└── Choice 2: Remote AI server
    ├── Windows Ollama → setup_remote_ollama()
    └── Linux llama.cpp → setup_remote_llamacpp()
└── Choice 3: Keep current config
```

### Platform Recommendations
- **macOS users**: Use local Ollama for best integration and performance
- **Linux desktop users**: Use local llama.cpp if already installed, otherwise remote
- **Linux server users**: Set up remote llama.cpp server for other machines
- **Mixed environments**: Use remote servers for consistency across platforms

## Development Guidelines

### Code Style
- Bash best practices with proper error handling
- Extensive logging for debugging
- Cross-platform compatibility (macOS/Linux)
- Idempotent operations where possible

### Testing Approach
- **Platform Testing**: Test on different platforms (M1/M2/M3, Intel, AMD)
- **Backend Testing**: Verify both Ollama and llama.cpp backends function correctly
- **Mode Testing**: Verify both optimized and full modes across backends
- **Setup Testing**: Test setup script idempotency and backend auto-detection
- **Integration Testing**: Validate with various diff sizes and types across backends
- **Legacy Testing**: Ensure OLLAMA_* variable compatibility and auto-conversion

### Performance Considerations
- **Cross-Backend Performance**: Monitor prompt sizes and processing times across both backends
- **Hardware Optimization**: Consider GPU memory limitations on mobile hardware (macOS) vs desktop hardware (Linux)
- **Backend Selection**: llama.cpp often performs better on high-end desktop GPUs, Ollama on mobile/integrated
- **Balance Strategy**: Balance accuracy vs speed for different use cases and hardware
- **Escape Hatches**: Provide `--full` flag for maximum accuracy regardless of backend

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