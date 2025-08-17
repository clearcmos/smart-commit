"""
Scope caching system for Smart Commit.

This module provides intelligent caching of scope analysis results to dramatically
improve performance while maintaining 100% accuracy.
"""

import os
import json
import fnmatch
from typing import Optional, Dict, Any
from loguru import logger


class ScopeCache:
    """In-memory cache for scope analysis results."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Optional[str]] = {}
        self._max_size = max_size
        self._access_count: Dict[str, int] = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    def get_scope(self, file_path: str) -> Optional[str]:
        """Get scope from cache or compute and cache it."""
        
        # Check cache first (FAST - microseconds)
        if file_path in self._cache:
            self._access_count[file_path] += 1
            self._cache_hits += 1
            return self._cache[file_path]
        
        # Cache miss - compute and store (SLOW - but only once per file)
        self._cache_misses += 1
        scope = self._compute_scope(file_path)
        
        # Store in cache
        self._cache[file_path] = scope
        self._access_count[file_path] = 1
        
        # Evict least used if cache is full
        if len(self._cache) > self._max_size:
            self._evict_least_used()
        
        return scope
    
    def _compute_scope(self, file_path: str) -> Optional[str]:
        """Actually compute the scope (expensive operation)."""
        try:
            from smart_commit.utils.prompts import PromptBuilder
            pb = PromptBuilder()
            return pb._analyze_scope(file_path)
        except Exception as e:
            logger.debug(f"Failed to compute scope for {file_path}: {e}")
            return None
    
    def _evict_least_used(self):
        """Remove least-used scopes when cache is full."""
        if len(self._cache) > self._max_size:
            # Remove least accessed scope
            least_used = min(self._access_count.items(), key=lambda x: x[1])
            del self._cache[least_used[0]]
            del self._access_count[least_used[0]]
            logger.debug(f"Evicted {least_used[0]} from scope cache")
    
    def invalidate_file(self, file_path: str):
        """Remove specific file from cache."""
        if file_path in self._cache:
            del self._cache[file_path]
            del self._access_count[file_path]
            logger.debug(f"Invalidated {file_path} from scope cache")
    
    def invalidate_pattern(self, pattern: str):
        """Remove files matching pattern from cache."""
        to_remove = [path for path in self._cache.keys() if fnmatch.fnmatch(path, pattern)]
        for path in to_remove:
            del self._cache[path]
            del self._access_count[path]
        logger.debug(f"Invalidated {len(to_remove)} files matching pattern {pattern}")
    
    def clear_cache(self):
        """Clear entire cache."""
        self._cache.clear()
        self._access_count.clear()
        logger.debug("Cleared scope cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return {
            'cache_size': len(self._cache),
            'max_size': self._max_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0
        }


class PersistentScopeCache(ScopeCache):
    """Persistent scope cache that survives between sessions."""
    
    def __init__(self, cache_file: str = "~/.cache/smart-commit/scopes.json", max_size: int = 1000):
        super().__init__(max_size)
        self.cache_file = os.path.expanduser(cache_file)
        self._load_cache()
    
    def _load_cache(self):
        """Load cached scopes from disk."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self._cache = data.get('scopes', {})
                    self._access_count = data.get('access_count', {})
                    self._cache_hits = data.get('cache_hits', 0)
                    self._cache_misses = data.get('cache_misses', 0)
                logger.debug(f"Loaded {len(self._cache)} scopes from cache file")
        except Exception as e:
            logger.debug(f"Failed to load scope cache: {e}")
            self._cache = {}
            self._access_count = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            data = {
                'scopes': self._cache,
                'access_count': self._access_count,
                'cache_hits': self._cache_hits,
                'cache_misses': self._cache_misses
            }
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"Saved {len(self._cache)} scopes to cache file")
        except Exception as e:
            logger.debug(f"Failed to save scope cache: {e}")
    
    def get_scope(self, file_path: str) -> Optional[str]:
        """Get scope from cache with automatic persistence."""
        result = super().get_scope(file_path)
        # Save cache periodically (every 10 operations)
        if (self._cache_hits + self._cache_misses) % 10 == 0:
            self._save_cache()
        return result
    
    def clear_cache(self):
        """Clear cache and remove cache file."""
        super().clear_cache()
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
                logger.debug("Removed scope cache file")
        except Exception as e:
            logger.debug(f"Failed to remove cache file: {e}")


class LazyScopeAnalyzer:
    """Lazy-loaded scope analyzer with caching."""
    
    def __init__(self):
        self._prompt_builder = None
        self._scope_cache = PersistentScopeCache()
    
    @property
    def prompt_builder(self):
        """Lazy load PromptBuilder only when needed."""
        if self._prompt_builder is None:
            from smart_commit.utils.prompts import PromptBuilder
            self._prompt_builder = PromptBuilder()
        return self._prompt_builder
    
    def get_scope(self, file_path: str) -> Optional[str]:
        """Get scope with intelligent caching."""
        return self._scope_cache.get_scope(file_path)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        return self._scope_cache.get_stats()
    
    def clear_cache(self):
        """Clear the scope cache."""
        self._scope_cache.clear_cache()
