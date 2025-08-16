"""
Professional commit message extraction and cleaning utilities.
"""

import re
from typing import Optional, List
from loguru import logger


class MessageExtractor:
    """Extract and clean commit messages from AI responses."""
    
    # Conventional commit types
    COMMIT_TYPES = [
        "feat", "fix", "docs", "style", "refactor", 
        "test", "chore", "build", "ci", "perf", "revert"
    ]
    
    def __init__(self, character_limit: int = 90):
        """Initialize message extractor."""
        self.character_limit = character_limit
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        types_pattern = "|".join(self.COMMIT_TYPES)
        
        # Pattern for conventional commits with scope
        self.pattern_with_scope = re.compile(
            rf'^({types_pattern})\(([^)]+)\):\s*(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Pattern for conventional commits without scope
        self.pattern_no_scope = re.compile(
            rf'^({types_pattern}):\s*(.+)$',
            re.MULTILINE | re.IGNORECASE
        )
        
        # Pattern for any line with conventional commit types
        self.pattern_any_type = re.compile(
            rf'({types_pattern})\b',
            re.IGNORECASE
        )
    
    def extract_commit_message(self, raw_response: str) -> Optional[str]:
        """Extract commit message using multiple strategies."""
        logger.debug(f"Extracting commit message from {len(raw_response)} char response")
        
        # Clean the response first
        cleaned_response = self._clean_response(raw_response)
        
        if not cleaned_response:
            logger.warning("Empty response after cleaning")
            return None
        
        # Strategy 1: Look for conventional commit with scope
        message = self._extract_with_scope(cleaned_response)
        if message:
            logger.debug(f"Extracted with scope: {message}")
            return self._finalize_message(message)
        
        # Strategy 2: Look for conventional commit without scope
        message = self._extract_without_scope(cleaned_response)
        if message:
            logger.debug(f"Extracted without scope: {message}")
            return self._finalize_message(message)
        
        # Strategy 3: Look for any line with commit types
        message = self._extract_any_commit_line(cleaned_response)
        if message:
            logger.debug(f"Extracted any commit line: {message}")
            return self._finalize_message(message)
        
        # Strategy 4: Intelligent fallback
        message = self._intelligent_fallback(cleaned_response)
        if message:
            logger.debug(f"Used intelligent fallback: {message}")
            return self._finalize_message(message)
        
        logger.warning("Could not extract commit message from response")
        return None
    
    def _clean_response(self, response: str) -> str:
        """Clean AI response by removing markdown and formatting."""
        # Remove markdown code blocks
        cleaned = re.sub(r'```\w*\n?', '', response)
        cleaned = re.sub(r'```', '', cleaned)
        
        # Remove HTML tags
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Remove extra whitespace and empty lines
        lines = [line.strip() for line in cleaned.split('\n') if line.strip()]
        
        return '\n'.join(lines)
    
    def _extract_with_scope(self, text: str) -> Optional[str]:
        """Extract conventional commit message with scope."""
        match = self.pattern_with_scope.search(text)
        if match:
            commit_type, scope, description = match.groups()
            return f"{commit_type.lower()}({scope.lower()}): {description.strip()}"
        return None
    
    def _extract_without_scope(self, text: str) -> Optional[str]:
        """Extract conventional commit message without scope."""
        match = self.pattern_no_scope.search(text)
        if match:
            commit_type, description = match.groups()
            return f"{commit_type.lower()}: {description.strip()}"
        return None
    
    def _extract_any_commit_line(self, text: str) -> Optional[str]:
        """Extract any line containing conventional commit types."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains a commit type and colon
            if ':' in line and self.pattern_any_type.search(line):
                # Try to clean and format the line
                return self._clean_commit_line(line)
        
        return None
    
    def _clean_commit_line(self, line: str) -> str:
        """Clean and format a potential commit line."""
        # Remove quotes and extra characters
        line = re.sub(r'^["\'\`]+|["\'\`]+$', '', line)
        line = re.sub(r'^\W+|\W+$', '', line)
        
        # Ensure proper format
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                prefix = parts[0].strip().lower()
                description = parts[1].strip()
                
                # Validate prefix
                for commit_type in self.COMMIT_TYPES:
                    if commit_type in prefix:
                        return f"{prefix}: {description}"
        
        return line
    
    def _intelligent_fallback(self, text: str) -> Optional[str]:
        """Intelligent fallback for difficult responses."""
        lines = text.split('\n')
        
        # Look for the most likely commit message line
        candidates = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Score lines based on characteristics
            score = 0
            
            # Contains conventional commit type
            if any(t in line.lower() for t in self.COMMIT_TYPES):
                score += 3
            
            # Contains colon (typical of commit messages)
            if ':' in line:
                score += 2
            
            # Reasonable length
            if 20 <= len(line) <= 100:
                score += 1
            
            # Not too many special characters
            if len(re.findall(r'[^\w\s:(),-]', line)) < 3:
                score += 1
            
            if score >= 3:
                candidates.append((score, line))
        
        if candidates:
            # Return the highest scoring candidate
            candidates.sort(reverse=True)
            best_line = candidates[0][1]
            return self._format_fallback_message(best_line)
        
        return None
    
    def _format_fallback_message(self, line: str) -> str:
        """Format a fallback message into conventional commit format."""
        line = line.strip()
        
        # If it already looks like a conventional commit, return as-is
        if any(f"{t}:" in line.lower() or f"{t}(" in line.lower() for t in self.COMMIT_TYPES):
            return line
        
        # Otherwise, make it a generic feature commit
        if not line.endswith('.'):
            return f"feat: {line}"
        else:
            return f"feat: {line[:-1]}"  # Remove trailing period
    
    def _finalize_message(self, message: str) -> str:
        """Finalize message with length checks and cleanup."""
        # Remove quotes and backticks
        message = re.sub(r'^["\'\`]+|["\'\`]+$', '', message.strip())
        
        # Smart length management
        if len(message) > self.character_limit:
            message = self._smart_truncate(message)
        
        return message
    
    def _smart_truncate(self, message: str) -> str:
        """Intelligently truncate long messages."""
        if len(message) <= self.character_limit:
            return message
        
        # Try to preserve the type and scope
        parts = message.split(':', 1)
        if len(parts) != 2:
            # Simple truncation if not conventional format
            return message[:self.character_limit - 3] + "..."
        
        prefix, description = parts
        description = description.strip()
        
        # Calculate available space for description
        available_space = self.character_limit - len(prefix) - 2  # -2 for ": "
        
        if available_space <= 10:
            # Very long prefix, just truncate everything
            return message[:self.character_limit - 3] + "..."
        
        # Smart description truncation
        if len(description) > available_space:
            # Try to truncate at word boundary
            truncated = description[:available_space - 3]
            last_space = truncated.rfind(' ')
            
            if last_space > available_space // 2:
                # Good word boundary found
                truncated = truncated[:last_space]
            
            description = truncated + "..."
        
        return f"{prefix}: {description}"


# Create global instance
message_extractor = MessageExtractor()