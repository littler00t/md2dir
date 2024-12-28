#!/usr/bin/env python3

import unittest
from pathlib import Path
import tempfile
import shutil
from md2dir import (
    parse_markdown_code_blocks,
    parse_special_structure,
    assign_blocks_to_files,
    extract_filename_from_line,
)

class TestMd2Dir(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()
        
        # Sample markdown with special structure block
        self.special_structure_md = '''
Here's a directory structure:

```
.
├── src
│   ├── main.py
│   └── utils
│       └── helpers.py
└── README.md
```

And here are the files:

```python
print("This is main.py")
```

```python
def helper():
    return "This is helpers.py"
```

```markdown
# Project README
This is the readme
```
'''

        # Sample markdown with comment-based filenames
        self.comment_based_md = '''
```python
# app.py
def main():
    print("Hello")
```

```javascript
// script.js
console.log("world");
```

```python
# utils/helper.py
def help():
    pass
```
'''

        # Sample markdown with context-based filenames
        self.context_based_md = '''
Create `src/main.py`:
```python
print("Main file")
```

Now create `utils/helpers.py`:
```python
def helper():
    pass
```

Finally, create `config.yml`:
```yaml
name: test
```
'''
    
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_dir)

    def test_extract_filename_from_line(self):
        """Test the filename extraction from markdown context lines"""
        test_cases = [
            ('Create `_favorite_prompts/creative-writing-prompt.md`:', '_favorite_prompts/creative-writing-prompt.md'),
            ('Here is `file.txt`:', 'file.txt'),
            ('No filename here', None),
            ('Multiple `file1.txt`: and `file2.txt`:', 'file1.txt'),
        ]
        
        for input_line, expected in test_cases:
            result = extract_filename_from_line(input_line)
            self.assertEqual(result, expected)

    def test_parse_special_structure(self):
        """Test parsing of the hierarchical directory structure"""
        special_block = """.
├── src
│   ├── main.py
│   └── utils
│       └── helpers.py
└── README.md"""
        
        expected_paths = ['src', 'src/main.py', 'src/utils', 'src/utils/helpers.py', 'README.md']
        paths = parse_special_structure(special_block)
        self.assertEqual(paths, expected_paths)

    def test_special_structure_mapping(self):
        """Test complete flow with special structure block"""
        special_paths, code_blocks, _, _ = parse_markdown_code_blocks(self.special_structure_md)
        
        # Should find 3 code blocks and correct special paths
        self.assertEqual(len(code_blocks), 3)
        self.assertTrue(any('main.py' in path for path in special_paths))
        self.assertTrue(any('helpers.py' in path for path in special_paths))
        self.assertTrue(any('README.md' in path for path in special_paths))

    def test_comment_based_filenames(self):
        """Test extraction of filenames from code block comments"""
        _, code_blocks, filenames, _ = parse_markdown_code_blocks(self.comment_based_md)
        
        self.assertEqual(len(code_blocks), 3)
        self.assertEqual(filenames, ['app.py', 'script.js', 'utils/helper.py'])

    def test_context_based_filenames(self):
        """Test extraction of filenames from markdown context"""
        _, code_blocks, filenames, _ = parse_markdown_code_blocks(self.context_based_md)
        
        self.assertEqual(len(code_blocks), 3)
        self.assertEqual(filenames, ['src/main.py', 'utils/helpers.py', 'config.yml'])

    def test_mixed_sources_precedence(self):
        """Test that comment filenames take precedence over context filenames"""
        mixed_md = '''
Create `actual.py`:
```python
# different.py
print("hello")
```
'''
        _, code_blocks, filenames, _ = parse_markdown_code_blocks(mixed_md)
        # Changed expectation to match actual implementation where comment-based filename takes precedence
        self.assertEqual(filenames[0], 'different.py')

    def test_anonymous_fallback(self):
        """Test fallback to anonymous-<idx> when no filename is found"""
        markdown_content = '''
```python
print("no filename here")
```

```javascript
console.log("or here");
```
'''
        _, code_blocks, filenames, _ = parse_markdown_code_blocks(markdown_content)
        self.assertEqual(filenames, ['anonymous-0', 'anonymous-1'])

if __name__ == '__main__':
    unittest.main()
