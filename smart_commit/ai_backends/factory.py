"""
AI backend factory with auto-detection capabilities.
"""

import asyncio
from typing import Optional
from loguru import logger

from .base import AIBackend
from .ollama import OllamaBackend
from .llamacpp import LlamaCppBackend
from ..config.settings import Settings


class BackendFactory:
    """Factory for creating AI backends with auto-detection."""
    
    _backends = {
        "ollama": OllamaBackend,
        "llamacpp": LlamaCppBackend,
    }
    
    @classmethod
    async def create_backend(
        cls, 
        settings: Settings,
        backend_type: Optional[str] = None
    ) -> AIBackend:
        """Create an AI backend with optional auto-detection."""
        
        # Use explicit backend type if provided
        if backend_type and backend_type != "auto":
            return cls._create_backend_instance(backend_type, settings)
        
        # Use configured backend type if not auto
        if settings.ai.backend_type != "auto":
            return cls._create_backend_instance(settings.ai.backend_type, settings)
        
        # Auto-detect backend
        logger.info("Auto-detecting AI backend...")
        detected_backend = await cls._detect_backend(settings)
        
        if not detected_backend:
            logger.warning("Could not auto-detect backend, falling back to Ollama")
            detected_backend = "ollama"
        
        return cls._create_backend_instance(detected_backend, settings)
    
    @classmethod
    def _create_backend_instance(cls, backend_type: str, settings: Settings) -> AIBackend:
        """Create a backend instance of the specified type."""
        if backend_type not in cls._backends:
            raise ValueError(f"Unknown backend type: {backend_type}")
        
        backend_class = cls._backends[backend_type]
        
        return backend_class(
            api_url=settings.ai.api_url,
            model=settings.ai.model,
            timeout=settings.ai.timeout
        )
    
    @classmethod
    async def _detect_backend(cls, settings: Settings) -> Optional[str]:
        """Auto-detect the backend type by probing endpoints."""
        
        # Test llama.cpp first (more specific endpoint)
        llamacpp = LlamaCppBackend(
            api_url=settings.ai.api_url,
            model=settings.ai.model,
            timeout=5  # Quick probe
        )
        
        if await llamacpp.health_check():
            logger.info("Auto-detected llama.cpp backend")
            return "llamacpp"
        
        # Test Ollama
        ollama = OllamaBackend(
            api_url=settings.ai.api_url,
            model=settings.ai.model,
            timeout=5  # Quick probe
        )
        
        if await ollama.health_check():
            logger.info("Auto-detected Ollama backend")
            return "ollama"
        
        logger.warning("No backend detected via health checks")
        return None
    
    @classmethod
    async def test_all_backends(cls, settings: Settings) -> dict[str, bool]:
        """Test all backend types and return their status."""
        results = {}
        
        for backend_type in cls._backends:
            try:
                backend = cls._create_backend_instance(backend_type, settings)
                results[backend_type] = await backend.health_check()
            except Exception as e:
                logger.debug(f"Failed to test {backend_type}: {e}")
                results[backend_type] = False
        
        return results
    
    @classmethod
    def list_supported_backends(cls) -> list[str]:
        """List all supported backend types."""
        return list(cls._backends.keys())