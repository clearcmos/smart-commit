#!/usr/bin/env python3
"""Test script to verify duplicate commit fixes."""

import subprocess
import tempfile
import shutil
from pathlib import Path

def run_command(cmd):
    """Run a shell command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def test_duplicate_fix():
    """Test that smart-commit doesn't create duplicate commits."""
    
    # Create a temporary git repo for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        print(f"Creating test repository in {repo_path}")
        
        # Initialize git repo
        run_command(f"cd {repo_path} && git init")
        run_command(f"cd {repo_path} && git config user.name 'Test User'")
        run_command(f"cd {repo_path} && git config user.email 'test@example.com'")
        
        # Create initial commit
        (repo_path / "README.md").write_text("# Test Project\n")
        run_command(f"cd {repo_path} && git add README.md")
        run_command(f"cd {repo_path} && git commit -m 'Initial commit'")
        
        # Create multiple files with different states
        print("\nCreating test files...")
        
        # File 1: Modified file
        (repo_path / "file1.txt").write_text("Original content")
        run_command(f"cd {repo_path} && git add file1.txt")
        run_command(f"cd {repo_path} && git commit -m 'Add file1'")
        (repo_path / "file1.txt").write_text("Modified content")
        
        # File 2: New file (untracked)
        (repo_path / "file2.txt").write_text("New file content")
        
        # File 3: Staged modification
        (repo_path / "file3.txt").write_text("Original file3")
        run_command(f"cd {repo_path} && git add file3.txt")
        run_command(f"cd {repo_path} && git commit -m 'Add file3'")
        (repo_path / "file3.txt").write_text("Modified file3")
        run_command(f"cd {repo_path} && git add file3.txt")
        
        # File 4: Staged then modified again (should only appear once)
        (repo_path / "file4.txt").write_text("Original file4")
        run_command(f"cd {repo_path} && git add file4.txt")
        run_command(f"cd {repo_path} && git commit -m 'Add file4'")
        (repo_path / "file4.txt").write_text("First modification")
        run_command(f"cd {repo_path} && git add file4.txt")
        (repo_path / "file4.txt").write_text("Second modification")
        
        # Check git status
        print("\nGit status before smart-commit:")
        _, status, _ = run_command(f"cd {repo_path} && git status --porcelain")
        print(status)
        
        # Parse the status to understand what we expect
        status_lines = [l.strip() for l in status.split('\n') if l.strip()]
        print(f"\nFound {len(status_lines)} status lines")
        
        # Count unique files
        unique_files = set()
        for line in status_lines:
            if len(line) > 3:
                file_path = line[3:].strip()
                unique_files.add(file_path)
        
        print(f"Unique files with changes: {unique_files}")
        print(f"Total unique files: {len(unique_files)}")
        
        # Now let's simulate what smart-commit would see
        print("\n" + "="*50)
        print("SIMULATING SMART-COMMIT FILE DETECTION")
        print("="*50)
        
        # Test the git status parsing logic
        seen_files = set()
        files_to_process = []
        
        for line in status_lines:
            if len(line) < 3:
                continue
            
            staged_status = line[0]
            unstaged_status = line[1]  
            file_path = line[3:]  # No strip needed, git status already has clean format
            
            print(f"\nProcessing: '{line}'")
            print(f"  Staged: '{staged_status}', Unstaged: '{unstaged_status}', File: '{file_path}'")
            
            if file_path in seen_files:
                print(f"  ⚠️  DUPLICATE DETECTED - Skipping!")
                continue
            
            if staged_status in ['A', 'M', 'D', 'R', 'C']:
                files_to_process.append(file_path)
                seen_files.add(file_path)
                print(f"  ✅ Added to process list (staged change)")
            elif unstaged_status == '?' and file_path not in seen_files:
                files_to_process.append(file_path)
                seen_files.add(file_path)
                print(f"  ✅ Added to process list (untracked)")
            elif unstaged_status in ['M', 'D'] and file_path not in seen_files:
                files_to_process.append(file_path)
                seen_files.add(file_path)
                print(f"  ✅ Added to process list (unstaged change)")
        
        print(f"\n" + "="*50)
        print(f"RESULTS:")
        print(f"  Files to process: {files_to_process}")
        print(f"  Total files: {len(files_to_process)}")
        print(f"  Expected: {len(unique_files)}")
        
        if len(files_to_process) == len(unique_files):
            print("  ✅ SUCCESS: No duplicates detected!")
        else:
            print(f"  ❌ FAILURE: Count mismatch!")
            missing = unique_files - set(files_to_process)
            extra = set(files_to_process) - unique_files
            if missing:
                print(f"  Missing files: {missing}")
            if extra:
                print(f"  Extra files: {extra}")

if __name__ == "__main__":
    test_duplicate_fix()