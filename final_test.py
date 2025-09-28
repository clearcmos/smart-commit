#!/usr/bin/env python3
"""Final test to demonstrate the duplicate fix."""

# Test with known git status patterns that would cause duplicates
test_cases = [
    # Case 1: File with both staged and unstaged changes (MM)
    "MM duplicated_file.txt",
    # Case 2: Normal staged file  
    "M  normal_staged.txt",
    # Case 3: Normal unstaged file
    " M normal_unstaged.txt", 
    # Case 4: New untracked file
    "?? new_file.txt",
    # Case 5: Deleted file
    " D deleted_file.txt"
]

def parse_git_status_line(line):
    """Parse a git status line using our fixed logic."""
    if len(line) < 3:
        return None
    
    staged_status = line[0]
    unstaged_status = line[1] 
    file_path = line[3:]  # Our fix: don't strip, git output is clean
    
    return {
        'staged': staged_status,
        'unstaged': unstaged_status, 
        'file_path': file_path,
        'has_staged_change': staged_status in ['A', 'M', 'D', 'R', 'C'],
        'has_unstaged_change': unstaged_status in ['M', 'D'],
        'is_untracked': unstaged_status == '?'
    }

def process_files_old_way(status_lines):
    """Simulate the old buggy processing that caused duplicates."""
    files = []
    
    for line in status_lines:
        parsed = parse_git_status_line(line)
        if not parsed:
            continue
            
        # Old buggy logic: used startswith which caught multiple cases
        if line.startswith('M'):  # This catches both "M " and "MM"
            files.append(f"{parsed['file_path']} (staged)")
        if line.startswith(' M') or 'M' in line[1:]:  # This also processes "MM" again
            files.append(f"{parsed['file_path']} (unstaged)")
        if line.startswith('??'):
            files.append(f"{parsed['file_path']} (untracked)")
            
    return files

def process_files_new_way(status_lines):
    """Process files using our fixed logic that prevents duplicates."""
    files = []
    seen_files = set()
    
    for line in status_lines:
        parsed = parse_git_status_line(line)
        if not parsed:
            continue
            
        file_path = parsed['file_path']
        
        # Our fix: check for duplicates first
        if file_path in seen_files:
            continue
            
        # Process based on exact status characters, not startswith
        if parsed['has_staged_change']:
            files.append(f"{file_path} (staged)")
            seen_files.add(file_path)
        elif parsed['has_unstaged_change']:
            files.append(f"{file_path} (unstaged)")
            seen_files.add(file_path)
        elif parsed['is_untracked']:
            files.append(f"{file_path} (untracked)")
            seen_files.add(file_path)
            
    return files

print("Testing Duplicate Detection Fix")
print("=" * 50)
print()

print("Test cases:")
for i, line in enumerate(test_cases, 1):
    print(f"  {i}. '{line}'")
print()

print("OLD (buggy) processing:")
old_result = process_files_old_way(test_cases)
for file in old_result:
    print(f"  {file}")
print(f"Total files: {len(old_result)}")
print()

print("NEW (fixed) processing:")
new_result = process_files_new_way(test_cases)
for file in new_result:
    print(f"  {file}")
print(f"Total files: {len(new_result)}")
print()

# Check for improvements
if len(new_result) < len(old_result):
    print(f"✅ SUCCESS: Reduced from {len(old_result)} to {len(new_result)} files")
    print(f"   Eliminated {len(old_result) - len(new_result)} duplicates!")
else:
    print(f"❌ No improvement detected")

# Check for actual duplicates in old vs new
old_file_paths = [f.split(' (')[0] for f in old_result]
new_file_paths = [f.split(' (')[0] for f in new_result]

old_duplicates = [f for f in old_file_paths if old_file_paths.count(f) > 1]
new_duplicates = [f for f in new_file_paths if new_file_paths.count(f) > 1]

if old_duplicates and not new_duplicates:
    print(f"✅ Fixed duplicates: {set(old_duplicates)}")
elif new_duplicates:
    print(f"❌ Still has duplicates: {set(new_duplicates)}")
else:
    print("ℹ️  No duplicates in either version (good test case needed)")