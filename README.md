# Smart Commit

AI-powered Git commit message generator that analyzes your git changes and creates conventional commit messages using local AI backends.

## Features

- Generates conventional commit messages (e.g., `feat(auth): add JWT validation`)
- Supports Ollama and llama.cpp backends
- Atomic commits mode (separate commit per file)
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

**Requirements**: Python 3.9+, Git, and either Ollama or llama.cpp server running.

## Usage

```bash
# Generate and create commit
smart-commit

# Preview without committing
smart-commit --dry-run

# Create separate commits for each file
smart-commit --atomic

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
    "model": "qwen3:8b",
    "backend_type": "auto",
    "timeout": 120,
    "max_retries": 3
  },
  "git": {
    "auto_stage": true,
    "auto_push": false,
    "max_diff_lines": 500,
    "atomic_mode": false
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
export SC_AI__API_URL="http://localhost:8080"
export SC_AI__MODEL="qwen2.5-coder:7b"
export SC_AI__BACKEND_TYPE="llamacpp"
export SC_GIT__AUTO_STAGE="true"
export SC_UI__LOG_LEVEL="DEBUG"
```

### Configure for Ollama

```bash
smart-commit config --backend ollama --url http://localhost:11434 --save
```

### Configure for llama.cpp

```bash
smart-commit config --backend llamacpp --url http://localhost:8080 --save
```

## AI Backends

**Ollama**: Uses `/api/generate` endpoint
**llama.cpp**: Uses `/v1/completions` endpoint (OpenAI-compatible)

The tool automatically detects which backend is running if `backend_type` is set to "auto".

## Atomic Commits

The `--atomic` flag creates individual commits for each changed file:

```bash
smart-commit --atomic
```

Shows a preview table of proposed commits, allows editing individual messages, then creates commits after approval.

## Troubleshooting

### Backend Connection Issues
```bash
# Test backend health
smart-commit test --all

# Check if services are running
curl http://localhost:11434/api/tags    # Ollama
curl http://localhost:8080/health       # llama.cpp

# Enable debug logging
export SC_UI__LOG_LEVEL="DEBUG"
smart-commit --verbose
```

### Common Issues

**"Not a valid Git repository"**: Run from within a git repository
**"AI backend health check failed"**: Ensure your AI server is running and accessible
**"No changes detected"**: Stage files with `git add` or enable `auto_stage`

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