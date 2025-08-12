# Smart Git Commit Tool

An intelligent bash script that analyzes your git changes and generates meaningful commit messages using AI via Ollama.

## Features

- 🤖 **AI-Powered Analysis** - Uses Ollama models to understand your code changes
- 📝 **Conventional Commits** - Generates properly formatted commit messages (feat:, fix:, etc.)
- 🎯 **Context-Aware** - Considers recent commit history for consistent messaging style
- ⚡ **Smart Validation** - Automatically improves and shortens messages when needed
- 🔍 **Dry Run Mode** - Preview commit messages without making changes
- 📊 **Comprehensive Logging** - Detailed logs for debugging and transparency
- 🌐 **Fully Portable** - Works from any git repository

## Installation

### 1. Copy to your bin directory
```bash
# User-specific installation
cp smart-commit.sh ~/bin/smart-commit
chmod +x ~/bin/smart-commit

# Or system-wide installation
sudo cp smart-commit.sh /usr/local/bin/smart-commit
```

### 2. Configure environment variables
Add to your `~/.bashrc` or `~/.bash_profile`:
```bash
# Ollama configuration for smart-commit script
export OLLAMA_API_URL="http://192.168.1.2:11434"
export OLLAMA_MODEL="qwen3:8b"
```

Then reload your shell:
```bash
source ~/.bashrc
```

## Prerequisites

- **Git repository** - Must be run from within a git repository
- **Ollama server** - Running with a capable model (qwen3:8b recommended)
- **jq** - For JSON parsing (`sudo apt install jq` on Ubuntu/Debian)
- **curl** - For API requests (usually pre-installed)

## Usage

### Basic Usage
```bash
# Generate commit message and push changes
smart-commit

# Preview commit message without committing
smart-commit --dry-run

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
- `OLLAMA_API_URL` - Ollama server endpoint (default: http://192.168.1.2:11434)
- `OLLAMA_MODEL` - Model to use (default: qwen3:8b)

### Temporary Override
```bash
# Use different model for one run
OLLAMA_MODEL="llama3.2:1b" smart-commit --dry-run

# Use different API endpoint
OLLAMA_API_URL="http://localhost:11434" smart-commit
```

## Generated Commit Message Examples

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
Usage: smart-commit [--dry-run] [--help]

Options:
  --dry-run    Show the generated commit message without committing
  --help       Show help message and exit

Examples:
  smart-commit              # Analyze, commit, and push changes
  smart-commit --dry-run    # Preview commit message only
```

## Advanced Features

### Smart Message Improvement
The script automatically:
- Validates conventional commit format
- Shortens messages that exceed 80 characters
- Improves messages that don't follow proper format
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