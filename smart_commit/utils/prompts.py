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
        
        # Detect if this is a new file
        is_new_file = change_type == 'A' and diff_content.startswith('--- /dev/null')
        
        # Use completely separate prompts to eliminate confusion
        if is_new_file:
            return self._build_new_file_prompt_clean(file_path, scope, diff_content)
        else:
            return self._build_modified_file_prompt_clean(file_path, scope, diff_content, change_type)

    def _build_new_file_prompt_clean(self, file_path: str, scope: str, diff_content: str) -> str:
        """Build completely clean prompt for NEW files - no confusion possible."""
        
        prompt = f"""You are an expert developer analyzing a NEW FILE being added to the repository.

## CRITICAL: THIS IS A NEW FILE
- **File**: {file_path}
- **Status**: NEW FILE being added (NOT modified, NOT deleted)
- **Scope**: {scope}
- **Max Length**: {self.character_limit} characters

## FILE CONTENT ANALYSIS
{self._get_diff_analysis_for_prompt(diff_content, file_path)}

## YOUR TASK
Analyze this NEW file and generate a commit message describing what NEW functionality is being introduced.

## COMMIT TYPE RULES FOR NEW FILES
- **Use `feat:` for new scripts, tools, or functionality**
- **Use `docs:` for new documentation or README files**
- **Use `chore:` for new configuration files**
- **NEVER use `refactor:` for new files**
- **NEVER use `fix:` for new files**

## EXAMPLES FOR NEW FILES
✅ `feat({scope}): add new user management script`
✅ `docs({scope}): add comprehensive API documentation`
✅ `chore({scope}): add configuration file for deployment`

## FORMAT REQUIREMENTS
- **Format**: EXACTLY type({scope}): description
- **Required scope in parentheses**: ({scope})
- **Description**: MUST be a complete sentence describing what NEW capability is being introduced
- **NEVER end with prepositions**: Don't end with "for", "to", "with", etc.
- **Be specific**: Instead of "add script for", say "add script for converting file formats"

## RESPONSE RULES
1. Generate ONLY the commit message in this EXACT format: type({scope}): description
2. The description MUST be a complete, grammatically correct sentence
3. NEVER leave sentences incomplete or hanging with prepositions
4. Be specific about what NEW functionality you're adding

Example for this file: feat({scope}): add new user authentication system"""

        # Log the final prompt for debugging
        from loguru import logger
        logger.info(f"📝 NEW FILE PROMPT FOR {file_path}:")
        logger.info(f"📊 Prompt length: {len(prompt)} characters")
        logger.info(f"🔍 Scope used: {scope}")
        
        return prompt

    def _build_modified_file_prompt_clean(self, file_path: str, scope: str, diff_content: str, change_type: str) -> str:
        """Build completely clean prompt for MODIFIED files."""
        
        change_desc = self._get_change_description(change_type)
        
        prompt = f"""You are an expert developer analyzing a MODIFIED file in the repository.

## FILE ANALYSIS
- **File**: {file_path}
- **Status**: {change_desc}
- **Scope**: {scope}
- **Max Length**: {self.character_limit} characters

## CHANGES ANALYSIS
{self._get_diff_analysis_for_prompt(diff_content, file_path)}

## YOUR TASK
Analyze the changes to this existing file and generate a commit message describing what was modified.

## COMMIT TYPE RULES FOR MODIFICATIONS
- **Use `feat:` for new functionality added to existing files**
- **Use `fix:` for bug fixes or corrections**
- **Use `refactor:` for code restructuring without changing behavior**
- **Use `docs:` for documentation updates**
- **Use `chore:` for maintenance tasks**

## FORMAT REQUIREMENTS
- **Format**: EXACTLY type({scope}): description
- **Required scope in parentheses**: ({scope})
- **Description**: MUST be a complete sentence with specific details
- **NEVER end with prepositions**: Don't end with "for", "to", "with", etc.
- **Be specific**: Instead of "add error handling for", say "add error handling for missing .env file"

## RESPONSE RULES
1. Generate ONLY the commit message in this EXACT format: type({scope}): description
2. The description MUST be a complete, grammatically correct sentence
3. NEVER leave sentences incomplete or hanging with prepositions
4. Be specific about what you're changing, not just the action

Example for this file: docs({scope}): update file documentation with new sections"""

        # Log the final prompt for debugging
        from loguru import logger
        logger.info(f"📝 MODIFIED FILE PROMPT FOR {file_path}:")
        logger.info(f"📊 Prompt length: {len(prompt)} characters")
        logger.info(f"🔍 Scope used: {scope}")
        
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
                'README.md': 'root',      # Changed from 'docs' to avoid docs(docs):
                'CLAUDE.md': 'root',      # Changed from 'docs' to avoid docs(docs):
                'LICENSE': 'root'         # Changed from 'docs' to avoid docs(docs):
            }
            return scope_map.get(parts[0], 'root')
        
        # Use first directory as scope
        return parts[0]
    
    def _get_focused_diff(self, diff_content: str) -> str:
        """Get focused diff content for analysis."""
        if not diff_content:
            return ""
        
        # For now, return the full diff content
        # This could be enhanced to focus on key changes
        return diff_content
    
    def _get_diff_analysis_for_prompt(self, diff_content: str, file_path: str) -> str:
        """Get intelligent diff analysis for the prompt instead of raw diff content."""
        from loguru import logger
        
        logger.info(f"🔍 ANALYZING DIFF FOR: {file_path}")
        logger.info(f"📊 Raw diff content length: {len(diff_content)} characters")
        
        if not diff_content:
            logger.warning(f"❌ No diff content available for {file_path}")
            return "No diff content available"
        
        # Check if this is a new file
        is_new_file = diff_content.startswith('--- /dev/null')
        
        lines = diff_content.split('\n')
        logger.info(f"📈 Diff has {len(lines)} lines")
        
        # Special handling for new files
        if is_new_file:
            logger.info(f"🆕 NEW FILE DETECTED: {file_path} - using new file analysis")
            return self._get_new_file_analysis(diff_content, file_path)
        
        # For normal diffs, provide focused content
        logger.info(f"✅ NORMAL DIFF: {len(lines)} lines - using raw content")
        result = self._get_normal_diff_content(diff_content)
        logger.info(f"📝 Using normal diff content: {len(result)} characters")
        return result

    def _get_new_file_analysis(self, diff_content: str, file_path: str) -> str:
        """Provide intelligent analysis for new files."""
        lines = diff_content.split('\n')
        
        # Extract the actual content (skip the diff headers and metadata)
        content_lines = []
        metadata_lines = []
        
        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                content_lines.append(line[1:])  # Remove the + prefix
            elif line.startswith('+') and line.startswith('+++'):
                continue  # Skip diff headers
            elif line.startswith('+NEW FILE:') or line.startswith('+FILE TYPE:') or line.startswith('+PURPOSE:') or line.startswith('+CONTEXT:') or line.startswith('+CONTENT PREVIEW:'):
                metadata_lines.append(line[1:])  # Store metadata for context
        
        # Analyze the content to understand what type of file this is
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else ''
        content_preview = '\n'.join(content_lines[:20])  # First 20 lines for analysis
        
        # Determine file type and purpose
        file_type = self._classify_new_file_type(file_extension, content_preview)
        
        analysis = f"**NEW FILE ANALYSIS**\n\n"
        analysis += f"**File**: {file_path}\n"
        analysis += f"**Type**: {file_type['category']}\n"
        analysis += f"**Purpose**: {file_type['purpose']}\n\n"
        
        if metadata_lines:
            analysis += "**Context**:\n"
            for meta in metadata_lines:
                analysis += f"- {meta}\n"
            analysis += "\n"
        
        analysis += "**Content Preview**:\n"
        analysis += "```\n"
        analysis += content_preview
        if len(content_lines) > 20:
            analysis += f"\n... and {len(content_lines) - 20} more lines"
        analysis += "\n```\n\n"
        
        analysis += "**Analysis**: This is a completely new file being added to the repository. "
        analysis += f"Focus on what new functionality or content is being introduced. "
        analysis += f"Use '{file_type['commit_type']}' as the commit type since this is new content."
        
        return analysis

    def _classify_new_file_type(self, extension: str, content_preview: str) -> Dict[str, str]:
        """Classify the type of new file based on extension and content."""
        # Extension-based classification
        if extension in ['md', 'txt', 'rst', 'adoc']:
            base_type = 'documentation'
            commit_type = 'docs'
        elif extension in ['py', 'js', 'ts', 'rb', 'php', 'sh', 'bash']:
            base_type = 'script/code'
            commit_type = 'feat'
        elif extension in ['json', 'yaml', 'yml', 'toml', 'ini', 'cfg']:
            base_type = 'configuration'
            commit_type = 'chore'
        elif extension in ['csv', 'xml', 'sql', 'db']:
            base_type = 'data'
            commit_type = 'feat'
        else:
            base_type = 'file'
            commit_type = 'feat'
        
        # Content-based refinement
        content_lower = content_preview.lower()
        if 'readme' in content_lower or 'documentation' in content_lower:
            purpose = 'documentation or README'
        elif 'config' in content_lower or 'settings' in content_lower:
            purpose = 'configuration or settings'
        elif 'script' in content_lower or 'utility' in content_lower:
            purpose = 'script or utility'
        elif 'test' in content_lower or 'spec' in content_lower:
            purpose = 'test or specification'
        else:
            purpose = f'new {base_type}'
        
        return {
            'category': base_type,
            'purpose': purpose,
            'commit_type': commit_type
        }
    
    def _get_normal_diff_content(self, diff_content: str) -> str:
        """Get normal diff content for analysis."""
        return diff_content
    
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
        # Simplified implementation
        return f"Multiple file changes detected: {len(changes)} files"
    
    def _determine_primary_scope(self, changes: List[FileChange]) -> str:
        """Determine the primary scope from multiple changes."""
        # Simplified implementation
        if changes:
            return self._extract_scope(changes[0].file_path)
        return "root"
    
    def _determine_primary_type(self, changes: List[FileChange]) -> str:
        """Determine the primary change type from multiple changes."""
        # Simplified implementation
        return "feat"
    
    def _get_detailed_changes_analysis(self, changes: List[FileChange]) -> str:
        """Get detailed analysis of changes."""
        # Simplified implementation
        return f"Changes across {len(changes)} files"
    
    def build_branch_name_prompt(self, changes_summary: List[str]) -> str:
        """Build a prompt for generating branch names based on changes."""
        prompt = f"""You are an expert developer analyzing code changes to generate a descriptive Git branch name.

## CHANGES BEING MADE
{chr(10).join(changes_summary[:5])}

## YOUR TASK
Generate a concise, descriptive branch name that captures the overall purpose of these changes.

## BRANCH NAMING RULES
- Use format: type/description (e.g., feature/user-auth, fix/login-bug, chore/update-deps)
- Common types: feature, fix, chore, refactor, docs, test
- Description should be 2-4 words max, kebab-case
- Be specific but concise
- Focus on the main purpose/theme of the changes

## EXAMPLES
✅ feature/user-authentication
✅ fix/oauth-token-validation  
✅ chore/update-dependencies
✅ refactor/auth-module
✅ docs/api-documentation

## RESPONSE FORMAT
Return ONLY the branch name, nothing else. No explanations, no code blocks, just the branch name.

Example: feature/smart-commit-protection"""
        
        return prompt
    
    def build_intelligent_branch_name_prompt(self, changes_analysis: List[Dict]) -> str:
        """Build comprehensive prompt for intelligent branch name generation."""
        
        # Analyze the changes to extract key information
        file_count = len(changes_analysis)
        total_lines_added = sum(change.get('lines_added', 0) for change in changes_analysis)
        total_lines_removed = sum(change.get('lines_removed', 0) for change in changes_analysis)
        
        # Filter primary vs auxiliary files
        primary_changes = []
        auxiliary_files = []
        
        # Categorize files by type
        api_files = []
        cli_files = []
        doc_files = []
        config_files = []
        script_files = []
        test_files = []
        other_files = []
        
        for change in changes_analysis:
            path = change['file_path'].lower()
            
            # Separate auxiliary files
            if any(skip in path for skip in ['.md', 'readme', 'changelog', 'license', '.gitignore', 
                                           'docker', '.yml', '.yaml']):
                auxiliary_files.append(change)
                doc_files.append(change) if any(doc in path for doc in ['.md', 'doc', 'readme']) else config_files.append(change)
            else:
                primary_changes.append(change)
                # Categorize primary files
                if 'api' in path or 'server' in path or 'endpoint' in path:
                    api_files.append(change)
                elif 'cli' in path or 'command' in path:
                    cli_files.append(change)
                elif 'script' in path or path.startswith('scripts/'):
                    script_files.append(change)
                elif 'test' in path or 'spec' in path:
                    test_files.append(change)
                else:
                    other_files.append(change)
        
        # Deep code analysis with universal language support
        code_themes = set()
        new_features = []
        bug_fixes = []
        function_names = []
        class_names = []
        domain_terms = []
        
        # Universal programming patterns across languages
        function_patterns = [
            r'(?:def|function|func|fn)\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Python, JS, Rust, Go
            r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)\s*{',  # C, Java, JS, Go
            r'([a-zA-Z_][a-zA-Z0-9_]*):?\s*\([^)]*\)\s*=?>',  # TypeScript, Scala
            r'public\s+\w+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # Java, C#
        ]
        
        class_patterns = [
            r'class\s+([A-Z][a-zA-Z0-9_]*)',  # Python, Java, C++, JS
            r'struct\s+([A-Z][a-zA-Z0-9_]*)',  # Rust, Go, C
            r'interface\s+([A-Z][a-zA-Z0-9_]*)',  # TypeScript, Java, Go
            r'type\s+([A-Z][a-zA-Z0-9_]*)',  # Go, TypeScript
        ]
        
        # Focus analysis on primary changes (ignore docs/config)
        analysis_changes = primary_changes if primary_changes else changes_analysis
        
        for change in analysis_changes:
            diff = change.get('diff_content', '')
            if not diff:
                continue
                
            # Extract all added lines for deep analysis
            added_lines = [line for line in diff.split('\n') if line.startswith('+') and not line.startswith('+++')]
            
            # Analyze up to 50 lines (much deeper than before)
            for line in added_lines[:50]:
                line_content = line[1:].strip()  # Remove the '+' prefix
                line_lower = line_content.lower()
                
                # Extract function names using universal patterns
                import re
                for pattern in function_patterns:
                    matches = re.findall(pattern, line_content)
                    for match in matches:
                        if len(match) > 2 and not match.startswith('_'):  # Skip private/test functions
                            function_names.append(match)
                
                # Extract class names
                for pattern in class_patterns:
                    matches = re.findall(pattern, line_content)
                    for match in matches:
                        if len(match) > 2:
                            class_names.append(match)
                
                # Comprehensive domain analysis
                domain_keywords = {
                    'authentication': ['auth', 'login', 'signin', 'signup', 'password', 'token', 'oauth', 'jwt', 'session'],
                    'user-management': ['user', 'profile', 'account', 'member', 'admin', 'role', 'permission'],
                    'api-development': ['api', 'endpoint', 'route', 'handler', 'controller', 'middleware', 'request', 'response'],
                    'database': ['db', 'database', 'sql', 'query', 'table', 'model', 'schema', 'migration'],
                    'cli-tools': ['cli', 'command', 'arg', 'option', 'flag', 'parser', 'terminal', 'console'],
                    'web-frontend': ['component', 'react', 'vue', 'html', 'css', 'frontend', 'ui', 'interface'],
                    'testing': ['test', 'spec', 'mock', 'assert', 'expect', 'unit', 'integration'],
                    'security': ['security', 'encrypt', 'decrypt', 'hash', 'validate', 'sanitize', 'csrf', 'xss'],
                    'monitoring': ['log', 'metric', 'monitor', 'analytics', 'track', 'debug', 'error'],
                    'deployment': ['deploy', 'docker', 'k8s', 'kubernetes', 'ci', 'cd', 'build', 'pipeline'],
                    'payment': ['payment', 'checkout', 'billing', 'invoice', 'stripe', 'paypal', 'transaction'],
                    'notification': ['notification', 'email', 'sms', 'push', 'alert', 'message'],
                    'file-management': ['file', 'upload', 'download', 'storage', 's3', 'blob', 'attachment'],
                    'search': ['search', 'index', 'elasticsearch', 'solr', 'query', 'filter'],
                    'cache': ['cache', 'redis', 'memcache', 'session', 'store'],
                    'integration': ['integration', 'webhook', 'sync', 'import', 'export', 'connector'],
                    'ai-features': ['ai', 'ml', 'machine learning', 'categorization', 'classification', 'generation', 'smart', 'intelligence'],
                    'branch-management': ['branch', 'git', 'commit', 'merge', 'checkout', 'protection', 'workflow'],
                }
                
                # Check for domain matches
                for domain, keywords in domain_keywords.items():
                    if any(keyword in line_lower for keyword in keywords):
                        code_themes.add(domain)
                
                # Extract specific technical terms for naming
                tech_terms = re.findall(r'[a-zA-Z][a-zA-Z0-9_]{3,}', line_content)
                for term in tech_terms:
                    if (len(term) > 3 and term.lower() not in ['true', 'false', 'null', 'none', 'self', 'this'] 
                        and not term.startswith('_')):
                        domain_terms.append(term.lower())
            
            # Detect new features and bug fixes
            if any(pattern in diff.lower() for pattern in ['+ def ', '+def ', '+ class ', '+class ', '+ function', '+function']):
                new_features.append(f"New code in {change['file_path']}")
            
            if any(word in diff.lower() for word in ['fix', 'bug', 'error', 'exception', 'issue', 'resolve']):
                bug_fixes.append(f"Fix in {change['file_path']}")
        
        # Clean and deduplicate extracted information
        function_names = list(set(function_names))[:10]  # Top 10 unique functions
        class_names = list(set(class_names))[:10]  # Top 10 unique classes  
        domain_terms = list(set(domain_terms))[:20]  # Top 20 unique terms
        code_themes = list(code_themes)
        
        prompt = f"""You are an expert developer analyzing code changes to generate an intelligent Git branch name that captures the OVERALL PURPOSE of the work being done.

## CODE CHANGES ANALYSIS
**Total Files:** {file_count} files ({len(primary_changes)} primary code files, {len(auxiliary_files)} auxiliary files)
**Scale:** +{total_lines_added} lines, -{total_lines_removed} lines

**PRIMARY CODE FILES (focus on these):**
"""
        
        if api_files:
            prompt += f"- **API/Server files:** {len(api_files)} files ({', '.join([f['file_path'] for f in api_files[:3]])})\n"
        if cli_files:
            prompt += f"- **CLI files:** {len(cli_files)} files ({', '.join([f['file_path'] for f in cli_files[:3]])})\n"
        if script_files:
            prompt += f"- **Scripts:** {len(script_files)} files ({', '.join([f['file_path'] for f in script_files[:3]])})\n"
        if test_files:
            prompt += f"- **Tests:** {len(test_files)} files ({', '.join([f['file_path'] for f in test_files[:3]])})\n"
        if other_files:
            prompt += f"- **Core files:** {len(other_files)} files ({', '.join([f['file_path'] for f in other_files[:3]])})\n"
            
        if auxiliary_files:
            prompt += f"\n**AUXILIARY FILES (ignore for branch naming):** {len(auxiliary_files)} files (docs, config, etc.)\n"
        
        if code_themes:
            prompt += f"\n**🎯 Detected Domains:** {', '.join(code_themes)}\n"
        
        if function_names:
            prompt += f"\n**🔧 New Functions:** {', '.join(function_names[:5])}\n"
            
        if class_names:
            prompt += f"\n**📦 New Classes:** {', '.join(class_names[:5])}\n"
            
        if domain_terms:
            # Show most relevant technical terms
            relevant_terms = [term for term in domain_terms if len(term) > 4][:8]
            if relevant_terms:
                prompt += f"\n**💡 Key Terms:** {', '.join(relevant_terms)}\n"
        
        if new_features:
            prompt += f"\n**✨ New Features Detected:** {len(new_features)} files have new functions/classes\n"
        
        if bug_fixes:
            prompt += f"\n**🐛 Bug Fixes Detected:** {len(bug_fixes)} files contain fix-related changes\n"

        prompt += f"""
## DETAILED CHANGE ANALYSIS (PRIMARY FILES ONLY)
"""
        
        # Show actual code changes for context - focus on primary files
        for i, change in enumerate(analysis_changes[:5], 1):
            prompt += f"""
**File {i}: {change['file_path']}** ({change['change_type']})
"""
            
            diff = change.get('diff_content', '')
            if diff:
                # Extract meaningful snippets from the diff
                lines = diff.split('\n')
                added_lines = [line[1:].strip() for line in lines if line.startswith('+') and not line.startswith('+++') and line.strip() != '+']
                removed_lines = [line[1:].strip() for line in lines if line.startswith('-') and not line.startswith('---') and line.strip() != '-']
                
                if added_lines:
                    prompt += f"  Adding: {' | '.join(added_lines[:3])}\n"
                if removed_lines:
                    prompt += f"  Removing: {' | '.join(removed_lines[:3])}\n"
            
            if change.get('lines_added', 0) > 0 or change.get('lines_removed', 0) > 0:
                prompt += f"  Scale: +{change.get('lines_added', 0)}/-{change.get('lines_removed', 0)} lines\n"
        
        prompt += """
## YOUR TASK
Using the deep code analysis above, determine the SPECIFIC PRIMARY FEATURE being developed. Focus on the primary code files and detected domains - ignore auxiliary files like documentation.

## BRANCH NAMING STRATEGY
1. **Identify the main domain** from "🎯 Detected Domains" 
2. **Use specific terms** from "🔧 New Functions", "📦 New Classes", and "💡 Key Terms"
3. **Focus on the core functionality** being built, not maintenance tasks
4. **Name the capability/system, not the implementation action**

## NAMING PRINCIPLES
- ❌ Avoid implementation verbs: "add", "implement", "create", "update"  
- ✅ Focus on the capability: "authentication-system", "branch-protection"
- ❌ Avoid redundant context: "for-users", "in-the-app"
- ✅ Use system-level terms: "system", "engine", "workflow", "integration"

## RESPONSE FORMAT
Use the pattern: "feat(scope): capability or system name"

GOOD EXAMPLES:
- feat(ai): smart-categorization-and-title-generation-system
- feat(auth): jwt-token-validation-and-session-management  
- feat(cli): user-management-command-interface
- feat(git): branch-protection-with-intelligent-naming

BAD EXAMPLES:
- feat(ai): add smart categorization features ❌ (uses "add", says "features")
- feat(auth): implement JWT validation for users ❌ (uses "implement", adds "for users")
- feat(git): update branch workflow with AI ❌ (uses "update", too vague)

Return ONLY the branch name."""
        
        return prompt