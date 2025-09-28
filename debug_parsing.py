#!/usr/bin/env python3
"""Debug git status parsing."""

# Simulate git status output
test_lines = [
    " M file1.txt",
    "MM file4.txt", 
    "?? file2.txt"
]

print("Testing git status parsing:")
for line in test_lines:
    print(f"\nLine: '{line}' (len={len(line)})")
    if len(line) >= 3:
        staged = line[0]
        unstaged = line[1]
        file_path = line[3:]
        print(f"  Staged: '{staged}'")
        print(f"  Unstaged: '{unstaged}'")
        print(f"  File: '{file_path}'")
    else:
        print(f"  Too short to parse")