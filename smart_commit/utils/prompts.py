"""
Optimized AI prompt templates for Qwen2.5-Coder-7B-Instruct.
Based on 2025 best practices for code analysis and commit message generation.
"""

from typing import List, Dict, Optional
from ..git_ops.repository import FileChange, RepositoryState


class PromptBuilder:
    """Build optimized prompts for Qwen2.5-Coder with structured analysis."""
    
    def __init__(self, character_limit: int = 150, optimized_mode: bool = False, settings=None):
        """Initialize prompt builder with conventional commit standards."""
        self.character_limit = character_limit
        self.optimized_mode = optimized_mode
        self.settings = settings
    
    def build_commit_prompt(
        self, 
        repo_state: RepositoryState = None,
        recent_commits: List[Dict] = None,
        file_context: FileChange = None
    ) -> str:
        """Build commit message generation prompt optimized for Qwen2.5-Coder."""
        
        if file_context:
            return self._build_single_file_prompt(file_context)
        elif repo_state:
            return self._build_multi_file_prompt(repo_state)
        else:
            raise ValueError("Either file_context or repo_state must be provided")
    
    def _build_single_file_prompt(self, file_context: FileChange) -> str:
        """Build optimized single-file prompt with step-by-step analysis."""
        
        # Extract key information
        file_path = file_context.file_path
        change_type = file_context.change_type
        scope = self._extract_scope(file_path)
        diff_content = self._get_focused_diff(file_context.diff_content)
        
        # Use ChatML-style structure optimized for Qwen2.5-Coder
        prompt = f"""You are an expert developer who writes precise git commit messages by carefully analyzing code changes.

## CRITICAL INSTRUCTIONS
- Focus on WHAT functionality was added/changed/fixed
- Ignore generic changes like "updates" or "improvements"
- Be SPECIFIC about the technical change
- SCOPE: {scope}

## FILE ANALYSIS

### File: {file_path} ({self._get_change_description(change_type)})

{self._get_diff_analysis_for_prompt(diff_content, file_path)}

## STEP-BY-STEP ANALYSIS (Required)

1. **What was added**: What new code/functionality was added?
2. **What was removed**: What old code was removed/changed?
3. **Technical Purpose**: What specific problem does this solve?
4. **Functional Impact**: What can the software do now that it couldn't before?

## FEW-SHOT EXAMPLES

### Example 1: Installation Logic
**Commit**: `feat(install): add intelligent PATH insertion logic`

### Example 2: API Enhancement
**Commit**: `feat(ai): add retry logic for API calls`

### Example 3: Configuration Update
**Commit**: `feat(config): add file size truncation threshold`

## YOUR TASK
Analyze the changes above and generate a conventional commit message.
**Format**: type(scope): description
**Scope**: {scope}
**Max Length**: {self.character_limit} characters

## SPECIAL CASES TO RECOGNIZE
- **Version updates**: If you see "v2.0" → "v2.0.1", use `docs(docs):` and mention "bump to v2.0.1 with [improvements]"
- **README updates**: If modifying README.md, use `docs(docs):` scope and be specific about what was updated
- **Documentation**: If adding new sections/notes, use `feat(docs):` for new content, `docs(docs):` for updates
- **IMPORTANT**: ALWAYS use parentheses around scope: `type(scope):` format
- **File deletions**: ALWAYS use `refactor:` for deletions. ALWAYS include space after colon. ALWAYS be specific about what's being removed.

## EXAMPLES FOR COMMON CHANGES

**Version Updates**:
✅ `docs(docs): bump version to v2.0.1 with validation improvements`
❌ `fix(docs): update v2`

**Documentation Changes**:
✅ `feat(docs): add troubleshooting guide for validation issues`
✅ `docs(docs): add comprehensive development guide`
❌ `docs: update documentation`

**New Features**:
✅ `feat(ai): add flexible regex validation for commit messages`
✅ `feat(install): add intelligent PATH insertion logic`
❌ `feat(ai): improve validation`

**Bug Fixes**:
✅ `fix(utils): remove unnecessary PromptBuilder initialization`
✅ `fix(git): resolve diff content extraction issues`
❌ `fix(core): fix bugs`

**File Deletions/Cleanup**:
✅ `refactor(claude): remove deprecated installer scripts and documentation`
✅ `refactor(utils): clean up unused configuration files`
❌ `fix(claude): remove unused files`
❌ `chore(claude): remove installer`



## STRICT ENFORCEMENT RULES
- **For deletions**: ONLY use `refactor:` type, NEVER use `fix:` or `chore:`
- **Spacing**: ALWAYS include space after colon: `type(scope): description`
- **Consistency**: Use similar descriptions for similar file types
- **Specificity**: Always mention what type of file/content is being removed





## CRITICAL FORMAT REQUIREMENTS
You MUST respond with ONLY the commit message in this exact format:
type(scope): description

**CORRECT FORMAT EXAMPLES:**
- `feat(install-apps): add new installation script`
- `fix(claude): resolve authentication issue`
- `refactor(bnet-linux): simplify configuration logic`

**WRONG FORMATS (DO NOT USE):**
- ❌ `Type: feat Scope: install-apps Description: add new script`
- ❌ `feat: add new script`
- ❌ `feat(install-apps) - add new script`
- ❌ `feat(install-apps) add new script`

**RESPOND WITH ONLY:** type(scope): description

"""

        # Log the final prompt for debugging
        from loguru import logger
        logger.info(f"📝 FINAL PROMPT FOR {file_path}:")
        logger.info(f"📊 Prompt length: {len(prompt)} characters")
        logger.info(f"🔍 Scope used: {scope}")
        logger.info(f"📋 Diff analysis method: {self._get_diff_analysis_for_prompt.__name__}")
        
        return prompt
    
    def _build_multi_file_prompt(self, repo_state: RepositoryState) -> str:
        """Build optimized multi-file prompt for repository-wide changes."""
        
        changes = repo_state.all_changes
        if not changes:
            return "No changes detected"
        
        # Analyze change patterns
        change_summary = self._analyze_changes(changes)
        primary_scope = self._determine_primary_scope(changes)
        primary_type = self._determine_primary_type(changes)
        
        # Build focused analysis of actual changes
        detailed_changes = self._get_detailed_changes_analysis(changes)
        
        prompt = f"""You are an expert developer analyzing multiple code changes to generate ONE precise conventional commit message.

## CRITICAL INSTRUCTIONS
- Analyze the actual code changes, not just file names
- Find the COMMON PURPOSE across all changes
- Be SPECIFIC about what functionality was added/changed/fixed
- Avoid generic descriptions
- SCOPE: {primary_scope}

## REPOSITORY CHANGES ANALYSIS

### Change Summary: {change_summary}

### Detailed Technical Changes:
{detailed_changes}

## STEP-BY-STEP ANALYSIS (Required)

1. **Common Theme**: What is the shared purpose across these changes?
2. **Primary Impact**: What new capability or fix is being delivered?
3. **Technical Category**: Is this a feature, fix, refactor, or maintenance?

## FEW-SHOT EXAMPLES

### Example 1: Installation Enhancement
**Files**: install.py (modified), core.py (modified)
**Changes**: Added PATH override detection + fixed method signature error
**Correct**: `fix(install): enhance PATH configuration to handle shell overrides`
**Wrong**: `fix(install): update installation system`

### Example 2: AI System Improvement  
**Files**: prompts.py (rewritten), ai_backends/base.py (modified)
**Changes**: Complete prompt rewrite + backend interface update
**Correct**: `refactor(ai): redesign prompt system for better accuracy`
**Wrong**: `refactor(ai): improve AI functionality`

### Example 3: Core Architecture Fix
**Files**: core.py (method added), utils/extractor.py (modified)  
**Changes**: Added missing method + updated extraction logic
**Correct**: `fix(core): add missing traditional commit message generation`
**Wrong**: `fix(core): improve core functionality`

## COMMIT MESSAGE RULES

**Format**: `type({primary_scope}): description`
**Max Length**: {self.character_limit} characters

**Suggested Type**: {primary_type}
**Suggested Scope**: {primary_scope}

**Description Must Be**:
- SPECIFIC about the main technical change
- Focused on the PRIMARY purpose (not listing all changes)
- Imperative mood
- NO generic words unless very specific about what was updated/improved

## TYPE SELECTION
- `feat`: NEW functionality/capability added
- `fix`: BUG corrected or missing functionality added  
- `refactor`: Code restructured without changing behavior
- `chore`: Maintenance, cleanup, dependencies

## YOUR ANALYSIS AND RESPONSE

Analyze the changes above and generate ONLY the commit message:"""

        return prompt
    
    def _extract_scope(self, file_path: str) -> str:
        """Extract conventional commit scope from file path."""
        parts = file_path.split('/')
        
        # Root level files
        if len(parts) == 1:
            scope_map = {
                'install.py': 'install',
                'pyproject.toml': 'build',
                'README.md': 'docs',
                'CLAUDE.md': 'docs',
                'LICENSE': 'docs'
            }
            return scope_map.get(file_path, 'root')
        
        # smart_commit directory structure
        if parts[0] == 'smart_commit':
            if len(parts) == 2:
                # Direct files in smart_commit/
                file_scope_map = {
                    'cli.py': 'core',
                    'core.py': 'core',
                    '__init__.py': 'core'
                }
                return file_scope_map.get(parts[1], 'core')
            elif len(parts) > 2:
                # Subdirectories
                subdir_scope_map = {
                    'ai_backends': 'ai',
                    'git_ops': 'git',
                    'ui': 'ui',
                    'utils': 'utils',
                    'config': 'config'
                }
                return subdir_scope_map.get(parts[1], parts[1])
        
        # Other directories
        if len(parts) >= 2:
            primary_scope = parts[0]
            
            # Special handling for specific directory patterns
            if primary_scope == 'install-apps':
                # Always use install-apps scope for files in this directory
                return 'install-apps'
            elif primary_scope == 'bnet-linux':
                # Always use bnet-linux scope for files in this directory
                return 'bnet-linux'
            elif primary_scope == 'claude':
                # Always use claude scope for files in this directory
                return 'claude'
            
            # Default behavior for other directories
            return primary_scope
        
        # Fallback
        return parts[0] if parts else 'root'
    
    def _analyze_scope(self, file_path: str) -> str:
        """Alias for _extract_scope for backward compatibility."""
        return self._extract_scope(file_path)
    
    def _get_focused_diff(self, diff_content: str, max_lines: int = None) -> str:
        """Get the most important parts of the diff for analysis."""
        if not diff_content:
            return "No diff content available"
        
        # Use configured default if not specified
        if max_lines is None:
            max_lines = self.settings.git.max_diff_lines if self.settings else 500
        
        lines = diff_content.split('\n')
        
        # If diff is manageable, use existing logic
        if len(lines) <= max_lines:
            return self._get_focused_diff_small(lines, max_lines)
        
        # Smart truncation for large diffs
        return self._smart_truncate_large_diff(lines, max_lines)
    
    def _get_focused_diff_small(self, lines: list, max_lines: int) -> str:
        """Original focused diff logic for small files."""
        # Prioritize important lines
        important_lines = []
        context_lines = []
        
        for line in lines:
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                # Only include substantive changes, not just whitespace
                if line.strip() not in ['+', '-'] and len(line.strip()) > 3:
                    important_lines.append(line)
            elif line.startswith('@@'):
                context_lines.append(line)
        
        # Build focused diff
        result = []
        
        # Add some context headers
        for line in context_lines[:3]:
            result.append(line)
        
        # Add the most important changes
        for line in important_lines[:max_lines]:
            result.append(line)
        
        # Add truncation notice if needed
        if len(important_lines) > max_lines:
            result.append(f"... [showing {max_lines} of {len(important_lines)} change lines]")
        
        return '\n'.join(result)
    
    def _smart_truncate_large_diff(self, lines: list, max_lines: int = 500) -> str:
        """Smart truncation for large diffs that preserves important changes."""
        
        # For very large diffs, use intelligent analysis instead of raw truncation
        if len(lines) > 800:  # Threshold for very large diffs
            return self._analyze_large_diff_significance('\n'.join(lines))
        
        # Always include file headers
        header_lines = [line for line in lines if line.startswith(('---', '+++'))]
        
        # Include diff context markers (hunk headers)
        context_lines = [line for line in lines if line.startswith('@@')]
        
        # Prioritize actual code changes (additions/deletions)
        change_lines = []
        for line in lines:
            if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                # Only include substantive changes, not just whitespace
                if line.strip() not in ['+', '-'] and len(line.strip()) > 3:
                    change_lines.append(line)
        
        # Include function/class context for better AI understanding
        context_lines_with_code = []
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ['def ', 'class ', 'function ', 'export ', 'import ', 'async def ']):
                # Include a few lines before and after for context
                start = max(0, i-2)
                end = min(len(lines), i+3)
                context_lines_with_code.extend(lines[start:end])
        
        # Calculate how many lines to allocate to each category
        total_original = len(lines)
        change_limit = max_lines // 2  # 50% for actual changes
        context_limit = max_lines // 4  # 25% for context
        header_limit = max_lines // 4  # 25% for headers and context markers
        
        # Build truncated diff
        result = []
        
        # Add file headers
        result.extend(header_lines[:header_limit])
        
        # Add diff context markers
        result.extend(context_lines[:header_limit])
        
        # Add the most important changes
        result.extend(change_lines[:change_limit])
        
        # Add function/class context
        result.extend(context_lines_with_code[:context_limit])
        
        # Add truncation notice
        if total_original > max_lines:
            result.append(f"\n... [showing {len(result)} of {total_original} lines]")
            result.append(f"... [truncated for performance - file has {len(change_lines)} actual changes]")
            result.append(f"... [focusing on most significant changes for AI analysis]")
        
        return '\n'.join(result)
    
    def _analyze_large_diff_significance(self, diff_content: str) -> str:
        """Analyze large diffs to extract only the most significant changes."""
        if not diff_content:
            return "No diff content available"
        
        lines = diff_content.split('\n')
        
        # For very large diffs, focus on structural changes
        if len(lines) > 200:
            return self._extract_structural_changes(lines)
        
        # For medium diffs, use focused analysis
        return self._extract_key_changes(lines)
    
    def _extract_structural_changes(self, lines: list) -> str:
        """Extract structural changes from very large diffs."""
        structural_changes = []
        
        # Look for class/method definitions, imports, and major structural elements
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Class definitions
            if line.startswith('+class ') or line.startswith('-class '):
                structural_changes.append(f"Class change: {line[1:].split('(')[0].split(':')[0].strip()}")
            
            # Method definitions
            elif line.startswith('+    def ') or line.startswith('-    def '):
                method_name = line[1:].split('(')[0].split('def ')[1].strip()
                structural_changes.append(f"Method change: {method_name}")
            
            # Import statements
            elif line.startswith('+from ') or line.startswith('-from ') or line.startswith('+import ') or line.startswith('-import '):
                structural_changes.append(f"Import change: {line[1:].strip()}")
            
            # Major comment blocks
            elif line.startswith('+"""') or line.startswith('-"""'):
                if i + 1 < len(lines) and '"""' in lines[i + 1]:
                    structural_changes.append("Docstring change")
        
        if structural_changes:
            return "Major structural changes detected:\n" + "\n".join(structural_changes[:10])  # Limit to 10 changes
        else:
            return "Large refactoring with many line changes"
    
    def _extract_key_changes(self, lines: list) -> str:
        """Extract key changes from medium-sized diffs."""
        key_changes = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('+') and ('def ' in line or 'class ' in line or 'import ' in line or 'from ' in line):
                key_changes.append(f"Added: {line[1:].strip()}")
            elif line.startswith('-') and ('def ' in line or 'class ' in line or 'import ' in line or 'from ' in line):
                key_changes.append(f"Removed: {line[1:].strip()}")
        
        if key_changes:
            return "Key changes:\n" + "\n".join(key_changes[:5])  # Limit to 5 changes
        else:
            return "General code modifications"
    
    def _get_diff_analysis_for_prompt(self, diff_content: str, file_path: str) -> str:
        """Get intelligent diff analysis for the prompt instead of raw diff content."""
        from loguru import logger
        
        logger.info(f"🔍 ANALYZING DIFF FOR: {file_path}")
        logger.info(f"📊 Raw diff content length: {len(diff_content)} characters")
        
        if not diff_content:
            logger.warning(f"❌ No diff content available for {file_path}")
            return "No diff content available"
        
        lines = diff_content.split('\n')
        logger.info(f"📈 Diff has {len(lines)} lines")
        
        # For extremely large diffs, provide a high-level summary
        if len(lines) > 1000:
            logger.info(f"🚨 EXTREMELY LARGE DIFF DETECTED: {len(lines)} lines - using summary analysis")
            result = self._get_extremely_large_diff_summary(lines, file_path)
            logger.info(f"📝 Generated summary for extremely large diff: {len(result)} characters")
            return result
        
        # For large diffs, provide structural analysis
        elif len(lines) > 500:
            logger.info(f"⚠️ LARGE DIFF DETECTED: {len(lines)} lines - using structural analysis")
            result = self._get_large_diff_summary(lines, file_path)
            logger.info(f"📝 Generated summary for large diff: {len(result)} characters")
            return result
        
        # For normal diffs, provide focused content
        else:
            logger.info(f"✅ NORMAL DIFF: {len(lines)} lines - using raw content")
            result = self._get_normal_diff_content(diff_content)
            logger.info(f"📝 Using normal diff content: {len(result)} characters")
            return result
    
    def _get_extremely_large_diff_summary(self, lines: list, file_path: str) -> str:
        """Provide a high-level summary for extremely large diffs."""
        from loguru import logger
        
        logger.info(f"🔍 Generating extremely large diff summary for {file_path}")
        
        # Count changes
        additions = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
        deletions = [line for line in lines if line.startswith('-') and not line.startswith('---')]
        
        logger.info(f"📊 Counted {len(additions)} additions and {len(deletions)} deletions")
        
        # Look for major structural indicators
        structural_changes = []
        for line in lines:
            line = line.strip()
            if line.startswith('+class ') or line.startswith('-class '):
                structural_changes.append("Class structure changes")
            elif line.startswith('+    def ') or line.startswith('-    def '):
                structural_changes.append("Method signature changes")
            elif line.startswith('+from ') or line.startswith('-from ') or line.startswith('+import ') or line.startswith('-import '):
                structural_changes.append("Import/dependency changes")
        
        logger.info(f"🏗️ Detected structural changes: {list(set(structural_changes))}")
        
        summary = f"**EXTREMELY LARGE REFACTORING DETECTED**\n\n"
        summary += f"File: {file_path}\n"
        summary += f"Total lines changed: {len(lines)}\n"
        summary += f"Additions: {len(additions)} lines\n"
        summary += f"Deletions: {len(deletions)} lines\n\n"
        
        if structural_changes:
            summary += "**Major Changes Detected:**\n"
            summary += "\n".join(set(structural_changes)) + "\n\n"
        
        summary += "**Analysis Required:**\n"
        summary += "This is a massive refactoring. Focus on the overall purpose and impact rather than individual line changes.\n"
        summary += "What was the main goal of this refactoring? What architectural improvements were made?"
        
        logger.info(f"📝 Generated extremely large diff summary: {len(summary)} characters")
        logger.info(f"📋 Summary preview: {summary[:200]}...")
        
        return summary
    
    def _get_large_diff_summary(self, lines: list, file_path: str) -> str:
        """Provide a summary for large diffs."""
        # Count changes
        additions = [line for line in lines if line.startswith('+') and not line.startswith('+++')]
        deletions = [line for line in lines if line.startswith('-') and not line.startswith('---')]
        
        # Extract key structural changes
        key_changes = []
        for line in lines:
            line = line.strip()
            if line.startswith('+') and ('def ' in line or 'class ' in line):
                key_changes.append(f"Added: {line[1:].strip()}")
            elif line.startswith('-') and ('def ' in line or 'class ' in line):
                key_changes.append(f"Removed: {line[1:].strip()}")
        
        summary = f"**LARGE REFACTORING DETECTED**\n\n"
        summary += f"File: {file_path}\n"
        summary += f"Total lines: {len(lines)}\n"
        summary += f"Additions: {len(additions)} lines\n"
        summary += f"Deletions: {len(deletions)} lines\n\n"
        
        if key_changes:
            summary += "**Key Structural Changes:**\n"
            summary += "\n".join(key_changes[:8]) + "\n"  # Limit to 8 changes
            if len(key_changes) > 8:
                summary += f"... and {len(key_changes) - 8} more changes\n"
        
        summary += "\n**Focus:** Analyze the overall purpose and architectural improvements of this refactoring."
        
        return summary
    
    def _get_normal_diff_content(self, diff_content: str) -> str:
        """Provide normal diff content for small files."""
        return f"```diff\n{diff_content}\n```"
    
    def _get_detailed_changes_analysis(self, changes: List[FileChange], max_files: int = 3) -> str:
        """Get detailed technical analysis of what actually changed in the code."""
        result = []
        
        for i, change in enumerate(changes[:max_files]):
            change_desc = self._get_change_description(change.change_type)
            
            # Get focused diff for this file
            key_diff = self._get_focused_diff(change.diff_content, max_lines=15)
            
            # Analyze what actually changed technically
            technical_summary = self._analyze_technical_change(change)
            
            result.append(f"""**{change.file_path}** ({change_desc}):
{technical_summary}
```diff
{key_diff}
```""")
        
        if len(changes) > max_files:
            result.append(f"\n... and {len(changes) - max_files} more files with related changes")
        
        return '\n\n'.join(result)
    
    def _analyze_technical_change(self, change: FileChange) -> str:
        """Analyze what technically changed in a file based on diff content."""
        if not change.diff_content:
            return "No diff content available"
        
        lines = change.diff_content.split('\n')
        added_functionality = []
        removed_functionality = []
        
        # Look for significant additions
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                line_content = line[1:].strip()
                if len(line_content) > 5:  # Skip trivial additions
                    # Look for function definitions, class additions, etc.
                    if line_content.startswith(('def ', 'class ', 'async def ')):
                        func_name = line_content.split('(')[0].replace('def ', '').replace('class ', '').replace('async ', '')
                        added_functionality.append(f"Added method/class: {func_name}")
                    elif 'if ' in line_content and ('export PATH' in line_content or 'path_override' in line_content):
                        added_functionality.append("Added PATH override detection logic")
                    elif 'insertion_point' in line_content or 'smart_path_insertion' in line_content:
                        added_functionality.append("Added intelligent PATH insertion logic")
                    elif 'few-shot' in line_content.lower() or 'examples' in line_content.lower():
                        added_functionality.append("Added few-shot examples to prompts")
                    elif 'await self._generate_traditional' in line_content:
                        added_functionality.append("Added traditional commit message generation call")
        
        # Look for significant removals
        for line in lines:
            if line.startswith('-') and not line.startswith('---'):
                line_content = line[1:].strip()
                if len(line_content) > 5:
                    if 'await self._generate_commit_message(repo_state)' in line_content:
                        removed_functionality.append("Removed incorrect method call")
                    elif line_content.startswith(('def ', 'class ')):
                        func_name = line_content.split('(')[0].replace('def ', '').replace('class ', '')
                        removed_functionality.append(f"Removed method/class: {func_name}")
        
        # Build technical summary
        summary_parts = []
        if added_functionality:
            summary_parts.append(f"Added: {', '.join(added_functionality)}")
        if removed_functionality:
            summary_parts.append(f"Removed: {', '.join(removed_functionality)}")
        
        if not summary_parts:
            # Fallback to simpler analysis
            return f"Modified {change.file_path} with {change.lines_added} additions and {change.lines_removed} deletions"
        
        return '; '.join(summary_parts)
    
    def _get_change_description(self, change_type: str) -> str:
        """Get human-readable description of change type."""
        descriptions = {
            'A': "Added",
            'D': "Deleted", 
            'M': "Modified",
            'R': "Renamed",
            'C': "Copied"
        }
        return descriptions.get(change_type, "Changed")
    
    def _analyze_changes(self, changes: List[FileChange]) -> str:
        """Analyze changes to understand the overall pattern."""
        if not changes:
            return "No changes"
        
        # Count by type
        type_counts = {}
        for change in changes:
            type_counts[change.change_type] = type_counts.get(change.change_type, 0) + 1
        
        # Build summary
        summary_parts = [f"Total files: {len(changes)}"]
        
        for change_type, count in type_counts.items():
            desc = self._get_change_description(change_type)
            summary_parts.append(f"{desc}: {count}")
        
        # Detect patterns
        patterns = []
        if any(c.file_path.endswith('.sh') and c.change_type == 'D' for c in changes):
            patterns.append("bash-to-python migration")
        if any('deprecated' in c.file_path for c in changes):
            patterns.append("file organization")
        if type_counts.get('M', 0) > type_counts.get('A', 0) + type_counts.get('D', 0):
            patterns.append("enhancement/fixes")
        
        if patterns:
            summary_parts.append(f"Patterns: {', '.join(patterns)}")
        
        return ' | '.join(summary_parts)
    
    def _get_key_changes(self, changes: List[FileChange], max_files: int = 5) -> str:
        """Get key changes for multi-file analysis."""
        result = []
        
        for i, change in enumerate(changes[:max_files]):
            change_desc = self._get_change_description(change.change_type)
            
            # Get a brief description of what changed
            purpose = self._infer_change_purpose(change)
            if purpose:
                result.append(f"- {change_desc}: {change.file_path} ({purpose})")
            else:
                result.append(f"- {change_desc}: {change.file_path}")
        
        if len(changes) > max_files:
            result.append(f"- ... and {len(changes) - max_files} more files")
        
        return '\n'.join(result)
    
    def _infer_change_purpose(self, change: FileChange) -> Optional[str]:
        """Infer the purpose of a file change from context."""
        file_path = change.file_path
        change_type = change.change_type
        
        # File-specific inferences
        if 'install' in file_path and change_type == 'M':
            return "PATH configuration enhancement"
        elif 'core.py' in file_path and change_type == 'M':
            return "core functionality improvement"
        elif file_path.endswith('.sh') and change_type == 'D':
            return "legacy script removal"
        elif 'deprecated' in file_path and change_type == 'A':
            return "archival directory creation"
        elif 'test' in file_path:
            return "testing enhancement"
        elif 'ai_backends' in file_path:
            return "AI backend improvement"
        elif 'git_ops' in file_path:
            return "git operations enhancement"
        
        return None
    
    def _determine_primary_scope(self, changes: List[FileChange]) -> str:
        """Determine the primary scope for multi-file changes."""
        scope_counts = {}
        
        for change in changes:
            scope = self._extract_scope(change.file_path)
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
        
        # Return the most common scope
        if scope_counts:
            return max(scope_counts.items(), key=lambda x: x[1])[0]
        
        return "smart_commit"
    
    def _determine_primary_type(self, changes: List[FileChange]) -> str:
        """Determine the primary commit type for multi-file changes."""
        # Count change types
        deletions = sum(1 for c in changes if c.change_type == 'D')
        additions = sum(1 for c in changes if c.change_type == 'A')
        modifications = sum(1 for c in changes if c.change_type == 'M')
        
        # Pattern-based type detection
        if deletions > 0 and any(c.file_path.endswith('.sh') for c in changes if c.change_type == 'D'):
            return "chore"  # Cleanup/migration
        
        if modifications > deletions + additions:
            # Check if these look like fixes or features
            if any('fix' in c.file_path.lower() or 'error' in c.file_path.lower() for c in changes):
                return "fix"
            else:
                return "feat"  # Assume improvements are features
        
        if additions > 0 and deletions == 0:
            return "feat"  # Pure additions are likely features
        
        if deletions > additions:
            return "chore"  # More deletions suggest cleanup
        
        return "feat"  # Default to feature