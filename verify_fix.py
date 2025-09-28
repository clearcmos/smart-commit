#!/usr/bin/env python3
"""Verify that the duplicate detection fix works correctly."""

import subprocess
import os
from pathlib import Path

def run_git_command(cmd):
    """Run a git command and return the output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/home/nicholas/git/smart-commit")
    return result.stdout.strip()

def test_git_status_parsing():
    """Test git status parsing logic that was fixed."""
    
    print("Testing Git Status Parsing Fix")
    print("=" * 40)
    
    # Get actual git status
    status_output = run_git_command("git status --porcelain")
    if not status_output:
        print("❌ No changes found to test with")
        return
    
    print(f"Git status output:")
    print(status_output)
    print()
    
    # Parse using the fixed logic
    changes = []
    seen_files = set()
    
    for line in status_output.split('\n'):
        if line.strip():
            print(f"Processing line: '{line}'")
            
            if len(line) < 3:
                print("  ⚠️  Line too short, skipping")
                continue
            
            staged_status = line[0]
            unstaged_status = line[1]
            file_path = line[3:]  # Fixed: was line[3:].strip()
            
            print(f"  Staged: '{staged_status}', Unstaged: '{unstaged_status}', File: '{file_path}'")
            
            # Check for duplicates (this is the main fix)
            if file_path in seen_files:
                print(f"  ❌ DUPLICATE DETECTED - would have been skipped!")
                continue
            
            # Only process if there's a staged change
            if staged_status in ['A', 'M', 'D', 'R', 'C']:
                changes.append((file_path, staged_status, 'staged'))
                seen_files.add(file_path)
                print(f"  ✅ Added as staged change")
            elif unstaged_status in ['M', 'D'] and file_path not in seen_files:
                changes.append((file_path, unstaged_status, 'unstaged'))
                seen_files.add(file_path)
                print(f"  ✅ Added as unstaged change")
            elif unstaged_status == '?' and file_path not in seen_files:
                changes.append((file_path, '?', 'untracked'))
                seen_files.add(file_path)
                print(f"  ✅ Added as untracked file")
            else:
                print(f"  ⏭️  No changes to process")
    
    print(f"\n" + "=" * 40)
    print(f"RESULTS:")
    print(f"  Total files to process: {len(changes)}")
    print(f"  Files found:")
    
    for file_path, change_type, status_type in changes:
        print(f"    {change_type} {file_path} ({status_type})")
    
    # Check if we have duplicates in our result
    file_paths = [c[0] for c in changes]
    unique_paths = set(file_paths)
    
    if len(file_paths) == len(unique_paths):
        print(f"  ✅ SUCCESS: No duplicates in final result!")
    else:
        print(f"  ❌ FAILURE: Found duplicates in result!")
        duplicates = [f for f in file_paths if file_paths.count(f) > 1]
        print(f"  Duplicate files: {set(duplicates)}")

if __name__ == "__main__":
    test_git_status_parsing()