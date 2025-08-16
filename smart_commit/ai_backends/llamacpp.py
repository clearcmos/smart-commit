"""
llama.cpp AI backend implementation.
"""

import asyncio
import aiohttp
from typing import Dict, Any
from loguru import logger

from .base import AIBackend, AIResponse


class LlamaCppBackend(AIBackend):
    """llama.cpp AI backend implementation."""
    
    async def call_api(self, prompt: str) -> AIResponse:
        """Call the llama.cpp API using OpenAI-compatible endpoint."""
        self._log_request(prompt)
        
        payload = {
            "prompt": prompt,
            "max_tokens": 150,
            "temperature": 0.1,
            "top_p": 0.9,
            "stop": ["\n\n", "```"],
            "stream": False
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/v1/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract response from OpenAI-compatible format
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError("No choices in llama.cpp response")
                    
                    content = choices[0].get("text", "").strip()
                    if not content:
                        raise ValueError("Empty response from llama.cpp")
                    
                    # Extract token usage if available
                    usage = data.get("usage", {})
                    tokens_used = usage.get("total_tokens")
                    
                    return AIResponse(
                        content=content,
                        model=self.model,
                        tokens_used=tokens_used,
                        backend_type=self.backend_type,
                        raw_response=data
                    )
                    
            except aiohttp.ClientError as e:
                logger.error(f"llama.cpp API error: {e}")
                raise
            except asyncio.TimeoutError:
                logger.error(f"llama.cpp API timeout after {self.timeout}s")
                raise
    
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
            logger.info(f"Auto-detected llama.cpp model: {detected_model}")
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