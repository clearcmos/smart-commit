#!/bin/bash

# Smart Git Commit Tool
# Analyzes git changes and generates intelligent commit messages using Ollama

# Configuration - can be overridden by environment variables
OLLAMA_API_URL="${OLLAMA_API_URL:-http://192.168.1.2:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"

# Command line options
DRY_RUN=false

# Portable log file location - use temp directory or user's home
if [ -n "$XDG_CACHE_HOME" ]; then
    LOG_DIR="$XDG_CACHE_HOME"
elif [ -n "$HOME" ]; then
    LOG_DIR="$HOME/.cache"
else
    LOG_DIR="/tmp"
fi
LOG_FILE="$LOG_DIR/smart-commit.log"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--help]"
            echo "  --dry-run    Show the generated commit message without committing"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Initialize log file
init_log() {
    # Ensure log directory exists
    mkdir -p "$LOG_DIR" 2>/dev/null
    # Overwrite log file each run (no history kept)
    echo "=== Smart Git Commit Tool Log - $(date) ===" > "$LOG_FILE"
    log "Starting smart-commit.sh with DRY_RUN=$DRY_RUN"
    log "Log file: $LOG_FILE"
    log "Working directory: $(pwd)"
}

# Function to check if we're in a git repository
check_git_repo() {
    log "Checking if in git repository..."
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log "ERROR: Not in a git repository"
        echo -e "${RED}Error: Not in a git repository${NC}"
        exit 1
    fi
    log "Git repository check passed"
}

# Function to check git status
check_git_status() {
    log "Checking git status..."
    local status=$(git status --porcelain)
    log "Git status output: '$status'"
    if [ -z "$status" ]; then
        log "No changes to commit - exiting"
        echo -e "${YELLOW}No changes to commit${NC}"
        exit 0
    fi
    log "Git status check passed - changes detected"
}

# Function to get git diff
get_git_diff() {
    log "Getting git diff..."
    # Get both staged and unstaged changes
    local staged_diff=$(git diff --cached)
    local unstaged_diff=$(git diff)
    
    log "Staged diff length: ${#staged_diff} characters"
    log "Unstaged diff length: ${#unstaged_diff} characters"
    
    if [ -z "$staged_diff" ] && [ -z "$unstaged_diff" ]; then
        log "No changes to analyze - exiting"
        echo -e "${YELLOW}No changes to analyze${NC}"
        exit 0
    fi
    
    # Combine both diffs
    local combined_diff="$staged_diff"$'\n'"$unstaged_diff"
    log "Combined diff length: ${#combined_diff} characters"
    echo "$combined_diff"
}

# Function to get recent commit history for context
get_recent_commits() {
    local recent_commits=$(git log --oneline -5 --format="%s" 2>/dev/null | head -5)
    if [ -n "$recent_commits" ]; then
        echo "$recent_commits"
    else
        echo "No recent commits found"
    fi
}

# Function to validate commit message format
validate_commit_message() {
    local message="$1"
    log "Validating commit message format: '$message'"
    
    # Check conventional commit format - be more lenient
    if echo "$message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\(.+\))?: ' && [ ${#message} -le 80 ]; then
        log "Commit message follows conventional format"
        return 0
    else
        log "Warning: Generated message doesn't follow conventional format"
        return 1
    fi
}

# Function to generate commit message using Ollama
generate_commit_message() {
    local diff_content="$1"
    local files_status="$2"
    
    # Get recent commits for context
    local recent_commits=$(get_recent_commits)
    log "Recent commits for context: $recent_commits"
    
    # Get key changes summary (first 50 lines of diff)
    local key_changes=$(echo "$diff_content" | head -50)
    local key_changes_summary=$(echo "$key_changes" | grep -E '^[+-]' | head -10)
    
    # Prepare the focused prompt for Ollama
    local prompt="Analyze this git diff and generate a concise conventional commit message (under 72 chars).

Files changed:
$files_status

Key changes summary:
$key_changes_summary

Recent commit style for context:
$recent_commits

Format: type(scope): description
Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert
Focus on WHAT changed and WHY it matters.

Examples:
- feat: add user authentication system
- fix: resolve memory leak in data processing
- refactor: optimize database query performance

Generate ONLY the commit message:"

    log "Preparing Ollama API call..."
    log "API URL: $OLLAMA_API_URL"
    log "Model: $OLLAMA_MODEL"
    log "Prompt length: ${#prompt} characters"
    
    # Call Ollama API
    # Note: Status message moved outside of function to avoid output capture
    
    log "Making curl request to Ollama..."
    local response=$(curl -s --max-time 120 -X POST "$OLLAMA_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$OLLAMA_MODEL\",
            \"prompt\": $(echo "$prompt" | jq -R -s .),
            \"stream\": false
        }")
    
    log "Curl request completed. Response length: ${#response} characters"
    log "Raw response: $response"
    
    # Extract the commit message from response
    local commit_message=$(echo "$response" | jq -r '.response' 2>/dev/null)
    log "Extracted commit message: '$commit_message'"
    
    if [ -z "$commit_message" ] || [ "$commit_message" = "null" ]; then
        log "ERROR: Failed to generate commit message"
        echo -e "${RED}Error: Failed to generate commit message${NC}" >&2
        echo "Ollama response: $response" >&2
        exit 1
    fi
    
    log "Original commit message before cleanup: '$commit_message'"
    
    # Clean up the commit message - extract content after </think> tag
    if echo "$commit_message" | grep -q "<think>"; then
        log "Found <think> tags, extracting content after </think>"
        # Extract everything after </think> and remove any remaining XML-like tags
        commit_message=$(echo "$commit_message" | sed 's/.*<\/think>//' | sed 's/<[^>]*>//g' | grep -v '^$' | tail -1 | xargs)
        log "Extracted from think tags: '$commit_message'"
    else
        # Original cleanup for other thinking patterns
        commit_message=$(echo "$commit_message" | sed -E 's/^[Tt]hinking\.\.\..*$//g' | sed -E 's/^[Tt]hinking:.*$//g' | sed -E 's/^[Tt]hinking.*\.\.\..*$//g' | sed '/^$/d' | head -1 | xargs)
        log "Standard cleanup applied: '$commit_message'"
    fi
    
    log "Commit message after initial cleanup: '$commit_message'"
    
    # If the message is still empty or just whitespace, try to extract from later lines
    if [ -z "$commit_message" ]; then
        log "Commit message empty, trying alternative extraction..."
        commit_message=$(echo "$response" | jq -r '.response' | grep -v -i "thinking" | grep -v "^$" | tail -1 | xargs)
        log "Alternative extraction result: '$commit_message'"
    fi
    
    # Only do improvements if message is clearly problematic
    if [ ${#commit_message} -gt 80 ] || ! echo "$commit_message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)'; then
        log "Commit message needs improvement (length: ${#commit_message} chars)"
        
        # Try to shorten if too long
        if [ ${#commit_message} -gt 80 ]; then
            log "Message too long, asking AI to shorten..."
            local shortened_message=$(shorten_commit_message "$commit_message")
            if [ -n "$shortened_message" ] && [ ${#shortened_message} -lt ${#commit_message} ]; then
                log "Using shortened message: '$shortened_message'"
                commit_message="$shortened_message"
            fi
        fi
        
        # Try to improve format if doesn't start with conventional type
        if ! echo "$commit_message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)'; then
            log "Message doesn't start with conventional type, attempting to improve..."
            local improved_message=$(improve_commit_message "$commit_message")
            if [ -n "$improved_message" ] && [ "$improved_message" != "$commit_message" ]; then
                log "Using improved message: '$improved_message'"
                commit_message="$improved_message"
            fi
        fi
    fi
    
    log "Final commit message: '$commit_message'"
    echo "$commit_message"
}

# Function to improve a commit message that doesn't follow conventional format
improve_commit_message() {
    local original_message="$1"
    log "Attempting to improve non-conventional commit message: '$original_message'"
    
    local improve_prompt="Fix this commit message to follow conventional commit format:

Original: $original_message

Requirements:
- Use format: type(scope): description
- Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert
- Keep under 72 characters
- Be specific and clear

Generate ONLY the improved commit message:"

    local response=$(curl -s --max-time 60 -X POST "$OLLAMA_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$OLLAMA_MODEL\",
            \"prompt\": $(echo "$improve_prompt" | jq -R -s .),
            \"stream\": false
        }")
    
    local improved_message=$(echo "$response" | jq -r '.response' 2>/dev/null)
    
    # Clean up the response
    if echo "$improved_message" | grep -q "<think>"; then
        improved_message=$(echo "$improved_message" | sed -n 's/.*<\/think>\s*//p' | sed 's/<[^>]*>//g' | xargs)
    else
        improved_message=$(echo "$improved_message" | head -1 | xargs)
    fi
    
    log "Improved message: '$improved_message'"
    echo "$improved_message"
}

# Function to shorten a commit message that's too long
shorten_commit_message() {
    local long_message="$1"
    log "Attempting to shorten long commit message: '$long_message'"
    
    local shorten_prompt="Shorten this commit message to under 72 characters while keeping the same meaning:

Original: $long_message

Requirements:
- Keep conventional commit format: type(scope): description
- Maximum 72 characters
- Preserve the core meaning
- Use abbreviations if needed

Generate ONLY the shortened commit message:"

    local response=$(curl -s --max-time 60 -X POST "$OLLAMA_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$OLLAMA_MODEL\",
            \"prompt\": $(echo "$shorten_prompt" | jq -R -s .),
            \"stream\": false
        }")
    
    local shortened_message=$(echo "$response" | jq -r '.response' 2>/dev/null)
    
    # Clean up the response
    if echo "$shortened_message" | grep -q "<think>"; then
        shortened_message=$(echo "$shortened_message" | sed -n 's/.*<\/think>\s*//p' | sed 's/<[^>]*>//g' | xargs)
    else
        shortened_message=$(echo "$shortened_message" | head -1 | xargs)
    fi
    
    log "Shortened message: '$shortened_message'"
    echo "$shortened_message"
}

# Function to stage all changes
stage_changes() {
    echo -e "${BLUE}Staging all changes...${NC}"
    git add .
}

# Function to commit with generated message
commit_changes() {
    local commit_message="$1"
    
    echo -e "${GREEN}Generated commit message:${NC}"
    echo "\"$commit_message\""
    echo
    
    # Ask for confirmation
    read -p "Do you want to commit with this message? (y/N): " confirmation
    
    if [[ $confirmation =~ ^[Yy]$ ]]; then
        git commit -m "$commit_message"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully committed changes${NC}"
            return 0
        else
            echo -e "${RED}Failed to commit changes${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}Commit cancelled${NC}"
        return 1
    fi
}

# Function to push changes
push_changes() {
    echo -e "${BLUE}Pushing changes to remote...${NC}"
    
    # Get current branch
    local current_branch=$(git branch --show-current)
    
    # Check if remote tracking branch exists
    if git rev-parse --verify "origin/$current_branch" >/dev/null 2>&1; then
        git push
    else
        echo -e "${YELLOW}No upstream branch found. Pushing and setting upstream...${NC}"
        git push -u origin "$current_branch"
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Successfully pushed changes${NC}"
    else
        echo -e "${RED}Failed to push changes${NC}"
        exit 1
    fi
}

# Main execution
main() {
    # Initialize logging
    init_log
    
    if [ "$DRY_RUN" = false ]; then
        echo -e "${BLUE}Smart Git Commit Tool${NC}"
        echo "========================="
    fi
    
    # Check prerequisites
    log "Starting main execution flow..."
    check_git_repo
    check_git_status
    
    # Get current status and diff
    if [ "$DRY_RUN" = false ]; then
        echo -e "${BLUE}Analyzing repository changes...${NC}"
    fi
    log "Getting files status..."
    local files_status=$(git status --porcelain)
    log "Getting diff content..."
    local diff_content=$(get_git_diff)
    
    # Display current status (only in non-dry-run mode)
    if [ "$DRY_RUN" = false ]; then
        echo -e "${YELLOW}Current git status:${NC}"
        git status --short
        echo
    fi
    
    # Generate commit message
    log "Generating commit message..."
    if [ "$DRY_RUN" = false ]; then
        echo -e "${BLUE}Analyzing changes and generating commit message...${NC}"
    fi
    local commit_message=$(generate_commit_message "$diff_content" "$files_status")
    log "Generated commit message: '$commit_message'"
    
    # Handle dry run mode
    if [ "$DRY_RUN" = true ]; then
        log "DRY_RUN mode - outputting commit message and exiting"
        echo "$commit_message"
        log "Script completed successfully in DRY_RUN mode"
        exit 0
    fi
    
    # Stage all changes
    log "Staging changes..."
    stage_changes
    
    # Commit changes
    log "Committing changes..."
    if commit_changes "$commit_message"; then
        # Push changes
        log "Pushing changes..."
        push_changes
    fi
    
    log "Script completed"
}

# Run the script
main "$@"
