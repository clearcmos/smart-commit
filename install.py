#!/usr/bin/env python3
"""
Professional installation script for Smart Commit v2.0.

This script handles:
- Dependency management
- Virtual environment setup  
- Configuration migration from bash version
- System integration
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any


class SmartCommitInstaller:
    """Professional installer for Smart Commit."""
    
    def __init__(self):
        """Initialize installer."""
        self.project_root = Path(__file__).parent
        self.python_executable = sys.executable
        self.home_dir = Path.home()
        self.config_dir = self._get_config_dir()
        self.venv_path = self.config_dir / "venv"
        
    def _get_config_dir(self) -> Path:
        """Get platform-appropriate config directory."""
        if sys.platform == "win32":
            base = Path(os.environ.get("APPDATA", self.home_dir))
        else:
            base = Path(os.environ.get("XDG_CONFIG_HOME", self.home_dir / ".config"))
        
        return base / "smart-commit"
    
    def _get_cache_dir(self) -> Path:
        """Get platform-appropriate cache directory."""
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", self.home_dir))
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", self.home_dir / ".cache"))
        
        return base / "smart-commit"
    
    def _handle_path_setup(self, user_bin: Path) -> None:
        """Handle PATH setup with user prompt and idempotent checks."""
        print()
        print("🔧 PATH Configuration")
        print(f"The smart-commit command was installed to: {user_bin}")
        print("This directory needs to be in your PATH to use 'smart-commit' from anywhere.")
        print()
        
        # Detect shell and shell RC file
        shell_name = os.environ.get('SHELL', '/bin/bash').split('/')[-1]
        if shell_name == 'zsh' or 'zsh' in shell_name:
            shell_rc = self.home_dir / ".zshrc"
        else:
            shell_rc = self.home_dir / ".bashrc"
        
        print(f"Shell detected: {shell_name}")
        print(f"Configuration file: {shell_rc}")
        
        # Check if PATH export already exists in shell RC
        path_line = f'export PATH="{user_bin}:$PATH"'
        rc_exists = shell_rc.exists()
        already_configured = False
        
        if rc_exists:
            try:
                with open(shell_rc, 'r') as f:
                    content = f.read()
                    if str(user_bin) in content and 'PATH' in content:
                        already_configured = True
                        print("✅ PATH already configured in shell profile")
                        return
            except Exception:
                pass
        
        print()
        
        # Check if running in interactive terminal
        if sys.stdin.isatty():
            response = input("Add to PATH automatically? [Y/n]: ").strip().lower()
        else:
            print("Non-interactive session detected. Adding to PATH automatically...")
            response = 'y'
        
        if response == '' or response == 'y' or response == 'yes':
            try:
                # Create shell RC if it doesn't exist
                if not rc_exists:
                    shell_rc.touch()
                    print(f"📝 Created {shell_rc}")
                
                # Add PATH export to shell RC
                with open(shell_rc, 'a') as f:
                    f.write(f"\n# Smart Commit PATH (added by installer)\n")
                    f.write(f"{path_line}\n")
                
                print(f"✅ Added to {shell_rc}")
                print()
                print("🔄 To apply changes:")
                print(f"   source {shell_rc}")
                print("   OR restart your terminal")
                print()
                print("💡 After applying changes, you can use: smart-commit")
                
            except Exception as e:
                print(f"❌ Failed to modify {shell_rc}: {e}")
                print()
                print("📝 Manual setup required:")
                print(f"   echo '{path_line}' >> {shell_rc}")
                print(f"   source {shell_rc}")
        else:
            print("⚠️  PATH not modified. Manual setup required:")
            print(f"   echo '{path_line}' >> {shell_rc}")
            print(f"   source {shell_rc}")
    
    def print_banner(self) -> None:
        """Print installation banner."""
        print("🚀 Smart Commit v2.0 Installation")
        print("=" * 40)
        print("Professional AI-powered Git commit tool")
        print()
    
    def check_requirements(self) -> bool:
        """Check system requirements."""
        print("📋 Checking requirements...")
        
        # Check Python version
        if sys.version_info < (3, 9):
            print(f"❌ Python 3.9+ required (found {sys.version_info.major}.{sys.version_info.minor})")
            return False
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        
        # Check Git
        try:
            result = subprocess.run(
                ["git", "--version"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            print(f"✅ {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Git not found - please install Git first")
            return False
        
        # Check pip
        try:
            subprocess.run([self.python_executable, "-m", "pip", "--version"], 
                         capture_output=True, check=True)
            print("✅ pip available")
        except subprocess.CalledProcessError:
            print("❌ pip not available")
            return False
        
        return True
    
    def create_virtual_environment(self) -> bool:
        """Create virtual environment for Smart Commit."""
        print(f"🐍 Setting up virtual environment at {self.venv_path}...")
        
        try:
            # Check if venv already exists and is valid
            if self.venv_path.exists():
                venv_python = self.venv_path / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
                if venv_python.exists():
                    print("✅ Virtual environment already exists")
                    return True
                else:
                    print("🔄 Removing corrupted virtual environment...")
                    shutil.rmtree(self.venv_path)
            
            # Create new virtual environment
            self.venv_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([
                self.python_executable, "-m", "venv", str(self.venv_path)
            ], check=True)
            
            print("✅ Virtual environment created")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies."""
        print("📦 Installing dependencies...")
        
        # Get pip executable in venv
        if sys.platform == "win32":
            pip_exe = self.venv_path / "Scripts" / "pip.exe"
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            pip_exe = self.venv_path / "bin" / "pip"
            python_exe = self.venv_path / "bin" / "python"
        
        try:
            # Check if package is already installed and up to date
            try:
                result = subprocess.run([
                    str(python_exe), "-c", 
                    "import smart_commit; print(smart_commit.__version__ if hasattr(smart_commit, '__version__') else '2.0.0')"
                ], capture_output=True, text=True, check=True)
                installed_version = result.stdout.strip()
                print(f"ℹ️  Found existing installation: v{installed_version}")
                
                # Check if all required modules can be imported
                subprocess.run([
                    str(python_exe), "-c", 
                    "import smart_commit.core, smart_commit.ai_backends.factory; print('Dependencies OK')"
                ], capture_output=True, text=True, check=True)
                
                print("✅ Dependencies already installed and working")
                return True
                
            except subprocess.CalledProcessError:
                print("🔄 Installing/updating dependencies...")
            
            # Upgrade pip first
            subprocess.run([
                str(python_exe), "-m", "pip", "install", "--upgrade", "pip"
            ], check=True, capture_output=True)
            
            # Install the package in development mode
            subprocess.run([
                str(pip_exe), "install", "-e", str(self.project_root)
            ], check=True)
            
            print("✅ Dependencies installed")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def migrate_bash_config(self) -> Optional[Dict[str, Any]]:
        """Migrate configuration from bash version."""
        print("🔧 Checking for existing configuration...")
        
        # Check environment variables
        legacy_config = {}
        
        # New format
        for var in ['AI_API_URL', 'AI_MODEL', 'AI_BACKEND_TYPE']:
            value = os.environ.get(var)
            if value:
                legacy_config[var.lower()] = value
        
        # Legacy format
        for var in ['OLLAMA_API_URL', 'OLLAMA_MODEL']:
            value = os.environ.get(var)
            if value:
                new_key = var.replace('OLLAMA_', 'AI_').lower()
                if new_key not in legacy_config:
                    legacy_config[new_key] = value
        
        # Special handling for macOS optimization
        macos_local = os.environ.get('SMART_COMMIT_MACOS_LOCAL', '').lower() == 'true'
        if macos_local:
            legacy_config['macos_local_mode'] = True
        
        if legacy_config:
            print(f"✅ Found existing configuration: {list(legacy_config.keys())}")
            return legacy_config
        else:
            print("ℹ️  No existing configuration found")
            return None
    
    def create_configuration(self, legacy_config: Optional[Dict[str, Any]] = None) -> bool:
        """Create Smart Commit configuration."""
        print("⚙️  Creating configuration...")
        
        config_file = self.config_dir / "config.json"
        
        # Check if configuration already exists
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    existing_config = json.load(f)
                    # Validate basic structure
                    if all(key in existing_config for key in ['ai', 'git', 'ui', 'performance']):
                        print("✅ Configuration already exists and is valid")
                        return True
                    else:
                        print("🔄 Updating incomplete configuration...")
            except (json.JSONDecodeError, KeyError):
                print("🔄 Replacing corrupted configuration...")
        
        config_data = {
            "ai": {
                "api_url": "http://localhost:11434",
                "model": "qwen3:8b", 
                "backend_type": "auto",
                "timeout": 120,
                "max_retries": 3
            },
            "git": {
                "auto_stage": True,
                "auto_push": True,
                "max_diff_lines": 500,
                "atomic_mode": False
            },
            "ui": {
                "use_colors": True,
                "show_progress": True,
                "interactive": True,
                "log_level": "INFO"
            },
            "performance": {
                "enable_optimization": True,
                "macos_local_mode": False,
                "character_limit": 90
            }
        }
        
        # Apply legacy configuration
        if legacy_config:
            if 'ai_api_url' in legacy_config:
                config_data["ai"]["api_url"] = legacy_config['ai_api_url']
            if 'ai_model' in legacy_config:
                config_data["ai"]["model"] = legacy_config['ai_model']
            if 'ai_backend_type' in legacy_config:
                config_data["ai"]["backend_type"] = legacy_config['ai_backend_type']
            if 'macos_local_mode' in legacy_config:
                config_data["performance"]["macos_local_mode"] = legacy_config['macos_local_mode']
        
        # Save configuration
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"✅ Configuration saved to {config_file}")
        return True
    
    def create_shell_scripts(self) -> bool:
        """Create shell integration scripts."""
        print("🔗 Creating shell integration...")
        
        # Get Python executable in venv
        if sys.platform == "win32":
            python_exe = self.venv_path / "Scripts" / "python.exe"
            script_ext = ".bat"
        else:
            python_exe = self.venv_path / "bin" / "python"
            script_ext = ""
        
        # Install to user bin
        user_bin = self.home_dir / ".local" / "bin"
        user_bin.mkdir(parents=True, exist_ok=True)
        
        script_path = user_bin / f"smart-commit{script_ext}"
        
        # Check if script already exists and is up to date
        script_needs_update = True
        if script_path.exists():
            try:
                with open(script_path, 'r') as f:
                    existing_content = f.read()
                    if str(python_exe) in existing_content and "smart_commit.cli" in existing_content:
                        print(f"✅ Shell script already exists and is current")
                        script_needs_update = False
                    else:
                        print("🔄 Updating shell script...")
            except Exception:
                print("🔄 Replacing corrupted shell script...")
        
        # Create or update script if needed
        if script_needs_update:
            script_content = f"""#!/usr/bin/env bash
# Smart Commit v2.0 - Python edition
exec "{python_exe}" -m smart_commit.cli "$@"
"""
            
            try:
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                if sys.platform != "win32":
                    script_path.chmod(0o755)
                
                print(f"✅ Created {script_path}")
                
            except Exception as e:
                print(f"❌ Failed to create shell script: {e}")
                return False
        
        # Always check PATH setup (handles idempotency internally)
        try:
            self._handle_path_setup(user_bin)
        except Exception as e:
            print(f"⚠️  PATH setup failed: {e}")
            print("You can manually add to PATH later.")
        
        return True
    
    def test_installation(self) -> bool:
        """Test the installation."""
        print("🧪 Testing installation...")
        
        # Get Python executable in venv
        if sys.platform == "win32":
            python_exe = self.venv_path / "Scripts" / "python.exe"
        else:
            python_exe = self.venv_path / "bin" / "python"
        
        try:
            # Test import
            result = subprocess.run([
                str(python_exe), "-c", "import smart_commit; print('✅ Import successful')"
            ], capture_output=True, text=True, check=True)
            print(result.stdout.strip())
            
            # Test CLI
            result = subprocess.run([
                str(python_exe), "-m", "smart_commit.cli", "--help"
            ], capture_output=True, text=True, check=True)
            print("✅ CLI test successful")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Installation test failed: {e}")
            if e.stdout:
                print(f"stdout: {e.stdout}")
            if e.stderr:
                print(f"stderr: {e.stderr}")
            return False
    
    def show_completion_info(self) -> None:
        """Show installation completion information."""
        print()
        print("🎉 Smart Commit v2.0 Installation Complete!")
        print("=" * 45)
        print()
        print("📋 What's new in v2.0:")
        print("  • Professional Python architecture")
        print("  • Beautiful Rich-based UI with progress bars")
        print("  • Improved AI backend abstraction")
        print("  • Comprehensive configuration system")
        print("  • Better error handling and logging")
        print("  • Professional CLI with Typer")
        print()
        print("🚀 Quick start:")
        print("  smart-commit                           # Standard workflow")
        print("  smart-commit --atomic                  # Atomic commits")
        print("  smart-commit --dry-run                 # Preview mode")
        print("  smart-commit config --show             # Show configuration")
        print("  smart-commit test                      # Test AI backend")
        print()
        print("📚 Configuration file:")
        print(f"  {self.config_dir / 'config.json'}")
        print()
        print("🔧 For help: smart-commit --help")
    
    def run_installation(self) -> bool:
        """Run the complete installation process."""
        self.print_banner()
        
        if not self.check_requirements():
            return False
        
        if not self.create_virtual_environment():
            return False
        
        if not self.install_dependencies():
            return False
        
        legacy_config = self.migrate_bash_config()
        
        if not self.create_configuration(legacy_config):
            return False
        
        if not self.create_shell_scripts():
            return False
        
        if not self.test_installation():
            return False
        
        self.show_completion_info()
        return True


def main():
    """Main installation entry point."""
    installer = SmartCommitInstaller()
    
    try:
        success = installer.run_installation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Installation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Installation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()