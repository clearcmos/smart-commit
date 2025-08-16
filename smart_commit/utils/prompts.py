"""
AI prompt templates with optimization strategies.
Based on 2025 best practices for AI commit message generation.
"""

from typing import List, Dict, Optional
from ..git_ops.repository import FileChange, RepositoryState


class PromptBuilder:
    """Build optimized prompts for different scenarios."""
    
    def __init__(self, character_limit: int = 72, optimized_mode: bool = False):
        """Initialize prompt builder with conventional commit standards."""
        self.character_limit = character_limit  # Conventional commit standard
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
        """Build optimized prompt for fast processing using 2025 best practices."""
        
        # For single file context (atomic commits)
        if file_context:
            return self._build_single_file_prompt(file_context)
        
        # For multiple files
        else:
            return self._build_multi_file_prompt(repo_state.all_changes)
    
    def _build_single_file_prompt(self, file_context: FileChange) -> str:
        """Build targeted single-file prompt with specific context."""
        
        file_path = file_context.file_path
        change_type = file_context.change_type
        
        # Build highly specific prompts based on exact context
        if change_type == 'D':
            return self._build_deletion_prompt(file_context)
        elif change_type == 'A':
            return self._build_addition_prompt(file_context)
        else:
            return self._build_modification_prompt(file_context)
    
    def _build_deletion_prompt(self, file_context: FileChange) -> str:
        """Build highly specific deletion prompt."""
        file_path = file_context.file_path
        
        # Very specific handling for known files
        if file_path == 'setup':
            return """Generate a conventional commit message for this file deletion:

FILE: setup (DELETED)
CONTEXT: This was a bash setup script being removed as part of migration from bash to Python implementation.

REQUIREMENTS:
- Format: type(scope): description  
- Max 72 characters
- Use imperative mood
- Type should be "chore" (maintenance/cleanup)
- Be specific about bash migration

EXAMPLES:
- chore: remove deprecated bash setup script
- chore: remove old setup script after Python migration

COMMIT MESSAGE:"""
        
        elif file_path == 'smart-commit.sh':
            return """Generate a conventional commit message for this file deletion:

FILE: smart-commit.sh (DELETED)  
CONTEXT: This was the main bash implementation being removed and replaced by Python implementation.

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters  
- Use imperative mood
- Type should be "chore" (maintenance/cleanup)
- Be specific about bash-to-python migration

EXAMPLES:
- chore: remove legacy bash implementation
- chore: remove deprecated bash smart-commit script

COMMIT MESSAGE:"""
        
        elif file_path.endswith('.sh'):
            return f"""Generate a conventional commit message for this file deletion:

FILE: {file_path} (DELETED)
CONTEXT: Shell script being removed as part of codebase migration.

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Use imperative mood  
- Type should be "chore" 

EXAMPLES:
- chore: remove deprecated shell script
- chore: remove old bash utilities

COMMIT MESSAGE:"""
        
        else:
            return f"""Generate a conventional commit message for this file deletion:

FILE: {file_path} (DELETED)

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Use imperative mood
- Type should be "chore" or "refactor"

COMMIT MESSAGE:"""
    
    def _build_addition_prompt(self, file_context: FileChange) -> str:
        """Build specific addition prompt."""
        file_path = file_context.file_path
        
        if 'deprecated' in file_path:
            return f"""Generate a conventional commit message for this file addition:

FILE: {file_path} (ADDED)
CONTEXT: Creating directory for archiving deprecated files.

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Type should be "chore"

EXAMPLES:
- chore: create deprecated directory for old files
- chore: add archive folder for legacy files

COMMIT MESSAGE:"""
        
        else:
            file_type = self._determine_file_type(file_path)
            scope = self._analyze_scope(file_path)
            scope_text = f"(scope: {scope})" if scope else ""
            
            return f"""Generate a conventional commit message for this file addition:

FILE: {file_path} (ADDED)
TYPE: {file_type} {scope_text}

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Use imperative mood
- Type: "feat" for new features, "chore" for tooling, "test" for tests

COMMIT MESSAGE:"""
    
    def _build_modification_prompt(self, file_context: FileChange) -> str:
        """Build specific modification prompt."""
        file_path = file_context.file_path
        purpose = self._analyze_file_purpose(file_context)
        scope = self._analyze_scope(file_path)
        
        # Specific handling for known files
        if 'repository.py' in file_path:
            return f"""Generate a conventional commit message for this file modification:

FILE: {file_path} (MODIFIED)
PURPOSE: {purpose or "Improving git operations handling"}
SCOPE: {scope or "git"}

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Type should be "fix" (if bug fix) or "feat" (if enhancement)

EXAMPLES:
- fix(git): handle deleted files in atomic commits
- feat(git): add support for staged deletions

COMMIT MESSAGE:"""
        
        elif 'prompts.py' in file_path:
            return f"""Generate a conventional commit message for this file modification:

FILE: {file_path} (MODIFIED)  
PURPOSE: {purpose or "Enhancing AI prompt generation"}
SCOPE: {scope or "ai"}

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Type should be "feat" (enhancement) or "fix" (bug fix)

EXAMPLES:
- feat(ai): improve context analysis for commit messages
- fix(ai): enhance prompt generation for deleted files

COMMIT MESSAGE:"""
        
        else:
            diff_preview = self._get_intelligent_diff(file_context)[:200] + "..." if file_context.diff_content else "No diff available"
            
            return f"""Generate a conventional commit message for this file modification:

FILE: {file_path} (MODIFIED)
SCOPE: {scope or "core"}

DIFF PREVIEW:
{diff_preview}

REQUIREMENTS:
- Format: type(scope): description
- Max 72 characters
- Use imperative mood
- Be specific about the change

COMMIT MESSAGE:"""
    
    def _build_multi_file_prompt(self, changes: List[FileChange]) -> str:
        """Build sophisticated multi-file prompt."""
        
        # Analyze the overall change pattern
        change_pattern = self._analyze_change_pattern(changes)
        
        prompt_sections = []
        
        # Header
        prompt_sections.append("""You are an expert Git commit message generator. Generate ONE conventional commit message that summarizes all changes.

REQUIREMENTS:
- Follow Conventional Commits 1.0.0 specification exactly
- Format: type(scope): description
- Maximum {char_limit} characters
- Use imperative mood
- Focus on the primary purpose of the changes
- Output ONLY the commit message, nothing else""".format(char_limit=self.character_limit))
        
        # Change pattern analysis
        prompt_sections.append(f"""CHANGE PATTERN ANALYSIS:
{change_pattern}""")
        
        # Summarized changes
        changes_summary = self._build_intelligent_changes_summary(changes)
        prompt_sections.append(f"""CHANGES SUMMARY:
{changes_summary}""")
        
        # Type guidance
        primary_type = self._determine_primary_type(changes)
        prompt_sections.append(f"""RECOMMENDED TYPE: {primary_type}
{self._get_type_rationale(primary_type, changes)}""")
        
        # Final instruction
        prompt_sections.append("COMMIT MESSAGE:")
        
        return "\n\n".join(prompt_sections)
    
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
        """Create a brief summary of changes with context."""
        if not changes:
            return "No changes detected"
        
        summary_lines = []
        deleted_files = []
        added_files = []
        modified_files = []
        
        # Categorize changes
        for change in changes:
            if change.change_type == 'D':
                deleted_files.append(change.file_path)
            elif change.change_type == 'A':
                added_files.append(change.file_path)
            elif change.change_type == 'M':
                modified_files.append(change.file_path)
        
        # Analyze patterns to provide context
        context_hints = []
        
        # Detect migrations/rewrites
        if deleted_files and added_files:
            bash_files = [f for f in deleted_files if f.endswith('.sh') or 'setup' in f]
            python_dirs = [f for f in added_files if 'smart_commit' in f or f.endswith('.py')]
            if bash_files and python_dirs:
                context_hints.append("🔄 MIGRATION: Bash to Python implementation")
        
        # Detect deprecation
        if any('deprecated' in f for f in added_files):
            context_hints.append("📁 DEPRECATION: Moving old files to deprecated folder")
        
        # Build summary with context
        if context_hints:
            summary_lines.extend([f"## Context: {hint}" for hint in context_hints])
            summary_lines.append("")
        
        # List changes by type
        for change in changes[:5]:  # Limit to first 5 files
            action = {
                'M': 'Modified',
                'A': 'Added', 
                'D': 'Deleted',
                'R': 'Renamed',
                'C': 'Copied'
            }.get(change.change_type, 'Changed')
            
            # Add more context for specific file types
            if change.change_type == 'D' and (change.file_path.endswith('.sh') or 'setup' == change.file_path):
                summary_lines.append(f"- {action}: {change.file_path} (old bash implementation)")
            elif change.change_type == 'A' and 'deprecated' in change.file_path:
                summary_lines.append(f"- {action}: {change.file_path} (archival directory)")
            elif change.change_type == 'M' and 'repository.py' in change.file_path:
                summary_lines.append(f"- {action}: {change.file_path} (git operations enhancement)")
            else:
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
    
    # New sophisticated analysis methods based on 2025 best practices
    
    def _analyze_file_context(self, file_context: FileChange) -> str:
        """Comprehensive analysis of file context for better AI understanding."""
        file_path = file_context.file_path
        change_type = file_context.change_type
        
        analysis_parts = []
        
        # File type analysis
        file_type = self._determine_file_type(file_path)
        analysis_parts.append(f"File Type: {file_type}")
        
        # Project structure analysis  
        scope = self._analyze_scope(file_path)
        if scope:
            analysis_parts.append(f"Scope: {scope}")
        
        # Pattern detection
        patterns = self._detect_patterns(file_context)
        if patterns:
            analysis_parts.append(f"Detected Patterns: {', '.join(patterns)}")
        
        # Purpose analysis
        purpose = self._analyze_file_purpose(file_context)
        if purpose:
            analysis_parts.append(f"Purpose: {purpose}")
        
        return "\n".join(analysis_parts)
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine the type of file based on extension and path."""
        if file_path.endswith('.py'):
            return "Python source code"
        elif file_path.endswith('.sh'):
            return "Shell script"
        elif file_path.endswith('.md'):
            return "Documentation"
        elif file_path.endswith(('.yml', '.yaml')):
            return "Configuration"
        elif file_path.endswith('.json'):
            return "Data/Configuration"
        elif 'test' in file_path.lower():
            return "Test file"
        elif file_path == 'setup':
            return "Setup/Installation script"
        elif '/' not in file_path:
            return "Root configuration file"
        else:
            return "Source code"
    
    def _analyze_scope(self, file_path: str) -> Optional[str]:
        """Analyze conventional commit scope from file path."""
        parts = file_path.split('/')
        if len(parts) > 1:
            # Use the most relevant part for scope
            if parts[0] in ['src', 'lib', 'core', 'smart_commit']:
                return parts[0]
            elif parts[0] in ['test', 'tests']:
                return 'test'
            elif parts[0] in ['docs', 'doc']:
                return 'docs'
            elif parts[0] in ['config', 'configs']:
                return 'config'
            else:
                return parts[0]
        return None
    
    def _detect_patterns(self, file_context: FileChange) -> List[str]:
        """Detect common patterns in file changes."""
        patterns = []
        file_path = file_context.file_path
        change_type = file_context.change_type
        
        # Migration patterns
        if change_type == 'D' and (file_path.endswith('.sh') or file_path == 'setup'):
            patterns.append("bash-to-python-migration")
        
        if 'deprecated' in file_path:
            patterns.append("deprecation")
        
        # Maintenance patterns
        if change_type == 'M' and any(word in file_path for word in ['fix', 'repair', 'bug']):
            patterns.append("bug-fix")
        
        # Feature patterns
        if change_type == 'A' and file_path.endswith('.py'):
            patterns.append("new-feature")
        
        # Refactor patterns
        if change_type == 'M' and any(word in file_path for word in ['refactor', 'improve', 'enhance']):
            patterns.append("refactoring")
        
        return patterns
    
    def _analyze_file_purpose(self, file_context: FileChange) -> Optional[str]:
        """Analyze the purpose of the file change."""
        file_path = file_context.file_path
        change_type = file_context.change_type
        
        # Specific file analysis
        if file_path == 'setup' and change_type == 'D':
            return "Removing old bash setup script as part of Python migration"
        elif file_path == 'smart-commit.sh' and change_type == 'D':
            return "Removing old bash implementation after Python rewrite"
        elif 'repository.py' in file_path and change_type == 'M':
            return "Improving git operations handling"
        elif 'prompts.py' in file_path and change_type == 'M':
            return "Enhancing AI prompt generation"
        elif 'deprecated' in file_path and change_type == 'A':
            return "Creating archive for deprecated files"
        
        return None
    
    def _get_change_description(self, change_type: str) -> str:
        """Get human-readable description of change type."""
        descriptions = {
            'A': "New file added",
            'D': "File deleted", 
            'M': "File modified",
            'R': "File renamed",
            'C': "File copied"
        }
        return descriptions.get(change_type, "File changed")
    
    def _build_deletion_context(self, file_context: FileChange) -> str:
        """Build rich context for deleted files."""
        file_path = file_context.file_path
        
        context_parts = []
        context_parts.append("DELETION CONTEXT:")
        
        # Specific guidance for known files
        if file_path == 'setup':
            context_parts.append("- This was a bash setup script for configuring the tool")
            context_parts.append("- Part of migration from bash to Python implementation")
            context_parts.append("- Recommended type: chore")
            context_parts.append("- Example: chore: remove deprecated bash setup script")
        elif file_path == 'smart-commit.sh':
            context_parts.append("- This was the main bash implementation of smart-commit")
            context_parts.append("- Being replaced by Python implementation")
            context_parts.append("- Recommended type: chore")
            context_parts.append("- Example: chore: remove legacy bash implementation")
        elif file_path.endswith('.sh'):
            context_parts.append("- This was a shell script")
            context_parts.append("- Likely part of migration to Python")
            context_parts.append("- Recommended type: chore")
        else:
            context_parts.append("- File removal as part of codebase cleanup")
            context_parts.append("- Consider if this is part of a larger refactoring")
        
        return "\n".join(context_parts)
    
    def _build_addition_context(self, file_context: FileChange) -> str:
        """Build rich context for added files."""
        file_path = file_context.file_path
        
        context_parts = []
        context_parts.append("ADDITION CONTEXT:")
        
        if 'deprecated' in file_path:
            context_parts.append("- Creating archive directory for old files")
            context_parts.append("- Recommended type: chore or refactor")
        elif file_path.endswith('.py'):
            context_parts.append("- New Python module/script")
            context_parts.append("- Recommended type: feat (if new feature) or chore (if tooling)")
        elif 'test' in file_path:
            context_parts.append("- New test file")
            context_parts.append("- Recommended type: test")
        
        # Show truncated content if available
        if file_context.diff_content:
            content_preview = self._truncate_diff(file_context.diff_content, 50)
            context_parts.append(f"\nFILE CONTENT PREVIEW:\n```\n{content_preview}\n```")
        
        return "\n".join(context_parts)
    
    def _get_intelligent_diff(self, file_context: FileChange) -> str:
        """Get intelligently truncated diff content."""
        if not file_context.diff_content:
            return "No diff content available"
        
        # For modifications, focus on the most important changes
        lines = file_context.diff_content.split('\n')
        
        # Prioritize added/removed lines
        important_lines = []
        context_lines = []
        
        for line in lines:
            if line.startswith(('+', '-')):
                important_lines.append(line)
            else:
                context_lines.append(line)
        
        # Build intelligent diff
        result_lines = []
        
        # Add some context
        result_lines.extend(context_lines[:5])
        
        # Add important changes
        result_lines.extend(important_lines[:20])
        
        # Add truncation notice if needed
        total_lines = len(lines)
        shown_lines = len(result_lines)
        if shown_lines < total_lines:
            result_lines.append(f"... [showing {shown_lines} of {total_lines} lines]")
        
        return '\n'.join(result_lines)
    
    def _build_type_guidance(self, file_context: FileChange) -> str:
        """Build specific type guidance based on the change."""
        file_path = file_context.file_path
        change_type = file_context.change_type
        
        guidance_parts = []
        guidance_parts.append("TYPE GUIDANCE:")
        
        # Specific recommendations
        if change_type == 'D':
            if file_path.endswith('.sh') or file_path == 'setup':
                guidance_parts.append("RECOMMENDED: chore (removing deprecated bash files)")
            else:
                guidance_parts.append("RECOMMENDED: chore or refactor (cleanup)")
        elif change_type == 'A':
            if 'test' in file_path:
                guidance_parts.append("RECOMMENDED: test (adding tests)")
            elif 'deprecated' in file_path:
                guidance_parts.append("RECOMMENDED: chore (organizing files)")
            else:
                guidance_parts.append("RECOMMENDED: feat (new functionality) or chore (tooling)")
        elif change_type == 'M':
            if 'fix' in file_path.lower() or 'bug' in file_path.lower():
                guidance_parts.append("RECOMMENDED: fix (bug fixes)")
            else:
                guidance_parts.append("RECOMMENDED: feat (new features), fix (bugs), or refactor (improvements)")
        
        # Add type definitions
        guidance_parts.append("\nTYPE DEFINITIONS:")
        guidance_parts.append("- feat: new feature")
        guidance_parts.append("- fix: bug fix") 
        guidance_parts.append("- chore: maintenance, no production code change")
        guidance_parts.append("- refactor: code improvement without changing behavior")
        guidance_parts.append("- docs: documentation changes")
        guidance_parts.append("- test: adding/updating tests")
        
        return "\n".join(guidance_parts)
    
    def _analyze_change_pattern(self, changes: List[FileChange]) -> str:
        """Analyze the overall pattern of changes."""
        if not changes:
            return "No changes detected"
        
        # Count change types
        deletions = sum(1 for c in changes if c.change_type == 'D')
        additions = sum(1 for c in changes if c.change_type == 'A') 
        modifications = sum(1 for c in changes if c.change_type == 'M')
        
        pattern_parts = []
        pattern_parts.append(f"Total files: {len(changes)}")
        pattern_parts.append(f"Deletions: {deletions}, Additions: {additions}, Modifications: {modifications}")
        
        # Detect patterns
        patterns = []
        if deletions > 0 and any(c.file_path.endswith('.sh') for c in changes if c.change_type == 'D'):
            patterns.append("bash-to-python-migration")
        if any('deprecated' in c.file_path for c in changes):
            patterns.append("file-organization")
        if modifications > deletions + additions:
            patterns.append("enhancement/improvement")
        
        if patterns:
            pattern_parts.append(f"Detected patterns: {', '.join(patterns)}")
        
        return "\n".join(pattern_parts)
    
    def _build_intelligent_changes_summary(self, changes: List[FileChange]) -> str:
        """Build an intelligent summary of all changes."""
        if not changes:
            return "No changes"
        
        summary_parts = []
        
        # Group by change type
        deletions = [c for c in changes if c.change_type == 'D']
        additions = [c for c in changes if c.change_type == 'A']
        modifications = [c for c in changes if c.change_type == 'M']
        
        if deletions:
            summary_parts.append(f"DELETED ({len(deletions)}):")
            for d in deletions:
                purpose = self._analyze_file_purpose(d)
                if purpose:
                    summary_parts.append(f"  - {d.file_path} ({purpose})")
                else:
                    summary_parts.append(f"  - {d.file_path}")
        
        if additions:
            summary_parts.append(f"ADDED ({len(additions)}):")
            for a in additions:
                purpose = self._analyze_file_purpose(a)
                if purpose:
                    summary_parts.append(f"  - {a.file_path} ({purpose})")
                else:
                    summary_parts.append(f"  - {a.file_path}")
        
        if modifications:
            summary_parts.append(f"MODIFIED ({len(modifications)}):")
            for m in modifications:
                purpose = self._analyze_file_purpose(m)
                if purpose:
                    summary_parts.append(f"  - {m.file_path} ({purpose})")
                else:
                    summary_parts.append(f"  - {m.file_path}")
        
        return "\n".join(summary_parts)
    
    def _determine_primary_type(self, changes: List[FileChange]) -> str:
        """Determine the primary commit type for multiple changes."""
        # Analyze patterns to determine primary type
        deletions = [c for c in changes if c.change_type == 'D']
        additions = [c for c in changes if c.change_type == 'A']
        modifications = [c for c in changes if c.change_type == 'M']
        
        # Migration pattern
        if deletions and any(c.file_path.endswith('.sh') for c in deletions):
            return "chore"
        
        # New feature pattern
        if additions and not deletions:
            return "feat"
        
        # Bug fix pattern
        if modifications and any('fix' in c.file_path.lower() for c in modifications):
            return "fix"
        
        # Mixed changes - default to refactor
        if modifications and (deletions or additions):
            return "refactor"
        
        # Default based on majority
        if len(modifications) > len(deletions) + len(additions):
            return "feat"
        elif len(deletions) > 0:
            return "chore"
        else:
            return "feat"
    
    def _get_type_rationale(self, commit_type: str, changes: List[FileChange]) -> str:
        """Get rationale for the recommended commit type."""
        rationales = {
            "chore": "Maintenance tasks, dependency updates, or cleanup without affecting production code",
            "feat": "New features or functionality added to the codebase", 
            "fix": "Bug fixes or corrections to existing functionality",
            "refactor": "Code improvements that don't change external behavior",
            "docs": "Documentation changes",
            "test": "Adding or updating tests"
        }
        
        base_rationale = rationales.get(commit_type, "General code changes")
        
        # Add specific rationale based on changes
        if commit_type == "chore" and any(c.file_path.endswith('.sh') for c in changes if c.change_type == 'D'):
            return f"{base_rationale}\nSpecific: Removing deprecated bash files during Python migration"
        
        return base_rationale