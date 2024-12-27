# Markdown Code Block Parser

A Python utility that parses code blocks from a Markdown file, optionally assigns them to file names, and writes them out to disk. This is especially useful for creating file-based outputs from lengthy Markdown documentation or tutorials that contain many code blocks. It can also be used to extract code from LLM responses, it was specifically tested with ChatGPT output.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [Mapping Code Blocks to File Names](#mapping-code-blocks-to-file-names)
  - [Using Comment-Based Filenames](#using-comment-based-filenames)
  - [Writing Code Blocks to Files](#writing-code-blocks-to-files)
  - [Excluding Paths](#excluding-paths)
  - [Excluding Code Blocks by Index](#excluding-code-blocks-by-index)
  - [Reading from `stdin`](#reading-from-stdin)
- [Special Structure Blocks](#special-structure-blocks)
- [Example Run](#example-run)
- [File Assignments Logic](#file-assignments-logic)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

This Python script scans a Markdown file for **triple backtick** code blocks. It can:

1. Collect them into memory.
2. Optionally map each block to a specific file path via:
   - A "special structure" code block (a directory tree).
   - A first-line comment based filename (using an optional `--comments` flag).
3. (Optionally) write each code block to a file on disk.

The result: you can keep all your code examples in a single Markdown file, and quickly extract them into actual files for easy building or usage.

---

## Features

- **Parse code blocks** from Markdown files or standard input.
- **Extract filenames** from:
  - A special block describing a directory structure.
  - The **first line comment** of each code block (e.g. `// MyFile.ts`, `# MyScript.sh`, etc.).
- **Default filenames** (`anonymous-<idx>`) if no valid filename can be determined from a comment.
- **Exclude** specific file paths or specific code block indices.
- **Write** code blocks to files with minimal fuss.
- Supports any code block language, from `python` to `tsx`, `sh`, `html`, etc.

---

## Installation

1. Clone this repository or download the `.py` script.
2. Ensure you have Python 3.7+ installed.
3. (Optional) Create a virtual environment and install dependencies if desired.  
4. Run the Python program directly:
   ```bash
   python markdown_parser.py --help
   ```

This project does not rely on external libraries beyond Python’s standard library (i.e., `argparse`, `re`, `sys`, `pathlib`).

---

## Usage

Below is a summary of CLI arguments. You can also see them at any time by running:
```bash
python markdown_parser.py --help
```

| Argument         | Description                                                                                                  | Default     |
|------------------|--------------------------------------------------------------------------------------------------------------|-------------|
| `input`          | Path to the Markdown file or `-` to read from standard input.                                                | _required_  |
| `--write`        | Write the extracted code blocks to files (if code blocks are mapped). Otherwise, just prints on screen.     | _flag_      |
| `--output-dir`   | Directory to which the code blocks will be written when `--write` is used.                                   | `output`    |
| `--exclude`      | Exclude paths that exactly match the specified paths. Can be used multiple times.                            | _None_      |
| `--exclude-block`| Comma-separated indices of code blocks to exclude. For example `--exclude-block 0,2` to skip blocks #0 and #2| _None_      |
| `--map`          | Map code blocks to file names. Without this, code blocks are just printed to screen.                         | _flag_      |
| `--comments`     | Use filenames from the first-line comment of each code block instead of the special structure.              | _flag_      |

### Basic Usage

To **parse** a local Markdown file (and simply print out all code blocks found) without any mapping:

```bash
python markdown_parser.py example.md
```

### Mapping Code Blocks to File Names

If you want to **map** each extracted code block to a file name using a **special structure block** in the Markdown, you pass `--map`. For example:

```bash
python markdown_parser.py example.md --map
```

The program looks for a code block like:

<details>
  <summary>An example tree structure:</summary>

````markdown
```
. 
├── src
│   ├── main.py
│   └── helpers.py
└── README.md
```
````
</details>

Such a block tells the parser that there are N files (lines) in this structure. It will try to map them in **the same order** to the N code blocks found in the entire document.

### Using Comment-Based Filenames

Alternatively, to have **each code block** named according to its **first line comment**, run with `--map` and `--comments`:

```bash
python markdown_parser.py example.md --map --comments
```

In this mode, each code block’s first line is inspected. If it starts with a recognized comment (like `// MyFile.ts`, `# MyFile.sh`, etc.), that filename is extracted. If multiple filenames are listed (e.g. `// MyFile.ts or Another.ts`), only the first is used. If no valid comment-based filename is found, it will assign a default name `anonymous-<idx>` (where `<idx>` is the 0-based index of the code block in the Markdown).

### Writing Code Blocks to Files

If you want to **write the code blocks** to disk (not just print them), you must pass `--write` along with `--map`. Example:

```bash
python markdown_parser.py example.md --map --write
```

This will create an `output` directory (by default) and produce the files named in the special structure block (or the comment-based filenames, if you used `--comments`).

You can customize the output directory:

```bash
python markdown_parser.py example.md --map --write --output-dir my_folder
```

### Excluding Paths

Sometimes you don’t want certain files from the special structure or the comment-based list. For this, use the `--exclude` argument. For example:

```bash
python markdown_parser.py example.md --map --write --exclude README.md --exclude old_file.py
```

If a path (or comment-based filename) matches exactly the string you provide in `--exclude`, it will be removed from the mapping.

### Excluding Code Blocks by Index

You might also want to skip certain code blocks by their **index** in the extraction order. In that case:

```bash
python markdown_parser.py example.md --exclude-block 2,4
```

This ignores the 3rd and 5th code blocks in the final list, effectively removing them from what is shown or mapped.

### Reading from `stdin`

You can pipe Markdown content directly via `stdin` by using `-` as the file argument. For example:

```bash
cat example.md | python markdown_parser.py - --map
```

---

## Special Structure Blocks

The script includes logic to detect a “special structure” block (like a directory tree). This structure must be in a dedicated code block, usually matching a pattern similar to:

<details>
  <summary>Example structure block</summary>

````markdown
```
.
├── file_a.txt
├── src
│   └── module_b.py
└── docs
```
````
</details>

The parser will capture these lines, read them as a hierarchical tree, and extract a list of file paths (e.g. `src/module_b.py`). If you use `--map` (and **not** `--comments`), these extracted file paths become the mapping basis for the code blocks.

**Important**: The total number of lines in that tree (i.e., total discovered files) must match the total number of code blocks. Otherwise, the tool will exit with an error.

---

## Example Run

Given a Markdown file [`example.md`](example.md) containing:
 
Running:
```bash
python markdown_parser.py example.md --map
```
Would detect a special structure block with 2 file paths: `main.py`, `helpers.py`. It also detects 2 code blocks. It then pairs them:

1. `main.py` -> code block #0 (language: plaintext or derived from code fence, content: `print("Hello, main!")`)
2. `helpers.py` -> code block #1 (content: `def helper(): ...`)

If you append `--write`, the tool writes:

- `output/main.py`
- `output/helpers.py`

Similarly, if you ran it with `--comments` (and no special structure block or ignoring it), it would map each code block to the first line comment for its filename. If none found, it assigns a default name: `anonymous-<idx>`.

---

## File Assignments Logic

When `--map` is used, the script assigns code blocks to filenames by **zipping** the list of filenames with the list of code blocks:

1. If `--comments` is **not** used, it tries to use the **special structure** code block.  
2. If `--comments` **is** used, it ignores the special structure block and uses the filenames extracted from the first line comments.  
3. If you also specified `--exclude`, it filters out any exact matches from the file path (or comment-based) list.  
4. If there is a mismatch in the number of code blocks versus the number of filenames after exclusion, the script stops with an error.  

Finally, each file name gets the code block with the same index. For example, file_paths[0] is matched to code_blocks[0], file_paths[1] to code_blocks[1], etc.

---

## Contributing

We welcome any issues, pull requests, or general feedback! To contribute:

1. Fork the repository.
2. Create a new branch from `main`.
3. Make your changes and run local tests.
4. Submit a pull request explaining the changes.

We will review your contribution as soon as possible.

---

## License

This project is licensed under the [MIT License](LICENSE). Feel free to use, modify, and distribute this software according to its terms.