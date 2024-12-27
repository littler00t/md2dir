#!/usr/bin/env python3

import argparse
import re
import sys
from pathlib import Path

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
    comments_filenames = []  # <-- new list for storing filenames from comments

    # Regex to capture something that looks like a first-line comment
    # e.g. // AppRouter.tsx or App.tsx
    # We'll consider typical comment starts: //, #, <!--, /*, %
    # Then we capture the rest of the line in group 'filenames'.
    comment_line_pattern = re.compile(r'^(?:\s*(?:\/\/|#|<!--|/\*|%)\s*)(?P<filenames>.+)$', re.IGNORECASE)

    # Enumerate code blocks so we can create an "anonymous-<idx>" filename if none is found
    for idx, match in enumerate(code_block_pattern.finditer(markdown_content)):
        language = match.group(1).strip() if match.group(1) else "plaintext"
        content = match.group(2)

        print(f"Found code block #{idx} with language: {language}")

        # Check if this block is a special structure block
        if special_block_pattern.match(match.group(0)):
            print("Identified special structure block.")
            special_paths = parse_special_structure(content)
        else:
            # Standard code block
            code_blocks.append((language, content))

            # --- New: Extract filename from the first line comment, if present ---
            first_line = content.split('\n', 1)[0].rstrip()
            comment_match = comment_line_pattern.match(first_line)
            if comment_match:
                # e.g. if it's " // AppRouter.tsx or App.tsx "
                # capture filenames and take the first chunk if " or " is present
                possible_filenames = re.split(r'\s+or\s+', comment_match.group('filenames'), maxsplit=1)
                extracted_filename = possible_filenames[0].strip()
                comments_filenames.append(extracted_filename)
            else:
                # No recognized comment-based filename => use a default "anonymous-<idx>"
                default_filename = f"anonymous-{idx}"
                comments_filenames.append(default_filename)

    print(f"Special paths extracted: {special_paths}")
    print(f"Comments-based filenames extracted: {comments_filenames}")
    print(f"Total code blocks found: {len(code_blocks)}")

    return special_paths, code_blocks, comments_filenames

def parse_special_structure(special_block_content):
    """Parse the special structure block and extract file paths."""
    print("Parsing special structure block...")
    paths = []
    stack = []
    for line in special_block_content.splitlines():
        line = line.lstrip()  # Ensure leading spaces are stripped
        print(f"Processing line: {line}")

        # Example lines might start with: ├──, └──, or │   └──
        if line.startswith("├──") or line.startswith("└──") or line.startswith("│   └──"):
            # Calculate the current depth level
            level = line.count("│")
            name = line.split("──")[-1].strip()

            # Update the stack to maintain the correct path hierarchy
            while len(stack) > level:
                stack.pop()

            # Add the current directory or file to the stack
            stack.append(name)

            # Construct the full path from the stack
            path = "/".join(stack)
            paths.append(path)
            print(f"Extracted path: {path}")
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
    special_paths, code_blocks, comments_filenames = parse_markdown_code_blocks(markdown_content)

    # Exclude blocks by index if requested
    exclude_indices = []
    if args.exclude_block:
        exclude_indices = [int(idx.strip()) for idx in args.exclude_block.split(",")]
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
