#!/bin/bash

# Smart Git Commit Tool
# Analyzes git changes and generates intelligent commit messages using Ollama

# Configuration - can be overridden by environment variables
# Support both new and legacy variable names for backward compatibility
AI_API_URL="${AI_API_URL:-${OLLAMA_API_URL:-http://localhost:11434}}"
AI_MODEL="${AI_MODEL:-${OLLAMA_MODEL:-qwen3:8b}}"
AI_BACKEND_TYPE="${AI_BACKEND_TYPE:-ollama}"
SMART_COMMIT_MACOS_LOCAL="${SMART_COMMIT_MACOS_LOCAL:-false}"

# Auto-detect backend type if not explicitly set and using legacy variables
detect_backend_type() {
    if [ -n "$OLLAMA_API_URL" ] && [ -z "$AI_BACKEND_TYPE" ] || [ "$AI_BACKEND_TYPE" = "ollama" ]; then
        # Check if the server responds to llama.cpp health endpoint
        if curl -s --max-time 3 "$AI_API_URL/health" >/dev/null 2>&1; then
            log "Auto-detected llama.cpp backend from health endpoint"
            AI_BACKEND_TYPE="llamacpp"
        elif curl -s --max-time 3 "$AI_API_URL/api/tags" >/dev/null 2>&1; then
            log "Confirmed Ollama backend from tags endpoint"
            AI_BACKEND_TYPE="ollama"
        else
            log "Cannot reach server, keeping default backend type: $AI_BACKEND_TYPE"
        fi
    fi
    log "Final backend type: $AI_BACKEND_TYPE"
}

# Command line options
DRY_RUN=false
ATOMIC_COMMITS=false

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
        --atomic)
            ATOMIC_COMMITS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--atomic] [--help]"
            echo "  --dry-run    Show the generated commit message without committing"
            echo "  --atomic     Create one commit per modified file (professional workflow)"
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

# Function to analyze what actually changed in files
analyze_file_changes() {
    local file="$1"
    local change_type="$2"  # "modified", "new", "deleted"
    
    if [ "$change_type" = "new" ] && [ -f "$file" ]; then
        local file_size=$(wc -l < "$file" 2>/dev/null || echo "0")
        echo "new file ($file_size lines)"
    elif [ "$change_type" = "modified" ]; then
        local additions=$(git diff HEAD -- "$file" | grep "^+" | wc -l 2>/dev/null || echo "0")
        local deletions=$(git diff HEAD -- "$file" | grep "^-" | wc -l 2>/dev/null || echo "0")
        echo "modified (+$additions -$deletions)"
    fi
}

# Function to get focused git analysis
get_git_diff() {
    log "Getting focused git analysis..."
    local analysis_content=""
    local temp_file=$(mktemp)
    
    # Get both staged and unstaged changes
    local staged_diff=$(git diff --cached)
    local unstaged_diff=$(git diff)
    local combined_diff="$staged_diff"$'\n'"$unstaged_diff"
    
    log "Combined diff length: ${#combined_diff} characters"
    
    # Build simple file listing
    echo "=== FILES CHANGED ===" >> "$temp_file"
    
    # Process staged changes
    if [ -n "$staged_diff" ]; then
        git diff --cached --name-status | while IFS=$'\t' read -r status file; do
            case "$status" in
                A) echo "NEW: $file - $(analyze_file_changes "$file" "new")" >> "$temp_file" ;;
                M) echo "MODIFIED: $file - $(analyze_file_changes "$file" "modified")" >> "$temp_file" ;;
                D) echo "DELETED: $file" >> "$temp_file" ;;
                R*) echo "RENAMED: $file" >> "$temp_file" ;;
            esac
        done
    fi
    
    # Process unstaged changes  
    if [ -n "$unstaged_diff" ]; then
        git diff --name-status | while IFS=$'\t' read -r status file; do
            case "$status" in
                M) echo "MODIFIED: $file - $(analyze_file_changes "$file" "modified")" >> "$temp_file" ;;
                D) echo "DELETED: $file" >> "$temp_file" ;;
            esac
        done
    fi
    
    # Process untracked files simply
    local untracked_files=$(git ls-files --others --exclude-standard)
    if [ -n "$untracked_files" ]; then
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                echo "NEW: $file - $(analyze_file_changes "$file" "new")" >> "$temp_file"
            fi
        done <<< "$untracked_files"
    fi
    
    # Include actual diff content (more lines for better context)
    if [ -n "$combined_diff" ]; then
        echo "" >> "$temp_file"
        echo "=== ACTUAL CHANGES ===" >> "$temp_file"
        echo "$combined_diff" | head -200 >> "$temp_file"
    fi
    
    # Read the complete analysis
    analysis_content=$(cat "$temp_file")
    rm -f "$temp_file"
    
    log "Analysis content length: ${#analysis_content} characters"
    echo "$analysis_content"
}





# Function to get smart truncation for large files (macOS optimization)
get_smart_truncation() {
    local content="$1"
    
    # Get first 80 lines (early context)
    echo "$content" | head -80
    echo ""
    echo "... [content truncated for performance] ..."
    echo ""
    # Get lines with function/class definitions for context
    echo "$content" | grep -E "^[+-].*(function|def|class|const|let|var|export|import)" | head -20
}

# Function to generate truncated commit message (for macOS local optimization)
generate_truncated_commit_message() {
    local diff_content="$1"
    local files_status="$2"
    
    # Progressive truncation based on content size
    local truncated_diff
    local diff_size=${#diff_content}
    
    if [ $diff_size -lt 4000 ]; then
        # Small changes: Use full diff
        truncated_diff="$diff_content"
        log "Small diff: using full content ($diff_size chars)"
    elif [ $diff_size -lt 7000 ]; then
        # Medium changes: Use first 150 lines
        truncated_diff=$(echo "$diff_content" | head -150)
        log "Medium diff: using 150 lines (from $diff_size chars)"
    else
        # Large changes: Use smart truncation
        truncated_diff=$(get_smart_truncation "$diff_content")
        log "Large diff: using smart truncation (from $diff_size chars)"
    fi
    
    # Simple, focused prompt for faster processing
    local prompt="You are a Git expert. Generate a conventional commit message.

## Git Changes:
$truncated_diff

## Instructions:
1. Analyze the code changes above
2. Write ONE commit message: type(scope): description  
3. Keep under 90 characters
4. Use present tense verbs
5. Be specific about what changed

## Types:
- feat: new features
- fix: bug fixes
- refactor: code restructuring
- docs: documentation
- chore: maintenance

## Your response:
Write ONLY the commit message, nothing else:"

    log "Using truncated prompt for macOS local optimization"
    log "Truncated diff length: ${#truncated_diff} characters"
    log "Prompt length: ${#prompt} characters"
    
    # Call AI API with truncated content
    local raw_response=$(call_ai_api "$prompt" 60)
    
    if [ -z "$raw_response" ] || [ "$raw_response" = "null" ]; then
        log "ERROR: Failed to get response from Ollama"
        echo "chore: update files"
        return
    fi
    
    # Extract conventional commit pattern
    local commit_message=$(echo "$raw_response" | grep -E '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)' | head -1)
    
    # Clean up the message
    if [ -n "$commit_message" ]; then
        commit_message=$(echo "$commit_message" | sed 's/^["'\'']*//g' | sed 's/["'\'']*$//g' | sed 's/`//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
    else
        # Fallback based on file analysis
        if echo "$diff_content" | grep -q "^+.*def \|^+.*function \|^+.*class "; then
            commit_message="feat: add new functionality"
        elif echo "$diff_content" | grep -q "README\|\.md"; then
            commit_message="docs: update documentation"
        else
            commit_message="chore: update files"
        fi
    fi
    
    log "Generated truncated commit message: '$commit_message'"
    echo "$commit_message"
}

# Function to calculate adaptive timeout based on content complexity
calculate_adaptive_timeout() {
    local diff_content="$1"
    local base_timeout=120
    
    # Calculate complexity factors
    local content_size=${#diff_content}
    local line_count=$(echo "$diff_content" | wc -l)
    local script_indicators=$(echo "$diff_content" | grep -c "function\|if\|for\|while\|case\|do\|done\|^\+.*def \|^\+.*class " || echo 0)
    
    log "Content analysis: size=$content_size chars, lines=$line_count, complexity_indicators=$script_indicators"
    
    # Adaptive timeout calculation
    if [ $content_size -lt 2000 ]; then
        echo $base_timeout  # Simple files: 120s
    elif [ $content_size -lt 5000 ] && [ $script_indicators -lt 10 ]; then
        echo $((base_timeout + 60))  # Medium files: 180s
    elif [ $content_size -lt 8000 ] || [ $script_indicators -gt 15 ]; then
        echo $((base_timeout + 120))  # Complex files: 240s (4 min)
    else
        echo $((base_timeout + 180))  # Very complex: 300s (5 min)
    fi
}

# Function to generate commit message using Ollama with adaptive timeout and fallback
generate_commit_message() {
    local diff_content="$1"
    local files_status="$2"
    
    # Use truncated version for macOS local optimization
    if [ "$SMART_COMMIT_MACOS_LOCAL" = "true" ]; then
        log "Using macOS local optimization (truncated mode)"
        generate_truncated_commit_message "$diff_content" "$files_status"
        return
    fi
    
    # Calculate adaptive timeout for this content
    local adaptive_timeout=$(calculate_adaptive_timeout "$diff_content")
    log "Using adaptive timeout: ${adaptive_timeout}s for content complexity"
    
    # Prepare an optimized prompt for qwen3:8b model
    local prompt="You are a Git expert. Generate a conventional commit message.

## Git Changes:
$diff_content

## Instructions:
1. Carefully analyze the actual code changes above
2. Write ONE commit message in this exact format: type(scope): description
3. Keep it under 90 characters
4. Use present tense verbs
5. Make the description SPECIFIC about what actually changed in the code
6. CRITICAL: Use this EXACT step-by-step process to determine scope:

--- SCOPE ANALYSIS STEPS ---
STEP 1: Look at the file path being analyzed
STEP 2: Check: Does the file path contain a slash (/) ?
STEP 3: IF no slash found → file is at root level → use NO scope (format: type: description)
STEP 4: IF slash found → extract the FIRST directory name before the slash → use as scope (format: type(directory): description)
STEP 5: Verify your choice matches the actual file path structure

--- VALIDATION ---
- Root level files (script.sh, README.md) → NO scope
- Directory files (src/file.js, docs/guide.md) → USE directory as scope
- DO NOT use scopes that don't exist in the actual file paths

## Types:
- feat: new features
- fix: bug fixes  
- refactor: code restructuring
- perf: performance improvements
- docs: documentation
- chore: maintenance/config

## Description Guidelines:
- Analyze ALL changes: both code modifications AND file additions/deletions
- For new documentation files: mention them explicitly like 'add README.md'
- For README/docs updates: look for NEW features, options, examples, or functionality being documented
- For code changes: be specific about functions, methods, algorithms modified
- For small changes: focus on what specific functionality was added/modified, not generic descriptions
- Pay special attention to lines starting with '+' as they show new content
- Avoid generic terms like 'implement features', 'update code', 'add new feature'
- When you see new options, commands, or features, mention them specifically

## SCOPE RULES (MANDATORY):
- Analyze the file paths in the current diff to determine scope
- Extract ONLY the first directory name that actually exists in the file paths
- Examples: 'src/auth/login.js' → scope = 'src'
- Examples: 'docs/api/readme.md' → scope = 'docs'
- Examples: 'tests/unit/helper.py' → scope = 'tests'
- Examples: 'script.sh' (root level) → NO scope, format: 'type: description'
- IMPORTANT: Only use directory names that are ACTUALLY in the file paths being committed
- NEVER use subdirectory names like 'delegate-config' or 'auth'
- ALWAYS use the top-level directory name, OR no scope if file is in root

## Examples (based on actual file paths):
feat(auth): add JWT token validation
fix(parser): handle null values in CSV reader  
perf(api): optimize database query caching
refactor(src): improve path detection algorithm
docs(docs): add CLAUDE.md and improve documentation
docs: add new CLI option documentation
feat(tests): add installation requirements validation
chore(deps): update eslint to v8.0
perf: add adaptive timeout handling for complex files

## Your response:
Write ONLY the commit message, nothing else:"

    log "Preparing Ollama API call..."
    log "API URL: $OLLAMA_API_URL"
    log "Model: $OLLAMA_MODEL"
    log "Prompt length: ${#prompt} characters"
    
    # Call Ollama API
    # Note: Status message moved outside of function to avoid output capture
    
    log "Making AI API request with ${adaptive_timeout}s timeout..."
    
    # Call AI API with adaptive timeout
    local raw_response=$(call_ai_api "$prompt" "$adaptive_timeout")
    local api_exit_code=$?
    
    # Check if request timed out or failed
    if [ $api_exit_code -ne 0 ] || [ -z "$raw_response" ] || [ "$raw_response" = "null" ]; then
        log "TIMEOUT/ERROR: Full analysis failed, falling back to truncated mode"
        log "API exit code: $api_exit_code"
        echo -e "${YELLOW}⚠ Complex file detected - using optimized analysis mode${NC}" >&2
        generate_truncated_commit_message "$diff_content" "$files_status"
        return
    fi
    
    log "AI API request completed. Response length: ${#raw_response} characters"
    log "Raw response: '$raw_response'"
    
    if [ -z "$raw_response" ] || [ "$raw_response" = "null" ]; then
        log "ERROR: Failed to get response from AI API"
        echo -e "${RED}Error: Failed to generate commit message${NC}" >&2
        echo "AI API response was empty or null" >&2
        exit 1
    fi
    
    # Extract commit message with multiple strategies
    local commit_message=""
    
    # First, clean the response by removing markdown code blocks and extra whitespace
    local cleaned_response=$(echo "$raw_response" | sed 's/```[a-z]*//g' | sed 's/```//g' | sed '/^[[:space:]]*$/d' | tr -d '\r')
    log "Cleaned response: '$cleaned_response'"
    
    # Strategy 1: Look for conventional commit pattern with scope
    commit_message=$(echo "$cleaned_response" | grep -E '^[[:space:]]*(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)\(' | head -1 | sed 's/^[[:space:]]*//')
    log "Strategy 1 (with scope): '$commit_message'"
    
    # Strategy 2: Look for conventional commit without scope
    if [ -z "$commit_message" ]; then
        commit_message=$(echo "$cleaned_response" | grep -E '^[[:space:]]*(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert):' | head -1 | sed 's/^[[:space:]]*//')
        log "Strategy 2 (no scope): '$commit_message'"
    fi
    
    # Strategy 3: Get any line that looks like a commit
    if [ -z "$commit_message" ]; then
        commit_message=$(echo "$cleaned_response" | grep -E '(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)' | tail -1 | sed 's/^[[:space:]]*//')
        log "Strategy 3 (any line): '$commit_message'"
    fi
    
    # Clean up the message
    if [ -n "$commit_message" ]; then
        # Remove quotes, backticks, and extra whitespace
        commit_message=$(echo "$commit_message" | sed 's/^["'\'']//g' | sed 's/["'\'']*$//g' | sed 's/`//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
        log "Cleaned commit message: '$commit_message'"
    fi
    
    # Smart length management
    if [ ${#commit_message} -gt 90 ]; then
        log "Warning: Generated message is ${#commit_message} characters (over 90 char limit)"
        
        # Try intelligent shortening first
        original_message="$commit_message"
        
        # Common shortening patterns
        commit_message=$(echo "$commit_message" | sed 's/enhance/improve/' | sed 's/preserve/keep/' | sed 's/remove amount from filenames/remove amounts/' | sed 's/vendor matching/matching/' | sed 's/Unicode support/Unicode/' | sed 's/, / /' | sed 's/  / /g')
        
        log "After intelligent shortening: '$commit_message' (${#commit_message} chars)"
        
        # If still too long, truncate intelligently
        if [ ${#commit_message} -gt 72 ]; then
            # Try to keep the most important parts - type, scope, and main action
            if echo "$commit_message" | grep -q ":"; then
                type_scope=$(echo "$commit_message" | cut -d':' -f1)
                description=$(echo "$commit_message" | cut -d':' -f2- | sed 's/^ *//')
                max_desc_len=$((72 - ${#type_scope} - 2))  # -2 for ": "
                
                if [ ${#description} -gt $max_desc_len ]; then
                    # Truncate description but avoid cutting words
                    truncated_desc=$(echo "$description" | cut -c1-$((max_desc_len - 3)))
                    # Remove trailing partial word
                    truncated_desc=$(echo "$truncated_desc" | sed 's/[^ ]*$//')
                    commit_message="${type_scope}: ${truncated_desc}..."
                fi
            else
                # Fallback: simple truncation
                commit_message=$(echo "$commit_message" | cut -c1-69)"..."
            fi
            log "After truncation: '$commit_message' (${#commit_message} chars)"
        fi
    fi
    
    # Final validation and fallback
    if [ -z "$commit_message" ] || ! echo "$commit_message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)'; then
        log "Warning: No valid commit message found"
        log "Raw response was: $raw_response"
        
        # Analyze the diff to create a better fallback
        if echo "$diff_content" | grep -q "^+.*def \|^+.*function \|^+.*class "; then
            commit_message="feat: add new functionality"
        elif echo "$diff_content" | grep -q "^-.*def \|^-.*function \|^-.*class "; then
            commit_message="refactor: remove unused code"
        elif echo "$diff_content" | grep -q "README\|CHANGELOG\|\.md"; then
            commit_message="docs: update documentation"
        elif echo "$diff_content" | grep -q "package\.json\|requirements\.txt\|Cargo\.toml"; then
            commit_message="chore: update dependencies"
        else
            commit_message="chore: update files"
        fi
        log "Using intelligent fallback: '$commit_message'"
    fi
    
    log "SUCCESS: Full analysis completed with adaptive timeout (${adaptive_timeout}s)"
    log "Final commit message: '$commit_message'"
    echo "$commit_message"
}

# API abstraction functions for different backends
call_ai_api() {
    local prompt="$1"
    local timeout="$2"
    
    log "Calling AI API with backend type: $AI_BACKEND_TYPE"
    log "API URL: $AI_API_URL"
    log "Model: $AI_MODEL"
    
    case "$AI_BACKEND_TYPE" in
        "ollama")
            call_ollama_api "$prompt" "$timeout"
            ;;
        "llamacpp")
            call_llamacpp_api "$prompt" "$timeout"
            ;;
        *)
            log "ERROR: Unknown backend type: $AI_BACKEND_TYPE"
            echo "chore: update files"
            ;;
    esac
}

# Ollama API call
call_ollama_api() {
    local prompt="$1"
    local timeout="$2"
    
    log "Making Ollama API call..."
    local temp_json=$(mktemp)
    cat > "$temp_json" << EOF
{
    "model": "$AI_MODEL",
    "prompt": $(echo "$prompt" | jq -R -s .),
    "stream": false
}
EOF
    
    local response=$(curl -s --max-time "$timeout" -X POST "$AI_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "@$temp_json" 2>/dev/null)
    
    local curl_exit_code=$?
    rm -f "$temp_json"
    
    # Check for timeout or connection errors
    if [ $curl_exit_code -eq 28 ]; then
        log "Ollama API call timed out after ${timeout}s"
        return 1
    elif [ $curl_exit_code -ne 0 ]; then
        log "Ollama API call failed with exit code: $curl_exit_code"
        return 1
    fi
    
    # Extract response from Ollama format
    local extracted_response=$(echo "$response" | jq -r '.response' 2>/dev/null)
    if [ -z "$extracted_response" ] || [ "$extracted_response" = "null" ]; then
        log "Failed to extract response from Ollama JSON: $response"
        return 1
    fi
    
    echo "$extracted_response"
    return 0
}

# llama.cpp API call (OpenAI-compatible format)
call_llamacpp_api() {
    local prompt="$1"
    local timeout="$2"
    
    log "Making llama.cpp API call..."
    
    # Auto-detect model if needed
    local model_name="$AI_MODEL"
    if [ "$model_name" = "auto-detected" ]; then
        log "Auto-detecting model from llama.cpp server..."
        local model_info=$(curl -s --max-time 5 "$AI_API_URL/v1/models" 2>/dev/null)
        if [ -n "$model_info" ]; then
            model_name=$(echo "$model_info" | jq -r '.data[0].id' 2>/dev/null)
            log "Auto-detected model: $model_name"
        else
            log "Failed to auto-detect model, using fallback"
            model_name="model"
        fi
    fi
    
    local temp_json=$(mktemp)
    cat > "$temp_json" << EOF
{
    "model": "$model_name",
    "prompt": $(echo "$prompt" | jq -R -s .),
    "max_tokens": 100,
    "temperature": 0.7,
    "stop": ["\n\n"]
}
EOF
    
    local response=$(curl -s --max-time "$timeout" -X POST "$AI_API_URL/v1/completions" \
        -H "Content-Type: application/json" \
        -d "@$temp_json" 2>/dev/null)
    
    local curl_exit_code=$?
    rm -f "$temp_json"
    
    # Check for timeout or connection errors
    if [ $curl_exit_code -eq 28 ]; then
        log "llama.cpp API call timed out after ${timeout}s"
        return 1
    elif [ $curl_exit_code -ne 0 ]; then
        log "llama.cpp API call failed with exit code: $curl_exit_code"
        return 1
    fi
    
    # Extract response from OpenAI format
    local extracted_response=$(echo "$response" | jq -r '.choices[0].text' 2>/dev/null)
    if [ -z "$extracted_response" ] || [ "$extracted_response" = "null" ]; then
        log "Failed to extract response from llama.cpp JSON: $response"
        return 1
    fi
    
    echo "$extracted_response"
    return 0
}


# Function to get per-file diff analysis
get_file_diff() {
    local file="$1"
    local analysis_content=""
    local temp_file=$(mktemp)
    
    # Build file analysis
    echo "=== FILE CHANGED ===" >> "$temp_file"
    
    # Get file status
    if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
        # File is tracked, check if modified or deleted
        if [ -f "$file" ]; then
            echo "MODIFIED: $file - $(analyze_file_changes "$file" "modified")" >> "$temp_file"
        else
            echo "DELETED: $file" >> "$temp_file"
        fi
    else
        # File is untracked (new)
        if [ -f "$file" ]; then
            echo "NEW: $file - $(analyze_file_changes "$file" "new")" >> "$temp_file"
        fi
    fi
    
    # Include actual diff content
    echo "" >> "$temp_file"
    echo "=== ACTUAL CHANGES ===" >> "$temp_file"
    
    if [ -f "$file" ]; then
        if git ls-files --error-unmatch "$file" >/dev/null 2>&1; then
            # Tracked file - show diff
            git diff HEAD -- "$file" >> "$temp_file"
        else
            # Untracked file - show content
            echo "New file content:" >> "$temp_file"
            head -100 "$file" >> "$temp_file"
        fi
    else
        # Deleted file
        git diff HEAD -- "$file" >> "$temp_file"
    fi
    
    # Read the complete analysis
    analysis_content=$(cat "$temp_file")
    rm -f "$temp_file"
    
    echo "$analysis_content"
}

# Function to validate and optionally edit commits before pushing
validate_commits() {
    local commit_list=("$@")
    local commit_count=${#commit_list[@]}
    
    if [ $commit_count -eq 0 ]; then
        echo -e "${YELLOW}No commits to validate${NC}"
        return
    fi
    
    echo
    echo -e "${BLUE}=== Commit Summary ===${NC}"
    echo "The following commits were created:"
    echo
    
    # Display all commits
    for i in $(seq 0 $((commit_count - 1))); do
        local commit_info="${commit_list[$i]}"
        local file=$(echo "$commit_info" | cut -d'|' -f1)
        local message=$(echo "$commit_info" | cut -d'|' -f2)
        local hash=$(echo "$commit_info" | cut -d'|' -f3)
        
        printf "%d) %s\n   %s\n   [%s]\n\n" $((i + 1)) "$file" "$message" "$hash"
    done
    
    echo -e "${YELLOW}Options:${NC}"
    echo "  ENTER - Accept all commits and push"
    echo "  1-$commit_count - Edit specific commit message"  
    echo "  c - Cancel (keep commits but don't push)"
    echo
    
    while true; do
        read -p "Your choice [ENTER/1-$commit_count/c]: " choice
        
        case "$choice" in
            "")
                # Accept all and push
                echo -e "${GREEN}Pushing all commits...${NC}"
                push_changes
                return
                ;;
            [1-9]|[1-9][0-9])
                if [ "$choice" -ge 1 ] && [ "$choice" -le $commit_count ]; then
                    edit_commit_message "$choice" commit_list
                else
                    echo -e "${RED}Invalid selection. Please choose 1-$commit_count${NC}"
                fi
                ;;
            [Cc])
                echo -e "${YELLOW}Cancelled. Commits remain local (not pushed).${NC}"
                return
                ;;
            *)
                echo -e "${RED}Invalid option. Please choose ENTER, 1-$commit_count, or 'c'${NC}"
                ;;
        esac
    done
}

# Function to edit a specific commit message
edit_commit_message() {
    local selection="$1"
    local -n commits_ref="$2"
    local index=$((selection - 1))
    
    local commit_info="${commits_ref[$index]}"
    local file=$(echo "$commit_info" | cut -d'|' -f1)
    local current_message=$(echo "$commit_info" | cut -d'|' -f2)
    local hash=$(echo "$commit_info" | cut -d'|' -f3)
    
    echo
    echo -e "${BLUE}Editing commit for: ${YELLOW}$file${NC}"
    echo -e "Current message: ${YELLOW}\"$current_message\"${NC}"
    echo
    read -p "Enter new commit message: " new_message
    
    if [ -n "$new_message" ]; then
        # Amend the commit
        git reset --soft HEAD~$((${#commits_ref[@]} - index))
        git commit -m "$new_message"
        
        # Re-apply any commits that came after this one
        for i in $(seq $((index + 1)) $((${#commits_ref[@]} - 1))); do
            local later_commit="${commits_ref[$i]}"
            local later_file=$(echo "$later_commit" | cut -d'|' -f1)
            local later_message=$(echo "$later_commit" | cut -d'|' -f2)
            git add "$later_file"
            git commit -m "$later_message"
        done
        
        # Update the commit info
        local new_hash=$(git rev-parse HEAD~$((${#commits_ref[@]} - index - 1)))
        commits_ref[$index]="$file|$new_message|$new_hash"
        
        echo -e "${GREEN}✓ Commit updated${NC}"
        
        # Ask if they want to edit any others
        echo
        read -p "Edit another commit? [ENTER to continue, 1-${#commits_ref[@]} to edit]: " next_choice
        
        if [ -n "$next_choice" ] && [ "$next_choice" -ge 1 ] && [ "$next_choice" -le ${#commits_ref[@]} ]; then
            edit_commit_message "$next_choice" commits_ref
        else
            echo -e "${GREEN}Pushing all commits...${NC}"
            push_changes
        fi
    else
        echo -e "${YELLOW}No changes made${NC}"
        validate_commits "${commits_ref[@]}"
    fi
}

# Function to handle atomic commits (one commit per file)
handle_atomic_commits() {
    echo -e "${BLUE}Atomic commit mode - creating one commit per file...${NC}"
    
    # Get list of changed files
    local changed_files=$(git status --porcelain | sed 's/^...//')
    
    if [ -z "$changed_files" ]; then
        echo -e "${YELLOW}No changes to commit${NC}"
        exit 0
    fi
    
    # Arrays to store file info and commit messages
    local file_list=()
    local message_list=()
    local diff_list=()
    
    # Reset staging area to ensure clean start
    git reset --quiet
    
    # Phase 1: Generate all commit messages first (no commits yet)
    echo -e "${BLUE}Generating commit messages for all files...${NC}"
    
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        
        echo
        echo -e "${BLUE}Processing file: ${YELLOW}$file${NC}"
        
        # Reset staging area before processing each file
        git reset --quiet
        
        # Stage only this file to get diff
        git add "$file"
        
        # Get diff analysis for this file only
        local file_diff=$(get_file_diff "$file")
        
        # Generate commit message for this file
        local commit_message
        if [ "$ATOMIC_COMMITS" = "true" ] && [ "$DRY_RUN" = "true" ]; then
            echo -e "${BLUE}Generating commit message for $file...${NC}"
        elif [ "$DRY_RUN" = "false" ]; then
            echo -e "${BLUE}Generating commit message for $file...${NC}"
        fi
        
        commit_message=$(generate_commit_message "$file_diff" "")
        
        # Store for later processing
        file_list+=("$file")
        message_list+=("$commit_message")
        diff_list+=("$file_diff")
        
        if [ "$DRY_RUN" = "true" ]; then
            echo -e "${GREEN}File: ${YELLOW}$file${NC}"
            echo -e "${GREEN}Generated commit message:${NC} \"$commit_message\""
        else
            echo -e "${GREEN}Generated message:${NC} \"$commit_message\""
        fi
        
    done <<< "$changed_files"
    
    # Reset staging area after message generation
    git reset --quiet
    
    if [ "$DRY_RUN" = "true" ]; then
        echo
        echo -e "${YELLOW}Dry run complete - no commits made${NC}"
        return
    fi
    
    # Phase 2: Show all messages and get user approval
    echo
    echo -e "${BLUE}=== Proposed Atomic Commits ===${NC}"
    echo "The following commits will be created:"
    echo
    
    for i in $(seq 0 $((${#file_list[@]} - 1))); do
        printf "%d) %s\n   %s\n\n" $((i + 1)) "${file_list[$i]}" "${message_list[$i]}"
    done
    
    echo -e "${YELLOW}Options:${NC}"
    echo "  ENTER - Accept all messages and create commits"
    echo "  1-${#file_list[@]} - Edit specific commit message"  
    echo "  c - Cancel (no commits will be made)"
    echo
    
    # Get user approval before any commits
    while true; do
        read -p "Your choice [ENTER/1-${#file_list[@]}/c]: " choice
        
        case "$choice" in
            "")
                # Accept all and create commits
                break
                ;;
            [1-9]|[1-9][0-9])
                if [ "$choice" -ge 1 ] && [ "$choice" -le ${#file_list[@]} ]; then
                    local index=$((choice - 1))
                    echo
                    echo -e "${BLUE}Editing message for: ${YELLOW}${file_list[$index]}${NC}"
                    echo -e "Current message: ${YELLOW}\"${message_list[$index]}\"${NC}"
                    echo
                    read -p "Enter new commit message: " new_message
                    if [ -n "$new_message" ]; then
                        message_list[$index]="$new_message"
                        echo -e "${GREEN}Message updated${NC}"
                    fi
                    echo
                    # Show updated list
                    echo -e "${BLUE}=== Updated Proposed Commits ===${NC}"
                    for i in $(seq 0 $((${#file_list[@]} - 1))); do
                        printf "%d) %s\n   %s\n\n" $((i + 1)) "${file_list[$i]}" "${message_list[$i]}"
                    done
                else
                    echo -e "${RED}Invalid selection. Please choose 1-${#file_list[@]}${NC}"
                fi
                ;;
            [Cc])
                echo -e "${YELLOW}Cancelled. No commits were made.${NC}"
                return
                ;;
            *)
                echo -e "${RED}Invalid option. Please choose ENTER, 1-${#file_list[@]}, or 'c'${NC}"
                ;;
        esac
    done
    
    # Phase 3: Create the approved commits
    echo -e "${BLUE}Creating commits...${NC}"
    local commit_info_list=()
    
    for i in $(seq 0 $((${#file_list[@]} - 1))); do
        local file="${file_list[$i]}"
        local commit_message="${message_list[$i]}"
        
        echo
        echo -e "${BLUE}Committing: ${YELLOW}$file${NC}"
        
        # Reset and stage only this file
        git reset --quiet
        git add "$file"
        
        # Create the commit
        if git commit -m "$commit_message"; then
            local commit_hash=$(git rev-parse HEAD)
            echo -e "${GREEN}✓ Committed: $file${NC}"
            echo -e "  Message: \"$commit_message\""
            
            # Store commit info for final validation
            commit_info_list+=("$file|$commit_message|$commit_hash")
        else
            echo -e "${RED}✗ Failed to commit: $file${NC}"
        fi
    done
    
    echo
    echo -e "${GREEN}All files committed individually!${NC}"
    
    # Final validation for pushing
    validate_commits "${commit_info_list[@]}"
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
    
    # Ask for confirmation with ENTER as default accept
    read -p "Press ENTER to commit, 'e' to edit message, or 'c' to cancel: " confirmation
    
    if [[ -z "$confirmation" ]]; then
        # Empty input (just ENTER pressed) - accept the message
        git commit -m "$commit_message"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Successfully committed changes${NC}"
            return 0
        else
            echo -e "${RED}Failed to commit changes${NC}"
            return 1
        fi
    elif [[ $confirmation =~ ^[Ee]$ ]]; then
        # User wants to edit the message
        echo -e "${YELLOW}Enter your custom commit message:${NC}"
        read -p "> " custom_message
        
        if [ -n "$custom_message" ]; then
            git commit -m "$custom_message"
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}Successfully committed with custom message${NC}"
                return 0
            else
                echo -e "${RED}Failed to commit changes${NC}"
                return 1
            fi
        else
            echo -e "${RED}Empty commit message. Commit cancelled.${NC}"
            return 1
        fi
    elif [[ $confirmation =~ ^[Cc]$ ]]; then
        # User wants to cancel
        echo -e "${YELLOW}Commit cancelled. No changes were committed.${NC}"
        git reset --quiet  # Unstage the changes
        return 1
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
    
    # Auto-detect backend type
    detect_backend_type
    
    if [ "$DRY_RUN" = false ]; then
        echo -e "${BLUE}Smart Git Commit Tool${NC}"
        echo "========================="
    fi
    
    # Check prerequisites
    log "Starting main execution flow..."
    check_git_repo
    check_git_status
    
    # Handle atomic commits if requested
    if [ "$ATOMIC_COMMITS" = "true" ]; then
        log "Atomic commits mode enabled"
        handle_atomic_commits
        return
    fi
    
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
