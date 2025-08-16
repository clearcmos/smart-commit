"""
AI prompt templates with optimization strategies.
"""

from typing import List, Dict
from ..git_ops.repository import FileChange, RepositoryState


class PromptBuilder:
    """Build optimized prompts for different scenarios."""
    
    def __init__(self, character_limit: int = 90, optimized_mode: bool = False):
        """Initialize prompt builder."""
        self.character_limit = character_limit
        self.optimized_mode = optimized_mode
    
    def build_commit_prompt(
        self, 
        repo_state: RepositoryState,
        recent_commits: List[Dict] = None,
        file_context: FileChange = None
    ) -> str:
        """Build commit message generation prompt."""
        
        if self.optimized_mode:
            return self._build_optimized_prompt(repo_state, file_context)
        else:
            return self._build_detailed_prompt(repo_state, recent_commits, file_context)
    
    def _build_optimized_prompt(self, repo_state: RepositoryState, file_context: FileChange = None) -> str:
        """Build optimized prompt for fast processing."""
        
        # For single file context (atomic commits)
        if file_context:
            diff_content = self._truncate_diff(file_context.diff_content, 150)
            scope_hint = f" Use scope '{file_context.scope}' if appropriate." if file_context.scope else ""
            
            return f"""Analyze this git change and write ONE conventional commit message:

## File: {file_context.file_path}
```diff
{diff_content}
```

## Instructions:
1. Write ONE commit message: type(scope): description
2. Keep under {self.character_limit} characters
3. Use present tense verbs
4. Be specific about what changed{scope_hint}

## Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert

Your response (commit message only):"""
        
        # For multiple files
        else:
            all_changes = self._summarize_changes(repo_state.all_changes)
            
            return f"""Analyze these git changes and write ONE conventional commit message:

## Changes Summary:
{all_changes}

## Instructions:
1. Write ONE commit message: type(scope): description  
2. Keep under {self.character_limit} characters
3. Use present tense verbs
4. Focus on the main change

## Types: feat, fix, docs, style, refactor, test, chore, build, ci, perf, revert

Your response (commit message only):"""
    
    def _build_detailed_prompt(
        self, 
        repo_state: RepositoryState, 
        recent_commits: List[Dict] = None,
        file_context: FileChange = None
    ) -> str:
        """Build detailed prompt for comprehensive analysis."""
        
        # Build context sections
        context_sections = []
        
        # Git changes section
        if file_context:
            diff_content = self._truncate_diff(file_context.diff_content, 300)
            context_sections.append(f"""## File: {file_context.file_path}
```diff
{diff_content}
```""")
        else:
            changes_summary = self._build_changes_summary(repo_state.all_changes)
            context_sections.append(f"## Git Changes:\n{changes_summary}")
        
        # Recent commits context
        if recent_commits:
            commits_text = "\n".join([
                f"- {commit['hash']}: {commit['message']}" 
                for commit in recent_commits[:3]
            ])
            context_sections.append(f"## Recent Commits (for style context):\n{commits_text}")
        
        # Instructions section
        instructions = self._build_detailed_instructions(file_context)
        
        return "\n\n".join(context_sections + [instructions])
    
    def _build_detailed_instructions(self, file_context: FileChange = None) -> str:
        """Build detailed instructions section."""
        
        scope_rules = ""
        if file_context and file_context.scope:
            scope_rules = f"""
## SCOPE RULES (MANDATORY):
- For file {file_context.file_path}, use scope '{file_context.scope}' if appropriate
- Extract scope from the directory structure of the file being modified
- Examples: 'src/auth/login.js' → scope = 'src', 'docs/api.md' → scope = 'docs'
- Root level files → NO scope (format: type: description)
"""
        else:
            scope_rules = """
## SCOPE RULES (MANDATORY):
- Analyze file paths to determine appropriate scope
- Use the first directory name from file paths as scope
- Examples: 'src/components/Button.js' → scope = 'src'
- Examples: 'tests/unit/helpers.py' → scope = 'tests'  
- Root level files → NO scope (format: type: description)
"""
        
        return f"""## Instructions:
1. Carefully analyze the code changes above
2. Write ONE commit message in this exact format: type(scope): description
3. Keep it under {self.character_limit} characters
4. Use present tense verbs
5. Make the description SPECIFIC about what actually changed in the code
6. CRITICAL: Follow the scope rules below exactly

{scope_rules}

## Types:
- feat: new features
- fix: bug fixes
- docs: documentation changes
- style: formatting, missing semicolons, etc
- refactor: code change that neither fixes bug nor adds feature
- test: adding missing tests
- chore: updating grunt tasks etc; no production code change
- build: changes affecting build system or dependencies
- ci: changes to CI configuration files and scripts
- perf: performance improvements
- revert: reverting previous commits

## Quality Guidelines:
- Pay special attention to lines starting with '+' as they show new content
- Avoid generic terms like 'implement features', 'update code', 'add new feature'
- When you see new options, commands, or features, mention them specifically
- Focus on the business value or technical improvement

## Examples (based on actual file paths):
feat(auth): add JWT token validation with expiry handling
fix(api): resolve memory leak in user session management  
perf(database): optimize query performance with connection pooling
refactor(components): simplify button component props interface
docs(readme): add installation requirements and setup guide
test(utils): add unit tests for date formatting functions

## Your response:
Write ONLY the commit message, nothing else:"""
    
    def _summarize_changes(self, changes: List[FileChange]) -> str:
        """Create a brief summary of changes."""
        if not changes:
            return "No changes detected"
        
        summary_lines = []
        for change in changes[:5]:  # Limit to first 5 files
            action = {
                'M': 'Modified',
                'A': 'Added', 
                'D': 'Deleted',
                'R': 'Renamed',
                'C': 'Copied'
            }.get(change.change_type, 'Changed')
            
            summary_lines.append(f"- {action}: {change.file_path}")
        
        if len(changes) > 5:
            summary_lines.append(f"... and {len(changes) - 5} more files")
        
        return "\n".join(summary_lines)
    
    def _build_changes_summary(self, changes: List[FileChange]) -> str:
        """Build detailed changes summary with diff content."""
        if not changes:
            return "No changes detected"
        
        summary_parts = []
        
        for i, change in enumerate(changes[:3]):  # Show detailed diff for first 3 files
            diff_content = self._truncate_diff(change.diff_content, 200)
            summary_parts.append(f"""### {change.file_path} ({change.change_type})
```diff
{diff_content}
```""")
        
        if len(changes) > 3:
            remaining = changes[3:]
            file_list = ", ".join([c.file_path for c in remaining[:5]])
            if len(remaining) > 5:
                file_list += f" and {len(remaining) - 5} more"
            summary_parts.append(f"\n### Additional files changed: {file_list}")
        
        return "\n\n".join(summary_parts)
    
    def _truncate_diff(self, diff_content: str, max_lines: int) -> str:
        """Truncate diff content to specified number of lines."""
        if not diff_content:
            return "No diff content available"
        
        lines = diff_content.split('\n')
        if len(lines) <= max_lines:
            return diff_content
        
        # Keep early context and show truncation
        early_lines = lines[:max_lines - 2]
        truncated_count = len(lines) - len(early_lines)
        
        early_lines.append(f"... [truncated: {truncated_count} more lines]")
        
        return '\n'.join(early_lines)