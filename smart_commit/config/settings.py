"""
Configuration management with Pydantic validation and environment variable support.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, AliasChoices
from pydantic_settings import BaseSettings
import platform


class AISettings(BaseModel):
    """AI backend configuration."""
    
    api_url: str = Field(
        default="http://localhost:11434",
        description="AI server endpoint"
    )
    model: str = Field(
        default="qwen3:8b",
        description="AI model to use"
    )
    backend_type: Literal["ollama", "llamacpp", "auto"] = Field(
        default="auto",
        description="AI backend type"
    )
    timeout: int = Field(
        default=120,
        ge=10,
        le=600,
        description="API request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of API retries"
    )


class GitSettings(BaseModel):
    """Git operation configuration."""
    
    auto_stage: bool = Field(
        default=True,
        description="Automatically stage changes before committing"
    )
    auto_push: bool = Field(
        default=True,
        description="Automatically push commits after creation"
    )
    max_diff_lines: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Maximum lines of diff to analyze"
    )
    atomic_mode: bool = Field(
        default=False,
        description="Create one commit per modified file"
    )


class UISettings(BaseModel):
    """User interface configuration."""
    
    use_colors: bool = Field(
        default=True,
        description="Use colored output"
    )
    show_progress: bool = Field(
        default=True,
        description="Show progress bars"
    )
    interactive: bool = Field(
        default=True,
        description="Enable interactive prompts"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )


class PerformanceSettings(BaseModel):
    """Performance optimization settings."""
    
    enable_optimization: bool = Field(
        default=True,
        description="Enable platform-specific optimizations"
    )
    macos_local_mode: bool = Field(
        default=False,
        description="Enable macOS local optimization mode"
    )
    character_limit: int = Field(
        default=150,  # Increased from 90 to allow longer, more descriptive messages
        ge=50,
        le=300,       # Increased max limit to 300 characters
        description="Maximum commit message character limit"
    )
    
    @field_validator('macos_local_mode', mode='before')
    @classmethod
    def detect_macos_local(cls, v):
        """Auto-detect macOS local mode."""
        if platform.system() == "Darwin":
            # Check if we're likely using local Ollama
            return os.getenv('SMART_COMMIT_MACOS_LOCAL', 'false').lower() == 'true'
        return v


class Settings(BaseSettings):
    """Main application settings with environment variable support."""
    
    ai: AISettings = Field(default_factory=AISettings)
    git: GitSettings = Field(default_factory=GitSettings)
    ui: UISettings = Field(default_factory=UISettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    
    model_config = {
        "env_prefix": "SC_",  # Smart Commit prefix
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "env_file": ".env",
        "extra": "ignore",
    }
    
    def __init__(self, **kwargs):
        # First, try to load from default config file if no explicit config provided
        if not kwargs and not any(os.getenv(var) for var in ["AI_API_URL", "OLLAMA_API_URL", "AI_MODEL", "OLLAMA_MODEL"]):
            config_path = self._get_default_config_path()
            if config_path.exists():
                import json
                try:
                    with open(config_path) as f:
                        config_data = json.load(f)
                    kwargs = config_data
                except (json.JSONDecodeError, OSError):
                    pass  # Fall back to defaults
        
        # Handle environment variables manually for nested fields
        env_overrides = {}
        
        # Check for AI environment variables
        if os.getenv("AI_API_URL") or os.getenv("OLLAMA_API_URL"):
            if not kwargs.get("ai"):
                kwargs["ai"] = {}
            kwargs["ai"]["api_url"] = os.getenv("AI_API_URL") or os.getenv("OLLAMA_API_URL")
        
        if os.getenv("AI_MODEL") or os.getenv("OLLAMA_MODEL"):
            if not kwargs.get("ai"):
                kwargs["ai"] = {}
            kwargs["ai"]["model"] = os.getenv("AI_MODEL") or os.getenv("OLLAMA_MODEL")
        
        if os.getenv("AI_BACKEND_TYPE"):
            if not kwargs.get("ai"):
                kwargs["ai"] = {}
            kwargs["ai"]["backend_type"] = os.getenv("AI_BACKEND_TYPE")
        
        if os.getenv("AI_TIMEOUT"):
            if not kwargs.get("ai"):
                kwargs["ai"] = {}
            try:
                kwargs["ai"]["timeout"] = int(os.getenv("AI_TIMEOUT"))
            except (ValueError, TypeError):
                pass
                
        super().__init__(**kwargs)
    
    def _get_default_config_path(self) -> Path:
        """Get the default config file path."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", "~"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
        
        return (base / "smart-commit" / "config.json").expanduser()
    
    
    @classmethod
    def from_file(cls, config_path: Path) -> "Settings":
        """Load settings from a configuration file."""
        if config_path.exists():
            import json
            with open(config_path) as f:
                config_data = json.load(f)
            return cls(**config_data)
        return cls()
    
    def save_to_file(self, config_path: Path) -> None:
        """Save current settings to a configuration file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            import json
            json.dump(self.model_dump(), f, indent=2)
    
    @property
    def config_dir(self) -> Path:
        """Get the configuration directory."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", "~"))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config"))
        
        return (base / "smart-commit").expanduser()
    
    @property
    def cache_dir(self) -> Path:
        """Get the cache directory."""
        if platform.system() == "Windows":
            base = Path(os.environ.get("LOCALAPPDATA", "~"))
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache"))
        
        return (base / "smart-commit").expanduser()
    
    @property
    def log_file(self) -> Path:
        """Get the log file path."""
        return self.cache_dir / "smart-commit.log"


# Global settings instance
settings = Settings()