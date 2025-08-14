#!/bin/bash

# Smart Git Commit Tool
# Analyzes git changes and generates intelligent commit messages using Ollama

# Configuration - can be overridden by environment variables
OLLAMA_API_URL="${OLLAMA_API_URL:-http://localhost:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:8b}"
SMART_COMMIT_MACOS_LOCAL="${SMART_COMMIT_MACOS_LOCAL:-false}"

# Command line options
DRY_RUN=false
FULL_MESSAGE=false
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
        --full)
            FULL_MESSAGE=true
            shift
            ;;
        --atomic)
            ATOMIC_COMMITS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run] [--full] [--atomic] [--help]"
            echo "  --dry-run    Show the generated commit message without committing"
            echo "  --full       Generate full commit message without character limit truncation"
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
    log "Starting smart-commit.sh with DRY_RUN=$DRY_RUN, FULL_MESSAGE=$FULL_MESSAGE"
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
3. Keep under 72 characters
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
    
    # Call Ollama API with truncated content
    local temp_json=$(mktemp)
    cat > "$temp_json" << EOF
{
    "model": "$OLLAMA_MODEL",
    "prompt": $(echo "$prompt" | jq -R -s .),
    "stream": false
}
EOF
    
    local response=$(curl -s --max-time 60 -X POST "$OLLAMA_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "@$temp_json")
    
    rm -f "$temp_json"
    
    # Extract commit message (simplified extraction)
    local raw_response=$(echo "$response" | jq -r '.response' 2>/dev/null)
    
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

# Function to generate commit message using Ollama
generate_commit_message() {
    local diff_content="$1"
    local files_status="$2"
    local use_full_message="$3"
    
    # Use truncated version for macOS local optimization (but not when --full flag is used)
    if [ "$SMART_COMMIT_MACOS_LOCAL" = "true" ] && [ "$use_full_message" != "true" ]; then
        generate_truncated_commit_message "$diff_content" "$files_status"
        return
    fi
    
    # Prepare an optimized prompt for qwen3:8b model
    local prompt="You are a Git expert. Generate a conventional commit message.

## Git Changes:
$diff_content

## Instructions:
1. Carefully analyze the actual code changes above
2. Write ONE commit message in this exact format: type(scope): description
3. Keep it under 72 characters
4. Use present tense verbs
5. Make the description SPECIFIC about what actually changed in the code
6. CRITICAL: For scope, you MUST use the top-level directory name from file paths
7. Look at file paths like 'gam/delegate-config/file.py' → scope MUST be 'gam'

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
- Extract ONLY the first directory from file paths
- Examples: 'gam/delegate-config/file.py' → scope = 'gam'
- Examples: 'src/auth/login.js' → scope = 'src'
- Examples: 'docs/api/readme.md' → scope = 'docs'
- NEVER use subdirectory names like 'delegate-config' or 'auth'
- ALWAYS use the top-level directory name

## Examples:
feat(auth): add JWT token validation
fix(parser): handle null values in CSV reader
perf(api): optimize database query caching
refactor(gam): improve path detection algorithm
docs(gam): add CLAUDE.md and improve path detection
docs: add new CLI option documentation
docs(readme): add installation requirements
chore(deps): update eslint to v8.0

## Your response:
Write ONLY the commit message, nothing else:"

    log "Preparing Ollama API call..."
    log "API URL: $OLLAMA_API_URL"
    log "Model: $OLLAMA_MODEL"
    log "Prompt length: ${#prompt} characters"
    
    # Call Ollama API
    # Note: Status message moved outside of function to avoid output capture
    
    log "Making curl request to Ollama..."
    # Create a temporary file with the JSON payload to avoid escaping issues
    local temp_json=$(mktemp)
    cat > "$temp_json" << EOF
{
    "model": "$OLLAMA_MODEL",
    "prompt": $(echo "$prompt" | jq -R -s .),
    "stream": false
}
EOF
    
    local response=$(curl -s --max-time 120 -X POST "$OLLAMA_API_URL/api/generate" \
        -H "Content-Type: application/json" \
        -d "@$temp_json")
    
    rm -f "$temp_json"
    
    log "Curl request completed. Response length: ${#response} characters"
    log "Raw response: $response"
    
    # Extract the commit message from response
    local raw_response=$(echo "$response" | jq -r '.response' 2>/dev/null)
    log "Raw response: '$raw_response'"
    
    if [ -z "$raw_response" ] || [ "$raw_response" = "null" ]; then
        log "ERROR: Failed to get response from Ollama"
        echo -e "${RED}Error: Failed to generate commit message${NC}" >&2
        echo "Ollama response: $response" >&2
        exit 1
    fi
    
    # Extract commit message with multiple strategies
    local commit_message=""
    
    # Strategy 1: Look for conventional commit pattern first
    commit_message=$(echo "$raw_response" | grep -E '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)\(' | head -1)
    log "Strategy 1 (with scope): '$commit_message'"
    
    # Strategy 2: Look for conventional commit without scope
    if [ -z "$commit_message" ]; then
        commit_message=$(echo "$raw_response" | grep -E '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert):' | head -1)
        log "Strategy 2 (no scope): '$commit_message'"
    fi
    
    # Strategy 3: Get the last line that looks like a commit
    if [ -z "$commit_message" ]; then
        commit_message=$(echo "$raw_response" | grep -E '(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)' | tail -1)
        log "Strategy 3 (any line): '$commit_message'"
    fi
    
    # Clean up the message
    if [ -n "$commit_message" ]; then
        # Remove quotes, backticks, and extra whitespace
        commit_message=$(echo "$commit_message" | sed 's/^["'\'']//g' | sed 's/["'\'']*$//g' | sed 's/`//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
        log "Cleaned commit message: '$commit_message'"
    fi
    
    # Smart length management (skip if using full message mode)
    if [ "$use_full_message" != "true" ] && [ ${#commit_message} -gt 72 ]; then
        log "Warning: Generated message is ${#commit_message} characters (over 72 char limit)"
        
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
    
    log "Final commit message: '$commit_message'"
    echo "$commit_message"
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
    
    # Array to store commit info for validation
    local commit_info_list=()
    
    # Process each file individually
    while IFS= read -r file; do
        [ -z "$file" ] && continue
        
        echo
        echo -e "${BLUE}Processing file: ${YELLOW}$file${NC}"
        
        # Stage only this file
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
        
        commit_message=$(generate_commit_message "$file_diff" "" "$FULL_MESSAGE")
        
        if [ "$DRY_RUN" = "true" ]; then
            echo -e "${GREEN}File: ${YELLOW}$file${NC}"
            echo -e "${GREEN}Generated commit message:${NC} \"$commit_message\""
        else
            # Commit this file
            if git commit -m "$commit_message"; then
                local commit_hash=$(git rev-parse HEAD)
                echo -e "${GREEN}✓ Committed: $file${NC}"
                echo -e "  Message: \"$commit_message\""
                
                # Store commit info for validation
                commit_info_list+=("$file|$commit_message|$commit_hash")
            else
                echo -e "${RED}✗ Failed to commit: $file${NC}"
            fi
        fi
        
    done <<< "$changed_files"
    
    if [ "$DRY_RUN" = "false" ]; then
        echo
        echo -e "${GREEN}All files committed individually!${NC}"
        
        # Validate commits before pushing
        validate_commits "${commit_info_list[@]}"
    else
        echo
        echo -e "${YELLOW}Dry run complete - no commits made${NC}"
    fi
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
    read -p "Press ENTER to commit, or 'n' to edit message: " confirmation
    
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
    elif [[ $confirmation =~ ^[Nn]$ ]]; then
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
    local commit_message=$(generate_commit_message "$diff_content" "$files_status" "$FULL_MESSAGE")
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
