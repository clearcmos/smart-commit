"""
llama.cpp AI backend implementation.
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional
from loguru import logger

from smart_commit.ai_backends.base import AIBackend, AIResponse


class LlamaCppBackend(AIBackend):
    """llama.cpp AI backend implementation."""
    
    def __init__(self, api_url: str, model: str, timeout: int = 120):
        """Initialize llama.cpp backend."""
        super().__init__(api_url, model, timeout)
        self.backend_type = "llamacpp"
        
        # Auto-detect model if not specified
        if self.model == "auto-detected":
            asyncio.create_task(self.auto_detect_model())
    
    def _format_chatml_prompt(self, prompt: str) -> str:
        """Format prompt using Qwen ChatML template."""
        return f"""<|im_start|>system
You are a helpful AI assistant specialized in generating conventional commit messages. You analyze code changes and create clear, concise commit messages following conventional commit standards.

CRITICAL RULES:
1. SCOPE IS MANDATORY: You MUST use the EXACT scope provided after "SCOPE:" in the prompt
2. NEVER use the full file path as scope - only use the specified scope
3. Follow the Conventional Commits 1.0.0 specification exactly
4. Use the format: type(scope): description
5. Keep descriptions under 150 characters (allows longer, more descriptive messages)
6. Use imperative mood (add, fix, remove, not added, fixed, removed)
7. Be specific about what changed in the code
8. NEVER respond with "No changes", "No changes made", or similar phrases
9. ALWAYS generate a proper conventional commit message
10. The response must start with a commit type (feat, fix, chore, etc.)
11. SCOPE ENFORCEMENT: The scope in your response MUST match EXACTLY what is specified in the prompt after "SCOPE:"
12. IGNORE THE FILE PATH - ONLY USE THE SPECIFIED SCOPE

EXAMPLE: If the prompt says "SCOPE: ai" and the file is "smart_commit/ai_backends/base.py", use "fix(ai): description" NOT "fix(smart_commit/ai_backends/base.py): description"

The scope is determined by the prompt instruction, NOT by the file path. Follow the scope guidance exactly as provided.

OUTPUT FORMAT: You must output ONLY a conventional commit message, nothing else.
<|im_end|>
<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""
    
    async def call_api(self, prompt: str) -> AIResponse:
        """Call the llama.cpp API using OpenAI-compatible endpoint."""
        import time
        from smart_commit.ai_backends.base import ValidationError
        
        start_time = time.time()
        
        self._log_request(prompt)
        
        # Format prompt for ChatML
        format_start = time.time()
        formatted_prompt = self._format_chatml_prompt(prompt)
        format_time = time.time() - format_start
        
        payload = {
            "prompt": formatted_prompt,
            "max_tokens": 150,
            "temperature": 0.6,  # Qwen recommendation
            "top_k": 20,         # Qwen recommendation
            "top_p": 0.95,       # Qwen recommendation
            "min_p": 0,          # Qwen recommendation
            "stop": ["<|im_end|>", "\n\n"],  # ChatML stop tokens
            "stream": False
        }
        
        # Use a shorter timeout for individual requests to avoid hanging
        request_timeout = min(self.timeout, 30)  # Cap at 30 seconds per request
        
        api_start = time.time()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/v1/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=request_timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Debug logging for response (only visible with --debug)
                    logger.debug(f"Raw llama.cpp response: {data}")
                    
                    # Extract response from OpenAI-compatible format
                    choices = data.get("choices", [])
                    if not choices:
                        logger.error(f"No choices in llama.cpp response: {data}")
                        raise ValueError("No choices in llama.cpp response")
                    
                    content = choices[0].get("text", "").strip()
                    logger.debug(f"Extracted content: '{content}' (length: {len(content)})")
                    
                    # Validate response quality
                    if not content:
                        logger.error(f"Empty content from llama.cpp response: {data}")
                        raise ValueError("Empty response from llama.cpp")
                    
                    # Check if response is too short (likely incomplete)
                    if len(content) < 10:
                        logger.warning(f"Response too short, likely incomplete: '{content}'")
                        raise ValueError("Response too short, likely incomplete")
                    
                    # Check if response looks like a commit message
                    validation_start = time.time()
                    if not self._looks_like_commit_message(content):
                        logger.debug(f"Response doesn't look like a commit message: '{content}'")
                        raise ValidationError("Response validation failed - using fallback")
                    validation_time = time.time() - validation_start
                    
                    # Extract token usage if available
                    usage = data.get("usage", {})
                    tokens_used = usage.get("total_tokens")
                    
                    # Create response object
                    ai_response = AIResponse(
                        content=content,
                        model=self.model,
                        tokens_used=tokens_used,
                        backend_type=self.backend_type
                    )
                    
                    total_time = time.time() - start_time
                    api_time = time.time() - api_start
                    
                    logger.info(f"✅ AI Response generated in {total_time:.2f}s (format: {format_time:.3f}s, API: {api_time:.2f}s, validation: {validation_time:.3f}s)")
                    
                    return ai_response
                    
            except ValidationError:
                # Re-raise validation errors without logging them as errors
                raise
            except aiohttp.ClientError as e:
                logger.error(f"llama.cpp API error: {e}")
                raise
            except asyncio.TimeoutError:
                logger.error(f"llama.cpp API timeout after {request_timeout}s")
                raise
            except Exception as e:
                logger.error(f"Unexpected error in llama.cpp call_api: {e}")
                raise
    
    def _looks_like_commit_message(self, content: str) -> bool:
        """Check if the response looks like a valid commit message."""
        if not content:
            return False
        
        # Must have reasonable length (allow longer descriptions)
        if len(content) < 10 or len(content) > 300:  # Increased from 200 to 300
            return False
        
        # Must contain a colon (typical of commit messages)
        if ':' not in content:
            return False
        
        # Must not contain obvious error messages (but allow valid technical terms)
        # Check for error messages that are likely AI failures, not valid commit content
        error_indicators = ['failed', 'timeout', 'invalid', 'no changes', 'No changes']
        
        # Only reject if the content looks like an error message, not if it contains valid technical terms
        content_lower = content.lower()
        if any(indicator in content_lower for indicator in error_indicators):
            return False
        
        # Special case: allow "empty" if it's part of a valid technical description
        # (e.g., "empty blob", "empty file", "empty directory" are valid Git terms)
        if 'empty' in content_lower:
            # Check if "empty" is used in a technical context, not as an error message
            technical_empty_contexts = ['empty blob', 'empty file', 'empty directory', 'empty string', 'empty array', 'empty list']
            if not any(context in content_lower for context in technical_empty_contexts):
                # If "empty" appears alone or in a non-technical context, it might be an error message
                # But let's be more lenient and only reject if it's clearly an error
                if content_lower.strip() == 'empty' or content_lower.startswith('empty:'):
                    return False
        
        # Special case: allow "error" if it's part of a valid technical description
        # (e.g., "error handling", "error handling", "error detection" are valid)
        if 'error' in content_lower:
            # Check if "error" is used in a technical context, not as an error message
            technical_error_contexts = ['error handling', 'error detection', 'error reporting', 'error logging', 'error recovery']
            if not any(context in content_lower for context in technical_error_contexts):
                # If "error" appears alone or in a non-technical context, it might be an error message
                # But let's be more lenient and only reject if it's clearly an error
                if content_lower.strip() == 'error' or content_lower.startswith('error:'):
                    return False
        
        # Additional check: the content should look like a conventional commit structure
        # Look for the pattern: type(scope): description or type: description
        import re
        
        # More flexible pattern that allows for slight variations
        # Pattern 1: type(scope): description (allows leading whitespace) - REQUIRED
        pattern1 = re.compile(r'\s*[a-z]+\([^)]+\):\s+.+', re.IGNORECASE)
        # Pattern 2: type: description (no scope, allows leading whitespace) - NOT ALLOWED for smart_commit files
        pattern2 = re.compile(r'\s*[a-z]+:\s+.+', re.IGNORECASE)
        
        # Check if any line matches either conventional commit pattern
        lines = content.split('\n')
        has_conventional_format = False
        has_scope = False
        
        for line in lines:
            line = line.strip()
            if pattern1.match(line):
                has_conventional_format = True
                has_scope = True
                break
            elif pattern2.match(line):
                has_conventional_format = True
                has_scope = False
                break
        
        if not has_conventional_format:
            return False
        
        # For smart_commit files, require scopes
        if not has_scope:
            return False
        
        # Scope validation: check for common scope inconsistencies
        # This helps catch cases where the AI uses semantic scopes instead of file path scopes
        scope_inconsistencies = {
            'ai': ['smart_commit', 'core', 'utils'],
            'core': ['smart_commit', 'ai', 'utils'],
            'utils': ['smart_commit', 'ai', 'core']
        }
        
        # Extract scope from the first conventional commit line
        for line in lines:
            line = line.strip()
            if pattern1.match(line) or pattern2.match(line):
                # Extract scope from type(scope): description
                scope_match = re.search(r'^[a-z]+\(([^)]+)\):', line, re.IGNORECASE)
                if scope_match:
                    scope = scope_match.group(1).lower()
                    
                    # Reject verbose scopes (containing slashes, dots, or too long)
                    if '/' in scope or '.' in scope or len(scope) > 25:
                        logger.debug(f"Verbose scope detected: '{scope}' in '{line}' - scope should be concise")
                        return False
                    
                    # Check if this scope might be inconsistent (but don't reject)
                    for inconsistent_scope, alternatives in scope_inconsistencies.items():
                        if scope == inconsistent_scope and any(alt in line.lower() for alt in alternatives):
                            logger.debug(f"Potential scope inconsistency detected: {scope} in '{line}'")
                            # Don't reject, just log for monitoring
                break
        
        return True
    
    def _get_expected_scope_for_file(self, file_path: str) -> Optional[str]:
        """Get the expected scope for a file based on its path."""
        try:
            from smart_commit.utils.prompts import PromptBuilder
            pb = PromptBuilder()
            return pb._analyze_scope(file_path)
        except:
            return None
    
    def _is_scope_appropriate(self, content: str, expected_scope: str) -> bool:
        """Check if the AI-generated scope is appropriate for the expected scope."""
        # Extract the actual scope from the AI response
        import re
        
        # Look for scope in conventional commit format
        scope_pattern = re.compile(r'\s*[a-z]+\(([^)]+)\):\s+.+', re.IGNORECASE)
        match = scope_pattern.search(content)
        
        if not match:
            return False
        
        actual_scope = match.group(1).lower()
        
        # Check if the actual scope is close to the expected scope
        # Allow some flexibility but catch obvious mismatches
        if actual_scope == expected_scope:
            return True
        
        # Allow semantic variations (e.g., 'ui' vs 'components')
        semantic_mappings = {
            'docs': ['docs', 'documentation', 'readme', 'claude'],
            'ui': ['ui', 'components', 'frontend', 'react'],
            'api': ['api', 'backend', 'server', 'routes'],
            'core': ['core', 'main', 'app', 'smart_commit'],
            'utils': ['utils', 'utilities', 'helpers', 'common']
        }
        
        for expected, variations in semantic_mappings.items():
            if expected_scope in variations and actual_scope in variations:
                return True
        
        # If no semantic match, require exact match
        return False
    
    async def health_check(self) -> bool:
        """Check if llama.cpp server is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"llama.cpp health check failed: {e}")
            return False
    
    async def list_models(self) -> list[str]:
        """List available llama.cpp models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/v1/models",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    models = []
                    for model in data.get("data", []):
                        models.append(model.get("id", ""))
                    
                    return [m for m in models if m]
                    
        except Exception as e:
            logger.debug(f"Failed to list llama.cpp models: {e}")
            return []
    
    async def auto_detect_model(self) -> str:
        """Auto-detect the loaded model from llama.cpp server."""
        models = await self.list_models()
        
        if models:
            # Use the first (usually only) model
            detected_model = models[0]
            logger.debug(f"Auto-detected llama.cpp model: {detected_model}")
            return detected_model
        
        logger.warning("No llama.cpp models detected, using configured model")
        return self.model
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get detailed server information."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/props",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.debug(f"Failed to get llama.cpp server info: {e}")
        
        return {}

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection and response quality."""
        logger.info("Testing llama.cpp connection and response quality...")
        
        test_results = {
            "health_check": False,
            "model_list": False,
            "completion_test": False,
            "response_quality": "unknown"
        }
        
        try:
            # Test 1: Health check
            health_ok = await self.health_check()
            test_results["health_check"] = health_ok
            logger.info(f"Health check: {'✅' if health_ok else '❌'}")
            
            # Test 2: Model list
            try:
                models = await self.list_models()
                test_results["model_list"] = len(models) > 0
                logger.info(f"Model list: {'✅' if test_results['model_list'] else '❌'} ({models})")
            except Exception as e:
                logger.warning(f"Model list test failed: {e}")
            
            # Test 3: Simple completion
            try:
                test_prompt = "Generate a simple commit message: feat: test"
                response = await self.call_api(test_prompt)
                test_results["completion_test"] = True
                test_results["response_quality"] = "good" if len(response.content) > 10 else "poor"
                logger.info(f"Completion test: ✅ (response: '{response.content}')")
            except Exception as e:
                logger.warning(f"Completion test failed: {e}")
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
        
        return test_results