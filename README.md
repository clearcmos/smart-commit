# Smart Git Commit Tool

An intelligent bash script that analyzes your git changes and generates meaningful commit messages using AI via Ollama.

## Features

- 🤖 **AI-Powered Analysis** - Uses Ollama models to understand your code changes with intelligent analysis
- 📝 **Conventional Commits** - Generates properly formatted commit messages (feat:, fix:, perf:, etc.)
- 🎯 **Context-Aware** - Considers recent commit history for consistent messaging style
- ⚡ **Smart Validation** - Automatically improves and shortens messages when needed
- 🔧 **Performance Detection** - Automatically detects performance optimizations (ThreadPoolExecutor, batch processing, concurrency)
- 🎯 **Auto-Correction** - Intelligently corrects commit types (e.g., feat→perf for performance changes)
- 🔍 **Dry Run Mode** - Preview commit messages without making changes
- 📊 **Comprehensive Logging** - Detailed logs for debugging and transparency
- 🌐 **Fully Portable** - Works from any git repository

## Installation

### Automated Setup (Recommended)

Run the setup script for easy installation:

```bash
./setup
```

The setup script will:
- Detect your OS (Linux/macOS) and configure the appropriate shell profile
- Give you three options:
  1. **Local Ollama** - Install and run Ollama locally (with macOS performance optimization)
  2. **Remote Ollama** - Connect to an existing Ollama server
  3. **Keep current configuration** - Maintain existing setup
- Handle Ollama installation, model download, and service management automatically
- Set up environment variables in `.bashrc` (Linux) or `.zshrc` (macOS)
- Install `smart-commit` to `/usr/local/bin/` system-wide

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
```bash
# Ollama configuration for smart-commit script
export OLLAMA_API_URL="http://localhost:11434"  # or your remote server IP
export OLLAMA_MODEL="qwen3:8b"

# Optional: Enable macOS performance optimization (for local macOS setups)
export SMART_COMMIT_MACOS_LOCAL="true"
```

Then reload your shell:
```bash
source ~/.bashrc  # Linux
source ~/.zshrc   # macOS
```

## Prerequisites

- **Git repository** - Must be run from within a git repository
- **Ollama** - Either local installation (handled by setup) or remote server access
- **jq** - For JSON parsing (`sudo apt install jq` on Ubuntu/Debian, `brew install jq` on macOS)
- **curl** - For API requests (usually pre-installed)

### Local Ollama (Recommended for new users)
The setup script can automatically:
- Install Ollama via Homebrew (macOS) or curl script (Linux)
- Download the qwen3:8b model (~5GB)
- Start the Ollama service
- Configure optimized settings for your platform

### Remote Ollama (For existing setups)
If you already have Ollama running elsewhere:
- Ensure the server is accessible on port 11434
- Verify the qwen3:8b model is available

## Usage

### Basic Usage
```bash
# Generate commit message and push changes
smart-commit

# Preview commit message without committing
smart-commit --dry-run

# Generate full commit message without character limit
smart-commit --full

# Show help
smart-commit --help
```

### Example Workflow
```bash
# Make your changes
git add .

# Preview the generated commit message
smart-commit --dry-run
# Output: feat(auth): add JWT token validation with expiry handling

# If satisfied, commit and push
smart-commit
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
- `OLLAMA_API_URL` - Ollama server endpoint (default: http://localhost:11434)
- `OLLAMA_MODEL` - Model to use (default: qwen3:8b)
- `SMART_COMMIT_MACOS_LOCAL` - Enable macOS performance optimization (set automatically by setup)

### Temporary Override
```bash
# Use different model for one run
OLLAMA_MODEL="llama3.2:1b" smart-commit --dry-run

# Use different API endpoint
OLLAMA_API_URL="http://localhost:11434" smart-commit
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
Usage: smart-commit [--dry-run] [--full] [--help]

Options:
  --dry-run    Show the generated commit message without committing
  --full       Generate full commit message without character limit truncation
  --help       Show help message and exit

Examples:
  smart-commit              # Analyze, commit, and push changes
  smart-commit --dry-run    # Preview commit message only
  smart-commit --full       # Generate detailed commit message without length limits
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
- ❌ When using `--full` flag (uses detailed analysis)
- ❌ Linux local or remote setups (use full power)

### Platform-Specific Behavior
- **macOS local**: Fast, optimized prompts (~20 seconds)
- **Linux local**: Full detailed analysis (more powerful hardware assumed)
- **Remote servers**: Full detailed analysis (desktop-class performance)
- **All platforms with `--full`**: Maximum detail and accuracy

## Advanced Features

### Smart Message Improvement
The script automatically:
- Validates conventional commit format
- Shortens messages that exceed 72 characters
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
- Verify Ollama server is running and accessible
- Check the model is available: `curl $OLLAMA_API_URL/api/tags`
- Review logs at `~/.cache/smart-commit.log`

**AI response issues**
- Try a different model (e.g., `llama3.2:1b` for faster responses)
- Check Ollama server logs for errors
- Ensure sufficient system resources for the model

### Debugging
Check the detailed log file for troubleshooting:
```bash
cat ~/.cache/smart-commit.log
```

## Recommended Models

- **qwen3:8b** (Recommended) - Best balance of quality and speed, excellent context understanding
- **llama3.2:1b** - Faster responses, good for simple commits
- **qwen3:4b** - Good middle ground if available

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Feel free to suggest improvements or report issues. The script is designed to be easily customizable for different workflows and preferences.