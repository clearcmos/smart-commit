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
import platform
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import urllib.request
from urllib.parse import urlparse
from urllib.error import URLError, HTTPError


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
                    # Check if smart-commit PATH is already properly configured
                    if str(user_bin) in content and 'PATH' in content:
                        # Verify it's not being overridden by checking line order
                        lines = content.split('\n')
                        smart_commit_line = -1
                        path_override_line = -1
                        
                        for i, line in enumerate(lines):
                            if str(user_bin) in line and 'PATH' in line:
                                smart_commit_line = i
                            # Check for common PATH overrides that might come after
                            if ('export PATH=' in line and 'npm-global' in line) or \
                               ('export PATH=' in line and 'nvm/versions' in line) or \
                               (line.strip().startswith('export PATH=') and user_bin not in line and len(line.split(':')) > 3):
                                path_override_line = max(path_override_line, i)
                        
                        # If smart-commit PATH comes after overrides, it's properly configured
                        if smart_commit_line > path_override_line:
                            already_configured = True
                            print("✅ PATH already configured in shell profile")
                            return
                        elif smart_commit_line >= 0:
                            print("🔄 Smart Commit PATH found but may be overridden, fixing...")
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
                    # Simple append for new files
                    with open(shell_rc, 'a') as f:
                        f.write(f"\n# Smart Commit PATH (added by installer)\n")
                        f.write(f"{path_line}\n")
                else:
                    # For existing files, intelligently place the PATH export
                    self._smart_path_insertion(shell_rc, user_bin, path_line)
                
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

    def _smart_path_insertion(self, shell_rc: Path, user_bin: Path, path_line: str) -> None:
        """Intelligently insert PATH configuration after other PATH-modifying sections."""
        with open(shell_rc, 'r') as f:
            lines = f.readlines()
        
        # Remove any existing smart-commit PATH lines
        filtered_lines = []
        for line in lines:
            if 'Smart Commit PATH' in line or (str(user_bin) in line and 'PATH' in line and 'export' in line):
                continue
            filtered_lines.append(line)
        
        # Find the best insertion point (after NVM, npm, or other PATH modifications)
        insertion_point = len(filtered_lines)
        
        # Look for common PATH-modifying sections
        for i, line in enumerate(filtered_lines):
            # After NVM setup
            if 'nvm/versions/node' in line or 'npm-global' in line:
                insertion_point = max(insertion_point, i + 1)
            # After large PATH exports
            elif line.strip().startswith('export PATH=') and len(line.split(':')) > 5:
                insertion_point = max(insertion_point, i + 1)
            # After sourcing NVM
            elif 'nvm.sh' in line or 'bash_completion' in line:
                insertion_point = max(insertion_point, i + 1)
            # After any PATH export (like cursor)
            elif line.strip().startswith('export PATH=') and '$PATH' in line:
                insertion_point = max(insertion_point, i + 1)
        
        # Insert the smart-commit PATH configuration
        new_lines = (
            filtered_lines[:insertion_point] +
            ["\n", "# Smart Commit PATH (added by installer)\n", f"{path_line}\n"] +
            filtered_lines[insertion_point:]
        )
        
        # Write back to file
        with open(shell_rc, 'w') as f:
            f.writelines(new_lines)
    
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
    
    def detect_platform(self) -> str:
        """Detect the current platform."""
        system = platform.system().lower()
        if system == "darwin":
            return "macos"
        elif system == "linux":
            return "linux"
        elif system == "windows":
            return "windows"
        else:
            print(f"❌ Unsupported platform: {system}")
            sys.exit(1)
    
    def get_shell_profile(self) -> Path:
        """Get the appropriate shell profile file."""
        shell = os.environ.get('SHELL', '/bin/bash')
        if 'zsh' in shell or platform.system() == "Darwin":
            return self.home_dir / ".zshrc"
        else:
            return self.home_dir / ".bashrc"
    
    def check_url_reachable(self, url: str, timeout: int = 10) -> bool:
        """Check if a URL is reachable."""
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return response.status == 200
        except (URLError, HTTPError):
            return False
    
    def validate_ip_address(self, ip: str) -> bool:
        """Validate IP address format."""
        pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        return bool(re.match(pattern, ip))
    
    def check_ollama_installed(self) -> bool:
        """Check if Ollama is installed."""
        try:
            subprocess.run(["ollama", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama service is running."""
        return self.check_url_reachable("http://localhost:11434/api/tags", 5)
    
    def check_llamacpp_running(self) -> Optional[int]:
        """Check if llama.cpp server is running on common ports."""
        for port in [8080, 8000, 3000]:
            if self.check_url_reachable(f"http://localhost:{port}/health", 3):
                return port
        return None
    
    def get_llamacpp_model(self, port: int) -> Optional[str]:
        """Get model information from llama.cpp server."""
        try:
            with urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=5) as response:
                data = json.loads(response.read().decode())
                if 'data' in data and len(data['data']) > 0:
                    return data['data'][0]['id']
        except (URLError, HTTPError, json.JSONDecodeError, KeyError):
            pass
        return None
    
    def install_ollama_macos(self) -> bool:
        """Install Ollama on macOS."""
        print("🔽 Installing Ollama...")
        
        # Check if Homebrew is available
        try:
            subprocess.run(["brew", "--version"], capture_output=True, check=True)
            print("📦 Installing Ollama via Homebrew...")
            result = subprocess.run(["brew", "install", "ollama"], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"⚠️  Homebrew installation failed: {result.stderr}")
                return self._install_ollama_curl()
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("📦 Homebrew not found, using curl installer...")
            return self._install_ollama_curl()
        
        return self.check_ollama_installed()
    
    def _install_ollama_curl(self) -> bool:
        """Install Ollama using curl script."""
        try:
            print("📦 Installing Ollama via curl...")
            result = subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # Run the install script
                subprocess.run(["sh"], input=result.stdout, text=True, check=True)
                return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Ollama: {e}")
        return False
    
    def start_ollama_service(self) -> bool:
        """Start Ollama service."""
        print("🚀 Starting Ollama service...")
        
        try:
            # Start Ollama in background
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for service to be ready
            for attempt in range(10):
                time.sleep(2)
                if self.check_ollama_running():
                    print("✅ Ollama service is running!")
                    return True
                print(f"⏳ Waiting for Ollama service... ({attempt + 1}/10)")
            
            print("❌ Failed to start Ollama service")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start Ollama: {e}")
            return False
    
    def download_model(self, model: str) -> bool:
        """Download Ollama model."""
        print(f"📥 Downloading {model} model (this may take several minutes)...")
        
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=True, text=True, timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode == 0:
                print(f"✅ {model} model downloaded successfully!")
                return True
            else:
                print(f"❌ Failed to download {model}: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"❌ Model download timed out")
            return False
        except Exception as e:
            print(f"❌ Error downloading model: {e}")
            return False
    
    def interactive_setup(self) -> Optional[Dict[str, Any]]:
        """Run interactive AI backend setup."""
        platform_type = self.detect_platform()
        
        print()
        print("🤖 AI Backend Configuration")
        print("===========================")
        
        # Show current configuration if any
        existing_config = self.migrate_bash_config()
        if existing_config:
            print("\n📋 Current Configuration:")
            for key, value in existing_config.items():
                print(f"  {key}: {value}")
        else:
            print("\nℹ️  No existing configuration found")
        
        print("\nChoose your AI backend setup:")
        
        if platform_type == "macos":
            print("1) Local Ollama (install and run locally) [Recommended]")
        elif platform_type == "linux":
            print("1) Local AI (detect existing llama.cpp installation)")
        
        print("2) Remote AI server (Windows Ollama or Linux llama.cpp)")
        
        if existing_config:
            print("3) Keep current configuration")
            max_choice = 3
        else:
            max_choice = 2
        
        print()
        
        while True:
            try:
                choice = input(f"Enter your choice (1-{max_choice}): ").strip()
                choice_num = int(choice)
                if 1 <= choice_num <= max_choice:
                    break
                else:
                    print(f"❌ Please enter a number between 1 and {max_choice}")
            except ValueError:
                print("❌ Please enter a valid number")
        
        if choice_num == 1:
            if platform_type == "macos":
                return self._setup_local_macos_ollama()
            elif platform_type == "linux":
                return self._setup_local_linux_llamacpp()
        elif choice_num == 2:
            return self._setup_remote_server()
        elif choice_num == 3 and existing_config:
            print("✅ Keeping current configuration")
            return existing_config
        
        return None
    
    def _setup_local_macos_ollama(self) -> Dict[str, Any]:
        """Setup local Ollama on macOS."""
        print("\n🍎 Setting up Local Ollama on macOS...")
        
        # Check/install Ollama
        if self.check_ollama_installed():
            print("✅ Ollama is already installed")
        else:
            if not self.install_ollama_macos():
                print("❌ Failed to install Ollama")
                sys.exit(1)
        
        # Check/start service
        if self.check_ollama_running():
            print("✅ Ollama service is already running")
        else:
            if not self.start_ollama_service():
                print("❌ Failed to start Ollama service")
                sys.exit(1)
        
        # Download model
        model = "qwen3:8b"
        if not self.download_model(model):
            print("❌ Failed to download model")
            sys.exit(1)
        
        config = {
            "ai_api_url": "http://localhost:11434",
            "ai_model": model,
            "ai_backend_type": "ollama",
            "macos_local_mode": True
        }
        
        print(f"\n✅ Local macOS Ollama setup complete!")
        print(f"   API URL: {config['ai_api_url']}")
        print(f"   Model: {config['ai_model']}")
        print(f"   Backend: {config['ai_backend_type']}")
        print(f"   macOS Optimization: Enabled")
        
        return config
    
    def _setup_local_linux_llamacpp(self) -> Optional[Dict[str, Any]]:
        """Setup local llama.cpp on Linux (detect existing)."""
        print("\n🐧 Setting up Local AI on Linux...")
        print("\n⚠️  WARNING: Linux local deployment is partially implemented")
        print("   This will detect and use your existing llama.cpp installation")
        print("   Full automated deployment is not yet available for Linux\n")
        
        # Probe for llama.cpp
        port = self.check_llamacpp_running()
        if port:
            print(f"✅ Found llama.cpp server running on port {port}")
            
            model = self.get_llamacpp_model(port)
            if model and model != "null":
                print(f"✅ Detected model: {model}")
            else:
                model = "auto-detected"
                print("⚠️  Could not detect specific model, will use auto-detection")
            
            config = {
                "ai_api_url": f"http://localhost:{port}",
                "ai_model": model,
                "ai_backend_type": "llamacpp"
            }
            
            print(f"\n✅ Local Linux llama.cpp setup complete!")
            print(f"   API URL: {config['ai_api_url']}")
            print(f"   Model: {config['ai_model']}")
            print(f"   Backend: {config['ai_backend_type']}")
            
            return config
        else:
            print("❌ No existing llama.cpp installation detected")
            print("\nTo set up llama.cpp locally, you would need to:")
            print("1. Install llama.cpp from https://github.com/ggerganov/llama.cpp")
            print("2. Download a compatible model (e.g., Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf)")
            print("3. Start llama-server with appropriate parameters")
            print("\n💡 Please choose option 2 (Remote AI server) instead.")
            return None
    
    def _setup_remote_server(self) -> Optional[Dict[str, Any]]:
        """Setup remote AI server."""
        print("\n🌐 Setting up Remote AI server...")
        print("\nChoose your remote server type:")
        print("1) Windows Ollama server (existing setup)")
        print("2) Linux llama.cpp server (new setup)")
        
        while True:
            try:
                choice = input("Enter your choice (1-2): ").strip()
                choice_num = int(choice)
                if choice_num in [1, 2]:
                    break
                else:
                    print("❌ Please enter 1 or 2")
            except ValueError:
                print("❌ Please enter a valid number")
        
        if choice_num == 1:
            return self._setup_remote_ollama()
        else:
            return self._setup_remote_llamacpp()
    
    def _setup_remote_ollama(self) -> Dict[str, Any]:
        """Setup remote Ollama server."""
        print("\n🪟 Setting up Remote Windows Ollama server...")
        
        while True:
            ip = input("Enter the IP address of your Windows Ollama server (e.g., 192.168.1.2): ").strip()
            if self.validate_ip_address(ip):
                break
            else:
                print("❌ Invalid IP address format. Please try again.")
        
        api_url = f"http://{ip}:11434"
        model = "qwen3:8b"
        
        print(f"\n🔍 Testing connection to {api_url}...")
        if self.check_url_reachable(f"{api_url}/api/tags", 10):
            print("✅ Successfully connected to remote Ollama server")
        else:
            print("⚠️  Warning: Could not connect to remote server")
            print("   (This is normal if the server is not running yet)")
        
        config = {
            "ai_api_url": api_url,
            "ai_model": model,
            "ai_backend_type": "ollama"
        }
        
        print(f"\n✅ Remote Windows Ollama setup complete!")
        print(f"   API URL: {config['ai_api_url']}")
        print(f"   Model: {config['ai_model']}")
        print(f"   Backend: {config['ai_backend_type']}")
        
        return config
    
    def _setup_remote_llamacpp(self) -> Dict[str, Any]:
        """Setup remote llama.cpp server."""
        print("\n🐧 Setting up Remote Linux llama.cpp server...")
        
        while True:
            ip = input("Enter the IP address of your Linux llama.cpp server (e.g., 192.168.1.3): ").strip()
            if self.validate_ip_address(ip):
                break
            else:
                print("❌ Invalid IP address format. Please try again.")
        
        port = input("Enter the port (default: 8080): ").strip() or "8080"
        api_url = f"http://{ip}:{port}"
        
        print(f"\n🔍 Testing connection to {api_url}...")
        if self.check_url_reachable(f"{api_url}/health", 10):
            print("✅ Successfully connected to remote llama.cpp server")
            
            # Try to detect model
            try:
                with urllib.request.urlopen(f"{api_url}/v1/models", timeout=5) as response:
                    data = json.loads(response.read().decode())
                    if 'data' in data and len(data['data']) > 0:
                        model = data['data'][0]['id']
                        print(f"✅ Detected model: {model}")
                    else:
                        model = "auto-detected"
            except:
                model = "auto-detected"
        else:
            print("⚠️  Warning: Could not connect to remote server")
            print("   (This is normal if the server is not running yet)")
            model = "auto-detected"
        
        config = {
            "ai_api_url": api_url,
            "ai_model": model,
            "ai_backend_type": "llamacpp"
        }
        
        print(f"\n✅ Remote Linux llama.cpp setup complete!")
        print(f"   API URL: {config['ai_api_url']}")
        print(f"   Model: {config['ai_model']}")
        print(f"   Backend: {config['ai_backend_type']}")
        
        return config

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
                        # Still update environment variables if needed
                        self._update_shell_environment(legacy_config)
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
                "truncation_threshold": 1000,
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
        
        # Update shell environment variables
        self._update_shell_environment(legacy_config)
        
        return True
    
    def _update_shell_environment(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Update shell environment variables to match configuration."""
        if not config:
            return
        
        print("🔧 Updating shell environment variables...")
        
        # Detect shell and shell RC file
        shell_name = os.environ.get('SHELL', '/bin/bash').split('/')[-1]
        if shell_name == 'zsh' or 'zsh' in shell_name:
            shell_rc = self.home_dir / ".zshrc"
        else:
            shell_rc = self.home_dir / ".bashrc"
        
        if not shell_rc.exists():
            print(f"⚠️  Shell RC file {shell_rc} not found, skipping environment update")
            return
        
        try:
            # Read current shell RC content
            with open(shell_rc, 'r') as f:
                content = f.read()
            
            # Remove old environment variable exports
            lines = content.split('\n')
            filtered_lines = []
            
            for line in lines:
                # Skip lines with old environment variables
                if any(var in line for var in ['OLLAMA_API_URL', 'OLLAMA_MODEL', 'SMART_COMMIT_MACOS_LOCAL']):
                    continue
                # Skip lines with old AI environment variables
                if any(var in line for var in ['AI_API_URL', 'AI_MODEL', 'AI_BACKEND_TYPE']):
                    continue
                filtered_lines.append(line)
            
            # Add new environment variable exports
            new_exports = []
            
            # Add comment header
            new_exports.append("")
            new_exports.append("# Smart Commit v2.0 Environment Variables")
            new_exports.append("# Auto-configured by installer")
            
            # Add new environment variables based on configuration
            if 'ai_api_url' in config:
                new_exports.append(f'export AI_API_URL="{config["ai_api_url"]}"')
            if 'ai_model' in config:
                new_exports.append(f'export AI_MODEL="{config["ai_model"]}"')
            if 'ai_backend_type' in config:
                new_exports.append(f'export AI_BACKEND_TYPE="{config["ai_backend_type"]}"')
            if 'macos_local_mode' in config:
                new_exports.append(f'export SMART_COMMIT_MACOS_LOCAL="{str(config["macos_local_mode"]).lower()}"')
            
            # Add footer comment
            new_exports.append("")
            
            # Combine content
            updated_content = '\n'.join(filtered_lines + new_exports)
            
            # Write updated content back to shell RC
            with open(shell_rc, 'w') as f:
                f.write(updated_content)
            
            print(f"✅ Updated environment variables in {shell_rc}")
            print("   Note: You may need to restart your terminal or run 'source ~/.zshrc' for changes to take effect")
            
        except Exception as e:
            print(f"⚠️  Failed to update shell environment: {e}")
            print("   You may need to manually update your shell configuration")
    
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
        print("🔧 Environment Variables:")
        print("  ✅ Shell environment variables have been updated")
        print("  📝 To apply changes immediately, run: source ~/.zshrc")
        print("  🔄 Or restart your terminal for permanent changes")
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
        
        # Run interactive setup if no existing config and in interactive mode
        legacy_config = self.migrate_bash_config()
        if not legacy_config and sys.stdin.isatty():
            print("\n🔧 No existing configuration found - starting interactive setup...")
            interactive_config = self.interactive_setup()
            if not interactive_config:
                print("❌ Configuration setup failed")
                return False
            legacy_config = interactive_config
        elif not legacy_config:
            # Non-interactive mode, create default config
            print("\nℹ️  No existing configuration found - creating default configuration")
            print("   You can reconfigure later using: smart-commit config")
            legacy_config = {
                "ai_api_url": "http://localhost:11434",
                "ai_model": "qwen3:8b",
                "ai_backend_type": "auto"
            }
        else:
            print(f"✅ Found existing configuration: {list(legacy_config.keys())}")
            
            # Ask if user wants to reconfigure (only in interactive mode)
            if sys.stdin.isatty():
                reconfigure = input("\nDo you want to reconfigure the AI backend? [y/N]: ").strip().lower()
                if reconfigure in ['y', 'yes']:
                    print("\n🔧 Starting interactive reconfiguration...")
                    interactive_config = self.interactive_setup()
                    if interactive_config:
                        legacy_config = interactive_config
        
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