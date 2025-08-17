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
    
    def __init__(self, character_limit: int = 150):  # Increased from 90 to 150
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
        logger.debug(f"Raw response content: '{raw_response}'")
        
        # Clean the response first
        cleaned_response = self._clean_response(raw_response)
        logger.debug(f"Cleaned response: '{cleaned_response}' (length: {len(cleaned_response)})")
        
        if not cleaned_response:
            logger.warning("Empty response after cleaning")
            return None
        
        # Strategy 1: Look for ChatML-specific patterns
        message = self._extract_chatml_response(cleaned_response)
        if message:
            logger.debug(f"Extracted from ChatML: {message}")
            return self._finalize_message(message)
        
        # Strategy 2: Look for conventional commit with scope
        message = self._extract_with_scope(cleaned_response)
        if message:
            logger.debug(f"Extracted with scope: {message}")
            return self._finalize_message(message)
        
        # Strategy 3: Look for conventional commit without scope
        message = self._extract_without_scope(cleaned_response)
        if message:
            logger.debug(f"Extracted without scope: {message}")
            return self._finalize_message(message)
        
        # Strategy 4: Look for any line with commit types
        message = self._extract_any_commit_line(cleaned_response)
        if message:
            logger.debug(f"Extracted any commit line: {message}")
            return self._finalize_message(message)
        
        # Strategy 5: Intelligent fallback
        message = self._intelligent_fallback(cleaned_response)
        if message:
            logger.debug(f"Used intelligent fallback: {message}")
            return self._finalize_message(message)
        
        # Strategy 6: Ultra-lenient fallback - catch any reasonable commit-like message
        message = self._ultra_lenient_fallback(cleaned_response)
        if message:
            logger.debug(f"Used ultra-lenient fallback: {message}")
            return self._finalize_message(message)
        
        logger.warning("Could not extract commit message from response")
        logger.debug(f"Failed to extract from cleaned response: '{cleaned_response}'")
        return None
    
    def _clean_response(self, response: str) -> str:
        """Clean AI response by removing markdown and formatting."""
        # Extract content from ChatML assistant response
        # Look for content between <|im_start|>assistant and <|im_end|>
        chatml_match = re.search(r'<\|im_start\|>assistant\s*(.*?)(?=<\|im_end\|>|$)', response, re.DOTALL)
        if chatml_match:
            cleaned = chatml_match.group(1).strip()
        else:
            # Fallback: remove ChatML tokens
            cleaned = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', response, flags=re.DOTALL)
            cleaned = re.sub(r'<\|im_start\|>', '', cleaned)
            cleaned = re.sub(r'<\|im_end\|>', '', cleaned)
        
        # Remove markdown code blocks
        cleaned = re.sub(r'```\w*\n?', '', cleaned)
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
    
    def _ultra_lenient_fallback(self, text: str) -> Optional[str]:
        """Ultra-lenient fallback that catches any reasonable commit-like message."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for any line that has a colon and looks like a commit message
            if ':' in line and len(line) > 10 and len(line) < 200:
                # Check if it starts with common commit types
                commit_types = ['fix', 'feat', 'refactor', 'chore', 'docs', 'style', 'test', 'perf', 'build', 'ci', 'revert']
                line_lower = line.lower()
                
                for commit_type in commit_types:
                    if line_lower.startswith(commit_type):
                        return line.strip()
                
                # If no commit type found, but it looks like a commit message, return it
                if '(' in line and ')' in line and ':' in line:
                    return line.strip()
                
                # Even more lenient: any line with colon that's not too long
                if len(line) < 150:  # Allow longer messages
                    return line.strip()
        
        return None
    
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

    def _extract_chatml_response(self, text: str) -> Optional[str]:
        """Extract commit message from ChatML-formatted responses."""
        # Look for the most likely commit message line
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip lines that are clearly not commit messages
            if any(skip in line.lower() for skip in ['<|im_start|>', '<|im_end|>', 'system:', 'user:', 'assistant:']):
                continue
            
            # Check if this line looks like a commit message
            if self._looks_like_commit_message(line):
                return line
        
        return None
    
    def _looks_like_commit_message(self, line: str) -> bool:
        """Check if a line looks like a conventional commit message."""
        line_lower = line.lower()
        
        # Must contain a conventional commit type
        has_type = any(t in line_lower for t in self.COMMIT_TYPES)
        if not has_type:
            return False
        
        # Must contain a colon (typical of commit messages)
        if ':' not in line:
            return False
        
        # Reasonable length
        if len(line) < 10 or len(line) > 200:
            return False
        
        # Not too many special characters
        special_chars = len(re.findall(r'[^\w\s:(),-]', line))
        if special_chars > 5:
            return False
        
        return True


# Create global instance
message_extractor = MessageExtractor()