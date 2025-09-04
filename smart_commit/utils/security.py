"""
Security utilities for scanning repositories before commits.
"""

import asyncio
import subprocess
import shutil
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger


class SecurityScanner:
    """Handles security scanning of repositories before commits."""
    
    def __init__(self):
        self.trufflehog_available = shutil.which("trufflehog") is not None
        
    async def scan_before_commit(self, repo_path: Path, staged_files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Scan repository for secrets before committing.
        
        Args:
            repo_path: Path to git repository
            staged_files: List of staged files to scan (if None, scan all)
            
        Returns:
            Dict with scan results and whether commit should proceed
        """
        result = {
            "scanner_available": self.trufflehog_available,
            "secrets_found": False,
            "should_block_commit": False,
            "findings": [],
            "scan_performed": False
        }
        
        if not self.trufflehog_available:
            logger.debug("TruffleHog not available, skipping security scan")
            return result
        
        try:
            # Scan only staged files if provided, otherwise scan whole repo
            if staged_files:
                scan_result = await self._scan_staged_files(repo_path, staged_files)
            else:
                scan_result = await self._scan_repository(repo_path)
            
            result.update(scan_result)
            result["scan_performed"] = True
            
            if result["secrets_found"]:
                logger.warning(f"Security scan found {len(result['findings'])} potential secrets")
            else:
                logger.info("Security scan completed - no secrets detected")
                
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            # Don't block commit on scanner errors
            
        return result
    
    async def _scan_repository(self, repo_path: Path) -> Dict[str, Any]:
        """Scan entire repository filesystem."""
        try:
            cmd = ["trufflehog", "filesystem", str(repo_path), "--json", "--no-verification"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=repo_path
            )
            
            stdout, stderr = await process.communicate()
            
            return self._parse_trufflehog_output(stdout.decode(), stderr.decode())
            
        except Exception as e:
            logger.error(f"Repository scan failed: {e}")
            return {"secrets_found": False, "should_block_commit": False, "findings": []}
    
    async def _scan_staged_files(self, repo_path: Path, staged_files: List[str]) -> Dict[str, Any]:
        """Scan only staged files for secrets."""
        findings = []
        
        for file_path in staged_files:
            full_path = repo_path / file_path
            if not full_path.exists():
                continue
                
            try:
                cmd = ["trufflehog", "filesystem", str(full_path), "--json", "--no-verification"]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=repo_path
                )
                
                stdout, stderr = await process.communicate()
                file_result = self._parse_trufflehog_output(stdout.decode(), stderr.decode())
                findings.extend(file_result["findings"])
                
            except Exception as e:
                logger.debug(f"Failed to scan {file_path}: {e}")
        
        return {
            "secrets_found": len(findings) > 0,
            "should_block_commit": len(findings) > 0,
            "findings": findings
        }
    
    def _parse_trufflehog_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse TruffleHog JSON output."""
        findings = []
        
        if stderr:
            logger.debug(f"TruffleHog stderr: {stderr}")
        
        for line in stdout.strip().split('\n'):
            if not line:
                continue
                
            try:
                finding = json.loads(line)
                
                # Extract key information
                findings.append({
                    "detector": finding.get("DetectorName", "unknown"),
                    "file": finding.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("file", "unknown"),
                    "line": finding.get("SourceMetadata", {}).get("Data", {}).get("Filesystem", {}).get("line", 0),
                    "verified": finding.get("Verified", False),
                    "raw": finding.get("Raw", "")[:100] + "..." if len(finding.get("Raw", "")) > 100 else finding.get("Raw", "")
                })
                
            except json.JSONDecodeError:
                logger.debug(f"Could not parse TruffleHog line: {line}")
                
        return {
            "secrets_found": len(findings) > 0,
            "should_block_commit": len(findings) > 0,
            "findings": findings
        }