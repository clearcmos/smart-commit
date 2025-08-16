"""
Smart Commit - AI-powered Git commit message generator.

A professional-grade CLI tool that analyzes your git changes and generates
meaningful commit messages using AI backends (Ollama, llama.cpp).
"""

__version__ = "2.0.0"
__author__ = "Nicholas"
__email__ = "clearcmos@domain.com"

from smart_commit.core import SmartCommit
from smart_commit.config.settings import Settings

__all__ = ["SmartCommit", "Settings"]