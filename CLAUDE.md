# Plaque - Interactive Python Notebook Library

Plaque is a local-first notebook system that turns regular Python files into interactive notebooks with live updates. This guide covers how to use Plaque effectively for notebook development.

## Basic Usage

### Creating Notebook Cells
Plaque supports two cell formats:

**Traditional markers:**
```python
# %%
x = 42
print(f"The answer is {x}")

# %% [markdown]
# # This is a markdown cell
# You can write **bold** text and *italic* text

# %%
import matplotlib.pyplot as plt
plt.plot([1, 2, 3, 4])
plt.show()
```

**Multiline comments (recommended):**
```python
"""
# Getting Started
This is a markdown cell using multiline strings.
You can include LaTeX: $E = mc^2$
"""

x = 42  # Regular Python code

"""
## Results
The value of x is displayed below:
"""

x  # This will be displayed as output
```

### Running Your Notebook

**Generate static HTML:**
```bash
plaque render notebook.py output.html --open
```

**Live development with auto-reload:**
```bash
plaque serve notebook.py --port 5000 --open
```

**File watching (generates HTML on changes):**
```bash
plaque watch notebook.py output.html --open
```

## Live Updates and Output

When using `plaque serve`, your notebook updates automatically:
- **Real-time updates**: Browser refreshes when you save changes
- **Live server**: Runs at `http://localhost:5000/` (or specified port)
- **Auto-reload**: JavaScript polls `/reload_check` endpoint every second

### Getting Current Output Programmatically
If you need to access the current notebook output, you can make a GET request to the server:
```python
import requests
response = requests.get('http://localhost:5000/')
html_content = response.text
```

The `/reload_check` endpoint returns JSON with update timestamps:
```python
import requests
response = requests.get('http://localhost:5000/reload_check')
data = response.json()
print(f"Last update: {data['last_update']}")
```

## Rich Display Support

Plaque uses a Marimo-style display system with method resolution order:

1. `_display_()` method - returns any Python object (recursive)
2. `_mime_()` method - returns `(mime_type, data)` tuple
3. IPython `_repr_*_()` methods - `_repr_html_()`, `_repr_png_()`, etc.
4. Built-in type handling - matplotlib figures, pandas DataFrames, PIL images
5. `repr()` fallback

### Example Rich Outputs
```python
"""
# Data Visualization Examples
"""

import pandas as pd
import matplotlib.pyplot as plt

# DataFrames render as HTML tables
df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
df

# Matplotlib figures are automatically captured
plt.figure(figsize=(8, 6))
plt.plot([1, 2, 3, 4], [1, 4, 2, 3])
plt.title('Sample Plot')
plt.show()

# HTML content
from IPython.display import HTML
HTML('<h3 style="color: blue;">Custom HTML</h3>')
```

## Best Practices

1. **Use multiline comments** for markdown cells - they're more readable
2. **Save frequently** - the live server updates on every save
3. **Keep cells focused** - one concept per cell works best
4. **Use descriptive markdown** - explain your code and results
5. **Test with `plaque serve`** - see results immediately during development

## Development Notes

For library development, see `CLAUDE.dev.md` which contains:
- Project structure details
- Architecture documentation
- Development workflow
- Testing instructions
- Implementation details

## Common Commands

```bash
# Start live development server
plaque serve notebook.py --open

# Generate final HTML output
plaque render notebook.py final_output.html

# Watch for changes and regenerate
plaque watch notebook.py --open

# Run tests (for development)
uv run pytest tests/
```

## Error Handling

Plaque provides comprehensive error handling:
- Syntax errors are highlighted with line numbers
- Runtime errors show clean tracebacks
- Internal plaque frames are filtered out
- Errors don't crash the entire notebook

Your notebook will continue running even if individual cells fail, making iterative development smooth and efficient.