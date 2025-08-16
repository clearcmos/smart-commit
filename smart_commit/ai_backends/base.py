"""
Abstract base class for AI backends with plugin architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
from loguru import logger


@dataclass
class AIResponse:
    """Structured AI response data."""
    
    content: str
    model: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    backend_type: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class AIBackend(ABC):
    """Abstract base class for AI backends."""
    
    def __init__(self, api_url: str, model: str, timeout: int = 120):
        """Initialize the AI backend."""
        self.api_url = api_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.backend_type = self.__class__.__name__.lower().replace('backend', '')
    
    @abstractmethod
    async def call_api(self, prompt: str) -> AIResponse:
        """Call the AI API with the given prompt."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the AI backend is healthy and responsive."""
        pass
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available models from the backend."""
        pass
    
    def _log_request(self, prompt: str) -> None:
        """Log the API request details."""
        logger.debug(f"AI API request to {self.backend_type}")
        logger.debug(f"URL: {self.api_url}")
        logger.debug(f"Model: {self.model}")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        logger.debug(f"Timeout: {self.timeout}s")
    
    def _log_response(self, response: AIResponse) -> None:
        """Log the API response details."""
        logger.debug(f"AI API response from {self.backend_type}")
        logger.debug(f"Response length: {len(response.content)} characters")
        if response.tokens_used:
            logger.debug(f"Tokens used: {response.tokens_used}")
        if response.response_time:
            logger.debug(f"Response time: {response.response_time:.2f}s")
    
    async def call_with_retry(self, prompt: str, max_retries: int = 3) -> AIResponse:
        """Call the AI API with retry logic."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"AI API attempt {attempt + 1}/{max_retries}")
                start_time = time.time()
                
                response = await self.call_api(prompt)
                response.response_time = time.time() - start_time
                
                self._log_response(response)
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(f"AI API attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.debug(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
        
        logger.error(f"All {max_retries} AI API attempts failed")
        raise last_exception


import asyncio