"""
Ollama AI backend implementation.
"""

import asyncio
import aiohttp
from typing import Dict, Any
from loguru import logger

from .base import AIBackend, AIResponse


class OllamaBackend(AIBackend):
    """Ollama AI backend implementation."""
    
    async def call_api(self, prompt: str) -> AIResponse:
        """Call the Ollama API."""
        self._log_request(prompt)
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    return AIResponse(
                        content=data.get("response", ""),
                        model=self.model,
                        backend_type=self.backend_type,
                        raw_response=data
                    )
                    
            except aiohttp.ClientError as e:
                logger.error(f"Ollama API error: {e}")
                raise
            except asyncio.TimeoutError:
                logger.error(f"Ollama API timeout after {self.timeout}s")
                raise
    
    async def health_check(self) -> bool:
        """Check if Ollama is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    models = []
                    for model in data.get("models", []):
                        models.append(model.get("name", ""))
                    
                    return [m for m in models if m]
                    
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []
    
    async def auto_detect_model(self) -> str:
        """Auto-detect the best available model."""
        models = await self.list_models()
        
        # Preferred model order
        preferred = [
            "qwen3:8b", "qwen3:4b", "qwen2.5-coder:7b", 
            "llama3.2:8b", "llama3.2:3b", "llama3.2:1b"
        ]
        
        for model in preferred:
            if any(model in m for m in models):
                logger.info(f"Auto-detected Ollama model: {model}")
                return model
        
        if models:
            logger.info(f"Using first available model: {models[0]}")
            return models[0]
        
        logger.warning("No Ollama models found, using default")
        return "qwen3:8b"