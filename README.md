# Smart Git Commit Tool

An intelligent bash script that analyzes your git changes and generates meaningful commit messages using AI. Supports both Ollama and llama.cpp backends with automatic detection and platform-specific optimizations.

## Features

- 🤖 **Dual AI Backend Support** - Works with both Ollama and llama.cpp servers with automatic detection
- 📝 **Conventional Commits** - Generates properly formatted commit messages (feat:, fix:, perf:, etc.)
- 🎯 **Context-Aware** - Considers recent commit history for consistent messaging style
- ⚡ **Smart Validation** - Automatically improves and shortens messages when needed
- 🔧 **Performance Detection** - Automatically detects performance optimizations (ThreadPoolExecutor, batch processing, concurrency)
- 🎯 **Auto-Correction** - Intelligently corrects commit types (e.g., feat→perf for performance changes)
- 🔍 **Dry Run Mode** - Preview commit messages without making changes
- 📊 **Comprehensive Logging** - Detailed logs for debugging and transparency
- 🌐 **Cross-Platform** - Native support for macOS and Linux with platform-specific optimizations
- 🔌 **Flexible Deployment** - Local, remote, or hybrid AI server configurations

## Installation

### Automated Setup (Recommended)

Run the setup script for easy installation:

```bash
./setup
```

The setup script will:
- Detect your OS (Linux/macOS) and configure the appropriate shell profile
- **Check current status**: Display smart-commit command availability and AI configuration validation
- Give you three options:
  1. **Local AI** - Platform-specific local setup:
     - **macOS**: Install and run Ollama locally (with performance optimization)
     - **Linux**: Probe and use existing llama.cpp installation (partial implementation)
  2. **Remote AI server** - Connect to existing servers:
     - **Windows Ollama server** (port 11434)
     - **Linux llama.cpp server** (port 8080, auto-detects model)
  3. **Keep current configuration** - Maintain existing setup with validation
- Handle installation, model detection, and service management automatically
- **Validate configuration**: Check environment variables are properly set and non-empty
- Set up environment variables in `.bashrc` (Linux) or `.zshrc` (macOS)
- **Always install command**: Ensure `smart-commit` is available system-wide in `/usr/local/bin/`

After setup, reload your shell:
```bash
source ~/.bashrc  # Linux
# or
source ~/.zshrc   # macOS
```

### Manual Installation

If you prefer manual setup:

#### 1. Copy to your bin directory
```bash
# System-wide installation (recommended)
sudo cp smart-commit.sh /usr/local/bin/smart-commit

# Or user-specific installation
cp smart-commit.sh ~/bin/smart-commit
chmod +x ~/bin/smart-commit
```

#### 2. Configure environment variables
Add to your `~/.bashrc` (Linux) or `~/.zshrc` (macOS):

**For Ollama backend:**
```bash
# AI configuration for smart-commit script
export AI_API_URL="http://localhost:11434"  # or your remote server IP
export AI_MODEL="qwen3:8b"
export AI_BACKEND_TYPE="ollama"

# Optional: Enable macOS performance optimization (for local macOS setups)
export SMART_COMMIT_MACOS_LOCAL="true"
```

**For llama.cpp backend:**
```bash
# AI configuration for smart-commit script
export AI_API_URL="http://localhost:8080"  # or your remote server IP:port
export AI_MODEL="auto-detected"  # or specific model path
export AI_BACKEND_TYPE="llamacpp"
```

**Legacy configuration (still supported):**
```bash
# Legacy Ollama configuration (automatically converted)
export OLLAMA_API_URL="http://localhost:11434"
export OLLAMA_MODEL="qwen3:8b"
# AI_BACKEND_TYPE will be auto-detected
```

Then reload your shell:
```bash
source ~/.bashrc  # Linux
source ~/.zshrc   # macOS
```

## Prerequisites

- **Git repository** - Must be run from within a git repository
- **AI Backend** - Choose from:
  - **Ollama** - Local installation (handled by setup) or remote server access
  - **llama.cpp** - Local installation or remote server access
- **jq** - For JSON parsing (`sudo apt install jq` on Ubuntu/Debian, `brew install jq` on macOS)
- **curl** - For API requests (usually pre-installed)

### Backend Options

#### Local Ollama (macOS - Recommended for new users)
The setup script can automatically:
- Install Ollama via Homebrew (macOS) or curl script (Linux)
- Download the qwen3:8b model (~5GB)
- Start the Ollama service
- Configure optimized settings for your platform

#### Local llama.cpp (Linux - Partial Implementation)
For Linux users with existing llama.cpp installations:
- **⚠️ Partially implemented** - Probes existing installations only
- Detects running llama.cpp servers on ports 8080, 8000, 3000
- Auto-detects model names and configurations
- **No automatic installation** - Use remote options if no existing setup

#### Remote Servers
- **Windows Ollama server** - Accessible on port 11434 with qwen3:8b model
- **Linux llama.cpp server** - Accessible on port 8080 (or custom) with compatible models

## Usage

### Basic Usage
```bash
# Generate commit message and push changes
smart-commit

# Preview commit message without committing
smart-commit --dry-run

# Create one commit per modified file (professional workflow)
smart-commit --atomic

# Show help
smart-commit --help
```

### Example Workflow

#### Traditional Single Commit
```bash
# Make your changes
git add .

# Preview the generated commit message
smart-commit --dry-run
# Output: feat(auth): add JWT token validation with expiry handling

# If satisfied, commit and push
smart-commit
```

#### Professional Atomic Commits
```bash
# Make changes to multiple files
# Modified: auth.js, login.html, README.md

# Create atomic commits (one per file) with validation
smart-commit --atomic

# Output:
# Processing file: auth.js
# ✓ Committed: auth.js
#   Message: "feat(auth): add JWT token validation with expiry handling"
# 
# Processing file: login.html  
# ✓ Committed: login.html
#   Message: "feat(ui): add login form validation feedback"
#
# Processing file: README.md
# ✓ Committed: README.md  
#   Message: "docs: update authentication setup instructions"
#
# All files committed individually!
# Pushing all commits to remote... 
```

## How It Works

1. **Analyzes Changes** - Examines `git status` and `git diff` output
2. **Contextual Understanding** - Reviews recent commit history for style consistency
3. **AI Processing** - Sends summarized changes to Ollama for analysis
4. **Message Generation** - Creates conventional commit format messages
5. **Validation & Improvement** - Checks length and format, improves if needed
6. **Git Operations** - Stages changes, commits with generated message, and pushes

## Configuration

### Environment Variables

#### New Configuration (v2.0+)
- `AI_API_URL` - AI server endpoint (default: http://localhost:11434)
- `AI_MODEL` - Model to use (default: qwen3:8b, or auto-detected for llama.cpp)
- `AI_BACKEND_TYPE` - Backend type: "ollama" or "llamacpp" (auto-detected if not set)
- `SMART_COMMIT_MACOS_LOCAL` - Enable macOS performance optimization (set automatically by setup)

#### Legacy Configuration (still supported)
- `OLLAMA_API_URL` - Ollama server endpoint (automatically converted to AI_API_URL)
- `OLLAMA_MODEL` - Ollama model (automatically converted to AI_MODEL)

### Temporary Override
```bash
# Use different model for one run
AI_MODEL="llama3.2:1b" smart-commit --dry-run

# Use different backend temporarily
AI_BACKEND_TYPE="llamacpp" AI_API_URL="http://localhost:8080" smart-commit

# Legacy override (still works)
OLLAMA_MODEL="llama3.2:1b" smart-commit --dry-run
```

## Multi-Account GitHub Setup

For users who need to work with different GitHub accounts on the same machine (personal vs work, multiple organizations, etc.), you can configure SSH to use different keys for different repositories.

### Setting Up Multiple GitHub Accounts

#### 1. Generate SSH keys for each account
```bash
# Personal account key (if you don't already have one)
ssh-keygen -t ed25519 -C "personal@example.com" -f ~/.ssh/id_ed25519

# Work account key
ssh-keygen -t ed25519 -C "work@company.com" -f ~/.ssh/id_ed25519_work
```

#### 2. Add keys to SSH agent
```bash
ssh-add ~/.ssh/id_ed25519       # Personal key
ssh-add ~/.ssh/id_ed25519_work  # Work key
```

#### 3. Create SSH config file
Create or edit `~/.ssh/config`:
```ssh
# Default GitHub account (personal)
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519

# Work GitHub account
Host github-work
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_work
```

#### 4. Add public keys to respective GitHub accounts
```bash
# Copy personal key
cat ~/.ssh/id_ed25519.pub

# Copy work key
cat ~/.ssh/id_ed25519_work.pub
```

Add these to the appropriate GitHub accounts in **Settings → SSH and GPG keys**.

#### 5. Configure repositories to use specific accounts

**For personal repos:**
```bash
git remote set-url origin git@github.com:username/repo.git
```

**For work repos:**
```bash
git remote set-url origin git@github-work:company/repo.git
```

#### 6. Test your configuration
```bash
ssh -T git@github.com      # Should show personal account
ssh -T git@github-work     # Should show work account
```

### Using smart-commit with Multiple Accounts

Once configured, **smart-commit works automatically** with your multi-account setup:

- The script calls `git push` which uses whatever remote URL is configured
- Your SSH config routes the connection to the correct GitHub account
- No changes needed to smart-commit itself

**Example workflow:**
```bash
# In a work repository
cd /path/to/work-repo
smart-commit  # Automatically uses work account

# In a personal repository  
cd /path/to/personal-repo
smart-commit  # Automatically uses personal account
```

### Troubleshooting Multi-Account Setup

**Both connections show the same account:**
```bash
# Clear SSH agent and reload keys
ssh-add -D
ssh-add ~/.ssh/id_ed25519       # Personal
ssh-add ~/.ssh/id_ed25519_work  # Work
```

**Permission denied errors:**
- Verify the correct public key is added to the right GitHub account
- Check that your SSH config host aliases match your remote URLs
- Ensure the repository owner has given your account appropriate access

## Generated Commit Message Examples

- `perf(google-api): add batch + concurrency with limit parameter`
- `feat(auth): add JWT token validation with expiry handling`
- `fix(api): resolve memory leak in data processing pipeline`
- `refactor(db): optimize query performance for user lookups`
- `docs(readme): update installation instructions for new users`
- `test(utils): add unit tests for date formatting functions`

## Logging

Logs are stored at `~/.cache/smart-commit.log` and overwritten on each run. The log includes:
- Git repository status
- Changes analysis
- AI API interactions
- Message generation process
- Validation and improvement steps

## Command Line Options

```
Usage: smart-commit [--dry-run] [--atomic] [--help]

Options:
  --dry-run    Show the generated commit message without committing
  --atomic     Create one commit per modified file (professional workflow)
  --help       Show help message and exit

Examples:
  smart-commit              # Analyze, commit, and push changes
  smart-commit --dry-run    # Preview commit message only
  smart-commit --atomic     # Create atomic commits with streamlined workflow
  smart-commit --atomic --dry-run  # Preview atomic commit messages
```

## Atomic Commits Workflow

The `--atomic` flag creates professional, focused commits:

### Benefits
- **Better code review** - Each commit represents one logical change
- **Cleaner git history** - Easy to understand project evolution  
- **Selective rollbacks** - Revert specific features without affecting others
- **Improved accuracy** - Single-file context generates better commit messages

### Streamlined Process
After generating all proposed commits, you can:
- **ENTER** - Accept all messages, create commits, and push to remote
- **1-N** - Edit specific commit messages before committing
- **c** - Cancel (no commits will be made)

### Flag Combinations
```bash
# Atomic commits with platform optimization
smart-commit --atomic

# Preview atomic commits without committing
smart-commit --atomic --dry-run
```

## Performance Optimization

### macOS Local Optimization
When using local Ollama on macOS (M1/M2/M3 chips), smart-commit automatically uses performance optimizations:

- **Streamlined prompts** - Simplified instructions for faster processing
- **Optimized context** - Right-sized diff analysis for mobile GPUs
- **Automatic detection** - No manual configuration required

**Performance comparison on M3 Pro:**
- **Standard mode**: 120+ seconds (timeout)
- **Optimized mode**: 15-25 seconds ✅

**When optimization is used:**
- ✅ Local Ollama on macOS (set by setup script)
- ✅ Regular `smart-commit` command
- ❌ Linux local or remote setups (use full power)

### Platform-Specific Behavior
- **macOS local**: Fast, optimized prompts (~15-25 seconds) with progressive truncation
- **Linux local**: Full detailed analysis (more powerful hardware assumed)
- **Remote servers**: Full detailed analysis (desktop-class performance)

### Progressive Optimization (macOS Local)
Smart-commit automatically adjusts analysis depth based on change complexity:

- **Small changes** (<4KB): Full analysis for perfect accuracy
- **Medium changes** (4-7KB): Balanced analysis (150 lines of diff)
- **Large changes** (>7KB): Smart truncation focusing on key patterns
  - Early context (first 80 lines)
  - Function/class definitions
  - Import/export statements

## Advanced Features

### Smart Message Improvement
The script automatically:
- Validates conventional commit format
- Shortens messages that exceed 90 characters
- Auto-corrects commit types based on code content (feat→perf for performance improvements)
- Detects performance patterns: ThreadPoolExecutor, batch processing, concurrency
- Uses context from recent commits for consistency

### Robust Error Handling
- Checks for git repository presence
- Validates changes exist before processing
- Handles API failures gracefully
- Provides detailed error messages and logging

### AI Response Processing
- Handles Ollama model "thinking" patterns (`<think>` tags)
- Extracts clean commit messages from verbose AI responses
- Falls back to alternative extraction methods
- Comprehensive response validation

## Troubleshooting

### Common Issues

**"Not in a git repository"**
- Ensure you're running the script from within a git repository

**"No changes to commit"**
- Make sure you have unstaged or staged changes
- Check `git status` to see current repository state

**"Failed to generate commit message"**
- Verify your AI server is running and accessible
- **For Ollama**: Check the model is available: `curl $AI_API_URL/api/tags`
- **For llama.cpp**: Check server health: `curl $AI_API_URL/health`
- Review logs at `~/.cache/smart-commit.log`

**AI response issues**
- Try a different model (e.g., `llama3.2:1b` for faster responses)
- Check AI server logs for errors
- Ensure sufficient system resources for the model
- Verify backend type is correctly set (`AI_BACKEND_TYPE`)

### Debugging
Check the detailed log file for troubleshooting:
```bash
cat ~/.cache/smart-commit.log
```

## Dual Backend Support

Smart-commit seamlessly supports both Ollama and llama.cpp backends with automatic detection and configuration.

### Backend Detection
The script automatically detects your backend type by:
1. **Environment variables** - Respects explicit `AI_BACKEND_TYPE` setting
2. **Legacy compatibility** - Auto-detects when using `OLLAMA_*` variables
3. **Server probing** - Tests `/health` (llama.cpp) and `/api/tags` (Ollama) endpoints
4. **Graceful fallback** - Uses specified backend if detection fails

### API Compatibility
- **Ollama**: Uses `/api/generate` endpoint with native JSON format
- **llama.cpp**: Uses `/v1/completions` endpoint with OpenAI-compatible format
- **Model handling**: 
  - Ollama: Uses model name directly (e.g., "qwen3:8b")
  - llama.cpp: Supports full model paths or auto-detection from server

### Configuration Examples

#### Setup Script Configurations
```bash
# Windows Ollama server
AI_API_URL="http://192.168.1.100:11434"
AI_MODEL="qwen3:8b"
AI_BACKEND_TYPE="ollama"

# Linux llama.cpp server  
AI_API_URL="http://192.168.1.200:8080"
AI_MODEL="/path/to/model.gguf"
AI_BACKEND_TYPE="llamacpp"

# Auto-detected local Linux llama.cpp
AI_API_URL="http://localhost:8080"
AI_MODEL="auto-detected"
AI_BACKEND_TYPE="llamacpp"
```

#### Legacy Auto-Conversion
```bash
# This legacy configuration...
export OLLAMA_API_URL="http://localhost:8080"
export OLLAMA_MODEL="model.gguf"

# ...automatically becomes:
# AI_API_URL="http://localhost:8080"
# AI_MODEL="model.gguf" 
# AI_BACKEND_TYPE="llamacpp"  (auto-detected via /health endpoint)
```

## Recommended Models

### For Ollama
- **qwen3:8b** (Recommended) - Best balance of quality and speed, excellent context understanding
- **llama3.2:1b** - Faster responses, good for simple commits
- **qwen3:4b** - Good middle ground if available

### For llama.cpp
- **Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf** (Recommended) - Excellent code understanding and commit generation
- **CodeLlama-7B-Instruct-Q4_K_M.gguf** - Good code-specific performance
- **Qwen2-7B-Instruct-Q4_K_M.gguf** - General purpose, good quality
- **Llama-3.2-1B-Instruct-Q8_0.gguf** - Fast responses for simple commits

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Feel free to suggest improvements or report issues. The script is designed to be easily customizable for different workflows and preferences.