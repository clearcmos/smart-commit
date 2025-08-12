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

# Function to analyze semantic changes in files
analyze_semantic_changes() {
    local file="$1"
    local change_type="$2"  # "modified", "new", "deleted"
    
    if [ "$change_type" = "new" ] && [ -f "$file" ]; then
        # For new files, analyze the content to understand purpose
        local purpose=""
        local file_size=$(wc -l < "$file" 2>/dev/null || echo "0")
        
        case "$file" in
            *.py)
                local has_classes=$(grep -c "^class " "$file" 2>/dev/null || echo "0")
                local has_functions=$(grep -c "^def " "$file" 2>/dev/null || echo "0")
                local imports=$(grep "^import\|^from.*import" "$file" | head -3)
                
                # Look for universal programming context clues
                local context=""
                local main_purpose=$(grep -E "^def main|if __name__|argparse|click" "$file" | head -1)
                local api_patterns=$(grep -iE "requests|http|api|client|service|oauth" "$file" | head -1)
                local data_patterns=$(grep -iE "pandas|csv|json|database|sql|sqlite" "$file" | head -1)
                local config_vars=$(grep "^[A-Z][A-Z_]*\s*=" "$file" | head -2)
                local docstring=$(grep -A2 '"""' "$file" | head -1 | sed 's/.*"""//' | sed 's/""".*//')
                
                purpose="Python script ($file_size lines, $has_classes classes, $has_functions functions)"
                [ -n "$imports" ] && purpose+="; imports: $(echo "$imports" | tr '\n' ' ')"
                [ -n "$main_purpose" ] && purpose+="; entry: $(echo "$main_purpose" | head -c30)..."
                [ -n "$api_patterns" ] && purpose+="; api: $(echo "$api_patterns" | head -c30)..."
                [ -n "$data_patterns" ] && purpose+="; data: $(echo "$data_patterns" | head -c30)..."
                [ -n "$config_vars" ] && purpose+="; config: $(echo "$config_vars" | tr '\n' ';' | head -c40)..."
                [ -n "$docstring" ] && purpose+="; purpose: $docstring"
                ;;
            *.sh)
                local shebang=$(head -1 "$file" 2>/dev/null)
                local description=$(grep -E "^#.*[Tt]ool|^#.*[Ss]cript|^#.*[Uu]tility" "$file" | head -1 | sed 's/^#\s*//')
                
                # Look for universal shell script patterns
                local function_names=$(grep "^[a-zA-Z_][a-zA-Z0-9_]*() {" "$file" | head -3 | sed 's/() {.*//' | tr '\n' ',')
                local cli_patterns=$(grep -E "\$1|\$@|getopts|while.*getopt|usage\(\)" "$file" | head -1)
                local api_calls=$(grep -iE "curl|wget|http|api" "$file" | head -1)
                local file_ops=$(grep -E "find|grep|sed|awk|\|\||&&" "$file" | head -1)
                
                purpose="Shell script ($file_size lines)"
                [ -n "$description" ] && purpose+=": $description"
                [ -n "$function_names" ] && purpose+="; functions: $function_names"
                [ -n "$cli_patterns" ] && purpose+="; cli: $(echo "$cli_patterns" | head -c30)..."
                [ -n "$api_calls" ] && purpose+="; api: $(echo "$api_calls" | head -c30)..."
                [ -n "$file_ops" ] && purpose+="; ops: $(echo "$file_ops" | head -c30)..."
                ;;
            *.md|*.txt)
                local first_header=$(grep -E "^#|^=" "$file" | head -1 | sed 's/^[#=]*\s*//')
                purpose="Documentation ($file_size lines)"
                [ -n "$first_header" ] && purpose+=": $first_header"
                ;;
            *.json|*.yml|*.yaml)
                purpose="Configuration file ($file_size lines)"
                ;;
        esac
        echo "$purpose"
    elif [ "$change_type" = "modified" ]; then
        # For modified files, analyze what changed
        local additions=$(git diff HEAD -- "$file" | grep "^+" | wc -l 2>/dev/null || echo "0")
        local deletions=$(git diff HEAD -- "$file" | grep "^-" | wc -l 2>/dev/null || echo "0")
        local net_change=$((additions - deletions))
        
        # Look for significant patterns in changes
        local changes_summary=""
        if git diff HEAD -- "$file" | grep -q "^+.*function\|^+.*def \|^+.*class "; then
            changes_summary+="new functions/classes; "
        fi
        if git diff HEAD -- "$file" | grep -q "^-.*function\|^-.*def \|^-.*class "; then
            changes_summary+="removed functions/classes; "
        fi
        if git diff HEAD -- "$file" | grep -q "^+.*import\|^+.*from.*import"; then
            changes_summary+="new imports; "
        fi
        
        # Look for universal programming context changes
        if git diff HEAD -- "$file" | grep -qi "^+.*config\|^+.*settings\|^+.*api\|^+.*auth"; then
            changes_summary+="configuration/api features; "
        fi
        if git diff HEAD -- "$file" | grep -q "^+.*main\|^+.*argparse\|^+.*click\|^+.*\$1\|^+.*\$@"; then
            changes_summary+="CLI/entry point handling; "
        fi
        if git diff HEAD -- "$file" | grep -qi "^+.*import\|^+.*require\|^+.*use "; then
            changes_summary+="new dependencies; "
        fi
        
        # Look for performance optimization patterns
        if git diff HEAD -- "$file" | grep -qi "^+.*concurrent\|^+.*batch\|^+.*thread\|^+.*async\|^+.*parallel\|^+.*performance"; then
            changes_summary+="performance optimizations; "
        fi
        if git diff HEAD -- "$file" | grep -qi "^+.*ThreadPoolExecutor\|^+.*concurrent.futures\|^+.*multiprocessing\|^+.*BatchHttpRequest"; then
            changes_summary+="concurrency/batch processing; "
        fi
        if git diff HEAD -- "$file" | grep -qi "^+.*--fast\|^+.*--max-workers\|^+.*--limited\|^+.*limit.*parameter"; then
            changes_summary+="performance CLI options; "
        fi
        
        echo "Modified (+$additions -$deletions lines); $changes_summary"
    fi
}

# Function to get comprehensive git analysis 
get_git_diff() {
    log "Getting comprehensive git analysis..."
    local analysis_content=""
    local temp_file=$(mktemp)
    
    # Get both staged and unstaged changes
    local staged_diff=$(git diff --cached)
    local unstaged_diff=$(git diff)
    
    log "Staged diff length: ${#staged_diff} characters"
    log "Unstaged diff length: ${#unstaged_diff} characters"
    
    # Build analysis content
    echo -e "\n=== CHANGE ANALYSIS ===" >> "$temp_file"
    
    # Process staged changes
    if [ -n "$staged_diff" ]; then
        echo -e "\nSTAGED CHANGES:" >> "$temp_file"
        git diff --cached --name-status | while IFS=$'\t' read -r status file; do
            case "$status" in
                A) echo "NEW: $file - $(analyze_semantic_changes "$file" "new")" >> "$temp_file" ;;
                M) 
                    local semantic_analysis=$(analyze_semantic_changes "$file" "modified")
                    local code_analysis=$(analyze_code_changes "$file")
                    echo "MODIFIED: $file - $semantic_analysis | $code_analysis" >> "$temp_file" ;;
                D) echo "DELETED: $file" >> "$temp_file" ;;
                R*) echo "RENAMED: $file" >> "$temp_file" ;;
            esac
        done
    fi
    
    # Process unstaged changes  
    if [ -n "$unstaged_diff" ]; then
        echo -e "\nUNSTAGED CHANGES:" >> "$temp_file"
        git diff --name-status | while IFS=$'\t' read -r status file; do
            case "$status" in
                M) echo "MODIFIED: $file - $(analyze_semantic_changes "$file" "modified")" >> "$temp_file" ;;
                D) echo "DELETED: $file" >> "$temp_file" ;;
            esac
        done
    fi
    
    # Process untracked files with detailed analysis
    local untracked_files=$(git ls-files --others --exclude-standard)
    if [ -n "$untracked_files" ]; then
        echo -e "\nNEW UNTRACKED CONTENT:" >> "$temp_file"
        while IFS= read -r file; do
            if [ -f "$file" ]; then
                local file_analysis=$(analyze_semantic_changes "$file" "new")
                echo "NEW FILE: $file - $file_analysis" >> "$temp_file"
                
                # Add purpose/content excerpts for key files
                case "$file" in
                    *.md)
                        local purpose=$(head -5 "$file" | grep -E "^#.*[A-Za-z]" | head -1 | sed 's/^#*\s*//')
                        [ -n "$purpose" ] && echo "  Purpose: $purpose" >> "$temp_file"
                        local key_sections=$(grep "^##" "$file" | head -3 | sed 's/^##\s*//' | tr '\n' ';')
                        [ -n "$key_sections" ] && echo "  Sections: $key_sections" >> "$temp_file"
                        ;;
                    *.py)
                        local main_purpose=$(grep -E "^#.*[Mm]ove|^#.*[Tt]ool|^#.*[Ss]cript" "$file" | head -1)
                        [ -n "$main_purpose" ] && echo "  Purpose: $main_purpose" >> "$temp_file"
                        local key_funcs=$(grep "^def " "$file" | head -3 | sed 's/def //' | sed 's/(.*/:/' | tr '\n' ';')
                        [ -n "$key_funcs" ] && echo "  Key functions: $key_funcs" >> "$temp_file"
                        ;;
                    *.sh)
                        local description=$(grep -E "^#.*[Tt]ool|^#.*[Ss]cript|^#.*[Uu]tility" "$file" | head -1)
                        [ -n "$description" ] && echo "  Purpose: $description" >> "$temp_file"
                        ;;
                esac
            elif [ -d "$file" ]; then
                echo "" >> "$temp_file"
                echo "NEW DIRECTORY: $file/" >> "$temp_file"
                local dir_files=$(find "$file" -name "*.py" -o -name "*.sh" -o -name "*.md" 2>/dev/null | head -5)
                if [ -n "$dir_files" ]; then
                    local file_count=$(echo "$dir_files" | wc -l | tr -d ' ')
                    echo "  Contains: $file_count key files" >> "$temp_file"
                    echo "$dir_files" | while read -r subfile; do
                        [ -n "$subfile" ] && echo "    - $subfile: $(analyze_semantic_changes "$subfile" "new")" >> "$temp_file"
                    done
                else
                    local all_files=$(find "$file" -type f 2>/dev/null | wc -l | tr -d ' ')
                    echo "  Contains: $all_files files" >> "$temp_file"
                fi
            fi
        done <<< "$untracked_files"
    fi
    
    # Add quantitative summary
    local total_additions=$(git diff --cached --numstat 2>/dev/null | awk '{sum+=$1} END {print sum+0}')
    local total_deletions=$(git diff --cached --numstat 2>/dev/null | awk '{sum+=$2} END {print sum+0}')
    local untracked_count=$(echo "$untracked_files" | wc -l 2>/dev/null | tr -d ' ')
    echo -e "\n=== CHANGE SUMMARY ===" >> "$temp_file"
    echo "Staged: +$total_additions -$total_deletions lines" >> "$temp_file"
    [ "$untracked_count" -gt 0 ] && echo "New files/dirs: $untracked_count items" >> "$temp_file"
    
    # Include selected diff excerpts for context
    if [ -n "$staged_diff" ] || [ -n "$unstaged_diff" ]; then
        echo -e "\n=== KEY DIFF CONTEXT ===" >> "$temp_file"
        local combined_diff="$staged_diff"$'\n'"$unstaged_diff"
        # Get meaningful diff lines (function definitions, major changes, performance patterns)
        echo "$combined_diff" | grep -E "^[+-].*def |^[+-].*class |^[+-].*function|^[+-].*import.*concurrent|^[+-].*ThreadPoolExecutor|^[+-].*batch|^[+-].*--fast|^[+-].*--max-workers|^[+-].*--limited|^[+-].*#.*[Tt]ool|^[+-].*#.*[Ss]cript|^@@" | head -30 >> "$temp_file"
    fi
    
    # Read the complete analysis
    analysis_content=$(cat "$temp_file")
    rm -f "$temp_file"
    
    log "Analysis content length: ${#analysis_content} characters"
    echo "$analysis_content"
}

# Function to analyze code changes depth and complexity
analyze_code_changes() {
    local file="$1"
    local additions=$(git diff HEAD -- "$file" | grep "^+" | wc -l 2>/dev/null || echo "0")
    
    # Look for specific patterns that indicate major changes
    local performance_changes=$(git diff HEAD -- "$file" | grep -i "^+.*\(concurrent\|batch\|thread\|async\|parallel\)" | wc -l 2>/dev/null || echo "0")
    local new_functions=$(git diff HEAD -- "$file" | grep "^+.*def " | wc -l 2>/dev/null || echo "0")
    local new_imports=$(git diff HEAD -- "$file" | grep "^+.*import" | wc -l 2>/dev/null || echo "0")
    local new_classes=$(git diff HEAD -- "$file" | grep "^+.*class " | wc -l 2>/dev/null || echo "0")
    
    if [ "$performance_changes" -gt 3 ]; then
        echo "major performance optimizations ($performance_changes perf changes)"
    elif [ "$new_functions" -gt 5 ]; then
        echo "significant functionality expansion ($new_functions new functions)"  
    elif [ "$new_classes" -gt 1 ]; then
        echo "architectural changes ($new_classes new classes)"
    elif [ "$additions" -gt 100 ]; then
        echo "substantial code additions ($additions+ lines)"
    else
        echo "moderate changes ($additions lines)"
    fi
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

# Function to analyze file types for better categorization
analyze_file_types() {
    local files_status="$1"
    local analysis=""
    
    # Count different file types
    local script_files=$(echo "$files_status" | grep -E '\.(sh|py|js|ts|rb|pl)$' | wc -l | tr -d ' ')
    local doc_files=$(echo "$files_status" | grep -E '\.(md|txt|rst|doc)$' | wc -l | tr -d ' ')
    local config_files=$(echo "$files_status" | grep -E '\.(json|yml|yaml|xml|ini|conf)$' | wc -l | tr -d ' ')
    local source_files=$(echo "$files_status" | grep -E '\.(c|cpp|java|go|rs|swift)$' | wc -l | tr -d ' ')
    
    # Count new vs modified
    local new_items=$(echo "$files_status" | grep "^??" | wc -l | tr -d ' ')
    local modified_items=$(echo "$files_status" | grep -E "^[MARC]" | wc -l | tr -d ' ')
    
    if [ "$script_files" -gt 0 ]; then
        analysis+="Scripts: $script_files files; "
    fi
    if [ "$doc_files" -gt 0 ]; then
        analysis+="Documentation: $doc_files files; "
    fi
    if [ "$config_files" -gt 0 ]; then
        analysis+="Config: $config_files files; "
    fi
    if [ "$source_files" -gt 0 ]; then
        analysis+="Source: $source_files files; "
    fi
    if [ "$new_items" -gt 0 ]; then
        analysis+="New: $new_items items; "
    fi
    if [ "$modified_items" -gt 0 ]; then
        analysis+="Modified: $modified_items items; "
    fi
    
    echo "$analysis"
}

# Function to validate commit message format
validate_commit_message() {
    local message="$1"
    log "Validating commit message format: '$message'"
    
    # Check conventional commit format with 100 char limit
    if echo "$message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)(\(.+\))?: ' && [ ${#message} -le 100 ]; then
        log "Commit message follows conventional format"
        return 0
    else
        log "Warning: Generated message doesn't follow conventional format or is too long"
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
    
    # Analyze file types for better categorization
    local file_analysis=$(analyze_file_types "$files_status")
    log "File analysis: $file_analysis"
    
    # Extract new files and directories for separate mention
    local new_files=$(echo "$files_status" | grep "^??" | cut -c4- | head -5)
    local modified_files=$(echo "$files_status" | grep -E "^[MARC]" | cut -c4- | head -5)
    
    # Prepare the enhanced prompt for Ollama
    local prompt="Generate a precise conventional commit message by analyzing these comprehensive git changes.

=== CHANGE ANALYSIS ===
$diff_content

=== FILE STATUS OVERVIEW ===
$files_status

=== RECENT COMMIT PATTERNS ===
$recent_commits

=== COMMIT MESSAGE RULES ===
Format: type(scope): description (max 100 chars)

Types based on actual changes (PRIORITIZE perf when applicable):
- perf: Performance improvements (batch processing, concurrency, optimization, threading) - USE THIS for ThreadPoolExecutor, batch APIs, concurrent processing
- feat: NEW functionality, tools, scripts, or features
- refactor: MAJOR changes to existing code (rewrites, restructuring, architectural changes) 
- fix: Bug fixes or corrections
- docs: Documentation updates
- chore: Maintenance, config, minor updates
- style: Code formatting, no functional changes

STRICT LENGTH LIMIT: Maximum 72 characters total.

Scope guidelines:
- Use specific component names (scripts, gam, api, etc.)
- Omit scope for broad changes across multiple areas
- Use directory names for organized projects

=== ANALYSIS INSTRUCTIONS ===
1. Read the CHANGE ANALYSIS section carefully to understand:
   - What files are new vs modified vs deleted
   - The semantic purpose of new files (tool, script, config, etc.)
   - The extent of modifications (major rewrite vs minor changes)
   
2. For NEW files/directories:
   - If it's a complete new tool/script: use 'feat'
   - If it's documentation: use 'docs' 
   - If it's configuration: use 'chore'

3. For MODIFIED files:
   - If performance optimizations (concurrent/batch/threading): use 'perf'
   - If major rewrite (>50% changed) or architectural changes: use 'refactor'
   - If adding new functions/features: use 'feat'
   - If fixing bugs: use 'fix'
   - If minor updates: use 'chore'

4. Look for the PRIMARY change (the most significant one) and base the commit type on that.
   - Performance improvements with ThreadPoolExecutor/batch APIs use 'perf'
   - Major functionality + performance focus on the dominant change type

5. Be specific about what was actually accomplished, not just what files changed.
   - Instead of \"add limit parameter\" use \"add batch processing, concurrency, and limit parameters\"
   - Include the core technical improvement in the description

Examples of GOOD messages (SHORT and SPECIFIC):
- perf(google-api): add batch processing + concurrency
- feat(gam): add domain ownership checker  
- refactor(scripts): rewrite for CLI usage
- docs(readme): update usage instructions
- perf: optimize with ThreadPoolExecutor + batching

BAD examples (too long, wrong type):
- feat(google-api/move-domain-owned-files) - Performance optimizations with concurrent/batch processing and limit parameters; configuration updates for improved performance. (171 chars - TOO LONG)
- feat: add performance improvements (should be 'perf')

Generate ONLY the commit message, no explanation:"

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
    local commit_message=$(echo "$response" | jq -r '.response' 2>/dev/null)
    log "Extracted commit message: '$commit_message'"
    
    if [ -z "$commit_message" ] || [ "$commit_message" = "null" ]; then
        log "ERROR: Failed to generate commit message"
        echo -e "${RED}Error: Failed to generate commit message${NC}" >&2
        echo "Ollama response: $response" >&2
        exit 1
    fi
    
    log "Original commit message before cleanup: '$commit_message'"
    
    # Clean up the commit message - extract content after </think> tag and handle multiple messages
    if echo "$commit_message" | grep -q "<think>"; then
        log "Found <think> tags, extracting content after </think>"
        # Extract everything after </think> and remove any remaining XML-like tags
        commit_message=$(echo "$commit_message" | sed 's/.*<\/think>//' | sed 's/<[^>]*>//g' | grep -v '^$' | tail -1 | xargs)
        log "Extracted from think tags: '$commit_message'"
    else
        # Original cleanup for other thinking patterns + handle multiple messages
        commit_message=$(echo "$commit_message" | sed -E 's/^[Tt]hinking\.\.\..*$//g' | sed -E 's/^[Tt]hinking:.*$//g' | sed -E 's/^[Tt]hinking.*\.\.\..*$//g' | sed '/^$/d' | head -1 | xargs)
        log "Standard cleanup applied: '$commit_message'"
    fi
    
    # Remove backticks and extract first message if multiple were generated
    commit_message=$(echo "$commit_message" | sed 's/`//g' | head -1 | xargs)
    log "Removed backticks and selected first message: '$commit_message'"
    
    log "Commit message after initial cleanup: '$commit_message'"
    
    # If the message is still empty or just whitespace, try to extract from later lines
    if [ -z "$commit_message" ]; then
        log "Commit message empty, trying alternative extraction..."
        commit_message=$(echo "$response" | jq -r '.response' | grep -v -i "thinking" | grep -v "^$" | tail -1 | xargs)
        log "Alternative extraction result: '$commit_message'"
    fi
    
    # Enhanced validation and auto-correction
    if [ ${#commit_message} -gt 72 ]; then
        log "Warning: Generated message is ${#commit_message} characters (over 72 char limit)"
        # Try to shorten automatically
        commit_message=$(echo "$commit_message" | sed 's/Performance optimizations/optimize/' | sed 's/concurrent\/batch processing/batch+concurrency/' | sed 's/ and / + /' | sed 's/parameters/params/' | sed 's/configuration/config/')
        log "Auto-shortened to: '$commit_message' (${#commit_message} chars)"
    fi
    
    # Auto-correct type based on content analysis
    if echo "$commit_message" | grep -qi "performance\|concurrent\|batch\|thread\|optimization" && ! echo "$commit_message" | grep -qE '^perf'; then
        log "Auto-correcting: Performance-related change should use 'perf' type"
        commit_message=$(echo "$commit_message" | sed 's/^feat/perf/' | sed 's/^refactor/perf/' | sed 's/^chore/perf/')
        log "Corrected to: '$commit_message'"
    fi
    
    if ! echo "$commit_message" | grep -qE '^(feat|fix|docs|style|refactor|test|chore|build|ci|perf|revert)'; then
        log "Warning: Generated message doesn't start with conventional commit type"
    fi
    
    log "Final commit message: '$commit_message'"
    echo "$commit_message"
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
