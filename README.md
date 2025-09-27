# Smart Commit

AI-powered Git commit message generator that analyzes your git changes and creates conventional commit messages using local AI backends.

## Features

- Generates conventional commit messages (e.g., `feat(auth): add JWT validation`)
- Supports Ollama backend (optimized for local AI)
- Atomic commits mode (separate commit per file) - default behavior
- Traditional single commit mode
- Branch protection for main/master branches
- AI-generated branch names
- Auto-staging and auto-push options
- Interactive preview and editing
- Configurable via files or environment variables

## Installation

### Automated (Recommended)
```bash
git clone https://github.com/clearcmos/smart-commit.git
cd smart-commit
python3 install.py
```

### Manual
```bash
pip install -e .
# or
pipx install .
```

**Requirements**: Python 3.9+, Git, and Ollama server running locally.

## Usage

```bash
# Generate atomic commits (default - one per file)
smart-commit

# Generate single commit for all changes
smart-commit --traditional

# Preview without committing
smart-commit --dry-run

# Force commit on protected branches
smart-commit --force-branch

# Create new branch with AI-generated name
smart-commit --new-branch

# Switch to existing branch
smart-commit --switch-to-branch feature-branch

# Show current configuration
smart-commit config --show

# Test backend connection
smart-commit test
```

## Configuration

Configuration file: `~/.config/smart-commit/config.json`

```json
{
  "ai": {
    "api_url": "http://localhost:11434",
    "model": "qwen2.5-coder:7b-instruct",
    "backend_type": "auto",
    "timeout": 120,
    "max_retries": 3
  },
  "git": {
    "auto_stage": true,
    "auto_push": false,
    "max_diff_lines": 500,
    "atomic_mode": true,
    "protected_branches": ["main", "master"]
  },
  "ui": {
    "interactive": true,
    "use_colors": true,
    "log_level": "INFO"
  }
}
```

### Environment Variables
```bash
export SC_AI__API_URL="http://localhost:11434"
export SC_AI__MODEL="qwen2.5-coder:7b-instruct"
export SC_AI__BACKEND_TYPE="ollama"
export SC_GIT__AUTO_STAGE="true"
export SC_GIT__ATOMIC_MODE="true"
export SC_GIT__PROTECTED_BRANCHES='["main", "master"]'
export SC_UI__LOG_LEVEL="DEBUG"
```

### Configure for Ollama (Default)

```bash
smart-commit config --backend ollama --url http://localhost:11434 --save
```

## AI Backend

**Ollama**: Uses `/api/generate` endpoint for modern, efficient local AI inference.

The tool is optimized for Ollama and will auto-detect the best available model if `backend_type` is set to "auto".

## Atomic Commits (Default)

By default, Smart Commit creates individual commits for each changed file:

```bash
smart-commit  # Creates one commit per file
```

Shows a preview table of proposed commits, allows editing individual messages, then creates commits after approval.

## Branch Protection

Smart Commit protects main/master branches by default. When on a protected branch:

1. Prompts to create a new branch with AI-generated name
2. Option to switch to existing branch
3. Option to force commit (with `--force-branch`)

## Troubleshooting

### Backend Connection Issues
```bash
# Test backend health
smart-commit test --all

# Check if Ollama is running
curl http://localhost:11434/api/tags

# Enable debug logging
export SC_UI__LOG_LEVEL="DEBUG"
smart-commit --verbose
```

### Common Issues

**"Not a valid Git repository"**: Run from within a git repository
**"AI backend health check failed"**: Ensure your AI server is running and accessible
**"No changes detected"**: Stage files with `git add` or enable `auto_stage`
**"Protected branch"**: Use `--force-branch`, `--new-branch`, or `--switch-to-branch`

### Debug Mode
Log file location: `~/.cache/smart-commit/smart-commit.log`

## Development

```bash
pip install -e .

# Code quality
black smart_commit/
mypy smart_commit/
pytest tests/
```

## License

MIT