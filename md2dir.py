#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

def extract_filename_from_line(line):
    """Extract filename from a line containing backticked filename."""
    match = re.search(r'`([^`]+)`:', line)
    if match:
        return match.group(1)
    return None

def parse_markdown_code_blocks(markdown_content):
    """Parse all code blocks from the markdown content."""
    print("Parsing markdown content for code blocks...")

    # Adjust the regex pattern to properly capture triple backtick code blocks:
    #   ```<language>\n<content>\n```
    code_block_pattern = re.compile(
        r'```([\w+-]*)\n(.*?)```',
        re.DOTALL
    )

    # Pattern to detect the "special structure" code block (directory tree).
    # We'll assume these also appear as triple backticks, but begin with a dot (.)
    # e.g. ```\n.(something)```
    special_block_pattern = re.compile(
        r'```[\w+-]*\n\.(.*?)```',
        re.DOTALL
    )

    code_blocks = []
    special_paths = []
    comments_filenames = []
    special_block_index = None  # Track special block index

    # Regex to capture something that looks like a first-line comment
    comment_line_pattern = re.compile(r'^(?:\s*(?:\/\/|#|<!--|/\*|%)\s*)(?P<filenames>.+)$', re.IGNORECASE)

    # Split content into lines for context analysis
    content_lines = markdown_content.splitlines()
    
    # Find all code blocks with their positions
    matches = list(code_block_pattern.finditer(markdown_content))
    
    for idx, match in enumerate(matches):
        language = match.group(1).strip() if match.group(1) else "plaintext"
        content = match.group(2)

        print(f"Found code block #{idx} with language: {language}")

        # Check if this block is a special structure block
        if special_block_pattern.match(match.group(0)):
            print("Identified special structure block.")
            special_paths = parse_special_structure(content)
            special_block_index = idx  # Store the index
            continue  # Skip adding to code_blocks

        # Check first line for existing filename comment
        first_line = content.split('\n', 1)[0].rstrip()
        comment_match = comment_line_pattern.match(first_line)
        
        if comment_match:
            # Use existing comment filename
            possible_filenames = re.split(r'\s+or\s+', comment_match.group('filenames'), maxsplit=1)
            extracted_filename = possible_filenames[0].strip()
            comments_filenames.append(extracted_filename)
            code_blocks.append((language, content))
        else:
            # Look for filename in preceding context
            # Find the line number where this code block starts
            start_pos = match.start()
            preceding_text = markdown_content[:start_pos]
            preceding_lines = preceding_text.splitlines()[-3:]  # Get last 3 lines
            
            filename = None
            for line in reversed(preceding_lines):
                extracted = extract_filename_from_line(line)
                if extracted:
                    filename = extracted
                    break
            
            if filename:
                # Add filename as a comment at the start of the content
                comment_prefix = '//' if language in ['javascript', 'typescript', 'js', 'ts'] else '#'
                modified_content = f"{comment_prefix} {filename}\n{content}"
                code_blocks.append((language, modified_content))
                comments_filenames.append(filename)
            else:
                # No filename found anywhere
                default_filename = f"anonymous-{idx}"
                code_blocks.append((language, content))
                comments_filenames.append(default_filename)

    print(f"Special paths extracted: {special_paths}")
    print(f"Comments-based filenames extracted: {comments_filenames}")
    print(f"Total code blocks found: {len(code_blocks)}")

    return special_paths, code_blocks, comments_filenames, special_block_index

def parse_tree(ascii_tree_str: str) -> list[str]:
    """
    Parse a tree-like ASCII directory structure into a list of paths.
    
    Example:
        Input:
            ├── src
            │   ├── main.py
            │   └── utils
            │       └── helpers.py
            └── README.md
        
        Output:
            ["src", "src/main.py", "src/utils", "src/utils/helpers.py", "README.md"]
    """
    lines = ascii_tree_str.strip().split("\n")
    result = []
    stack = []
    
    for line in lines:
        # Strip trailing spaces
        line = line.rstrip()
        
        # Find the item name after "── "
        match = re.search(r"── (.+)", line)
        if not match:
            # If we can't find "── ", skip this line (could be empty or just an intermediate '│')
            continue
        item_name = match.group(1)
        
        # Count how many indentation groups of "│   " or "    " occur at the start
        depth = 0
        i = 0
        while i < len(line):
            chunk = line[i:i+4]
            if chunk in ("│   ", "    "):
                depth += 1
                i += 4
            else:
                # Move character-by-character until we find more 4-char blocks or the name
                i += 1
        
        # If we are at a shallower level, pop from the stack
        while len(stack) > depth:
            stack.pop()
        
        # Build the full path from stack + current item
        path = "/".join(stack + [item_name])
        result.append(path)
        
        # Heuristic: if the item has no '.', treat it as a directory and push onto the stack
        # (so that subsequent deeper paths will be nested within it).
        if '.' not in item_name:
            stack.append(item_name)
    
    return result

def parse_special_structure(special_block_content):
    return parse_tree(special_block_content)

    """Parse the special structure block and extract file paths."""
    print("Parsing special structure block...")
    paths = []
    current_path = []
    
    for line in special_block_content.splitlines():
        if not line or line == '.':  # Skip empty lines and root
            continue
            
        print(f"Processing line: {line}")

        # Find the position of the first character of the filename
        # (after the tree symbols)
        if '──' in line:
            name = line.split("──")[-1].strip()
            # Calculate indent level based on the position of the name
            # First level starts at position 5, each subsequent level is 4 chars further
            pos = len(line) - len(line.lstrip())
            indent = (pos - 5) // 4 if pos >= 5 else 0
            
            # Adjust current path based on indent level
            current_path = current_path[:indent]
            print(f"Current path: {current_path}, indent: {indent}, name: {name}")
            current_path.append(name)
            
            # Build the full path
            if indent == 0:  # Root level files (like README.md)
                paths.append(name)
            else:
                # For nested files/directories, include all parent directories
                path_parts = current_path[:]
                if '.' in name:  # If it's a file
                    paths.append('/'.join(path_parts))
                else:  # If it's a directory
                    paths.append('/'.join(path_parts))
                
    print(f"Extracted paths: {paths}")
    return paths

def assign_blocks_to_files(file_paths, code_blocks):
    """Assign code blocks to file paths."""
    print("Assigning code blocks to file paths...")
    file_assignments = {}
    for file_path, code_block in zip(file_paths, code_blocks):
        file_assignments[file_path] = code_block
        print(f"Assigned code block to file: {file_path}")
    return file_assignments

def write_files(file_assignments, output_dir):
    """Write the code blocks to files."""
    print(f"Writing files to directory: {output_dir}")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for file_path, (language, content) in file_assignments.items():
        full_path = output_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Writing file: {full_path}")
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

def filter_excluded_paths(paths, excludes):
    """Filter out paths that exactly match any of the exclude criteria."""
    if not excludes:
        return paths

    print(f"Excluding paths that exactly match any of: {excludes}")
    filtered_paths = [path for path in paths if path not in excludes]
    print(f"Filtered paths: {filtered_paths}")
    return filtered_paths

def filter_excluded_blocks(code_blocks, exclude_indices):
    """Filter out code blocks by their indices."""
    if not exclude_indices:
        return code_blocks

    print(f"Excluding code blocks with indices: {exclude_indices}")
    filtered_blocks = [block for idx, block in enumerate(code_blocks) if idx not in exclude_indices]
    print(f"Filtered code blocks count: {len(filtered_blocks)}")
    return filtered_blocks

def main():
    parser = argparse.ArgumentParser(description="Parse markdown code blocks and optionally write to files.")
    parser.add_argument("input", type=str, help="Path to the markdown file or '-' for stdin.")
    parser.add_argument("--write", action="store_true", help="Write the extracted code blocks to files.")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory to write the files to (default: 'output').")
    parser.add_argument("--exclude", action="append", help="Exclude paths that exactly match the specified paths.")
    parser.add_argument("--exclude-block", type=str, help="Exclude code blocks by their indices (comma-separated).")
    parser.add_argument("--map", action="store_true", help="Map code blocks to file names.")
    parser.add_argument("--comments", action="store_true",
                        help="Use filenames from the first line comment of each code block instead of the special structure block.")

    args = parser.parse_args()

    # Read Markdown Content
    if args.input == "-":
        print("Reading markdown content from stdin...")
        markdown_content = sys.stdin.read()
    else:
        print(f"Reading markdown content from file: {args.input}")
        with open(args.input, "r", encoding="utf-8") as f:
            markdown_content = f.read()

    # Parse all code blocks
    special_paths, code_blocks, comments_filenames, special_block_index = parse_markdown_code_blocks(markdown_content)

    # Setup exclude indices
    exclude_indices = []
    if args.exclude_block:
        exclude_indices = [int(idx.strip()) for idx in args.exclude_block.split(",")]
    
    # Always exclude the special structure block if one was found
    if special_block_index is not None:
        exclude_indices.append(special_block_index)
        
    code_blocks = filter_excluded_blocks(code_blocks, exclude_indices)

    # If --map is set, we attempt to assign code blocks to file names
    if args.map:
        # Decide which list of filenames to use
        if args.comments:
            print("Using comments-based filenames for mapping.")
            selected_filenames = comments_filenames
        else:
            print("Using special_paths for mapping.")
            selected_filenames = special_paths

        # Filter out excluded paths (only if we're using them)
        selected_filenames = filter_excluded_paths(selected_filenames, args.exclude)

        # Check that the count matches the code blocks
        if len(selected_filenames) != len(code_blocks):
            print("Mismatch between number of filenames and number of code blocks.")
            sys.exit(1)

        # Assign code blocks to the chosen filenames
        file_assignments = assign_blocks_to_files(selected_filenames, code_blocks)

        # Optionally write them out
        if args.write:
            write_files(file_assignments, args.output_dir)
            print(f"Files written to {args.output_dir}.")
        else:
            print("File assignments (no write flag):")
            for file_path, (lang, content) in file_assignments.items():
                print(f"--- {file_path} ({lang}) ---\n{content}\n")
    else:
        # Just print the code blocks
        print("Code blocks (no mapping selected):")
        for idx, (lang, content) in enumerate(code_blocks):
            print(f"[{idx}] {lang}:\n{content}\n")

if __name__ == "__main__":
    print("Starting markdown parser...")
    main()
    print("Markdown parser finished.")
