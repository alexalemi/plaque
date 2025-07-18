# Plaque - Interactive Python Notebook Library

Plaque is a local-first notebook system that turns regular Python files into interactive notebooks with live updates. This guide covers how to use Plaque effectively for notebook development.

## Basic Usage

### Creating Notebook Cells
Plaque supports three cell formats:

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

**F-style comments (programmatic templating):**
```python
f"""
# Dynamic Analysis Report

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Dataset: {dataset_name}
"""

dataset_name = "User Metrics"
sample_count = 1000
mean_value = 42.5

f"""
## Key Findings

- Sample size: {sample_count:,} observations
- Average value: {mean_value:.2f}
- Status: {'✅ Complete' if sample_count > 500 else '⚠️ Insufficient data'}

The analysis shows {sample_count} data points with an average of {mean_value}.
"""
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

## API for AI Agents

When running `plaque serve`, Plaque exposes RESTful API endpoints that enable AI agents to interact with notebooks programmatically. This allows agents to query individual cells, inspect outputs, and understand notebook state without parsing HTML.

### API Endpoints

All API endpoints return JSON and include CORS headers for cross-origin access.

#### List All Cells
```
GET /api/cells
```
Returns a summary of all cells in the notebook:
```json
{
  "cells": [
    {
      "index": 0,
      "type": "markdown",
      "lineno": 1,
      "is_code": false,
      "has_error": false,
      "execution_count": null
    },
    {
      "index": 1,
      "type": "code",
      "lineno": 5,
      "is_code": true,
      "has_error": false,
      "execution_count": 1
    }
  ]
}
```

#### Get Cell Details
```
GET /api/cell/{index}
```
Returns complete information for a specific cell (0-based index):
```json
{
  "index": 1,
  "type": "code",
  "lineno": 5,
  "content": "x = 42\nprint(f\"The answer is {x}\")",
  "metadata": {},
  "execution": {
    "counter": 1,
    "status": "success",
    "error": null,
    "stdout": "The answer is 42\n",
    "stderr": "",
    "result": {
      "type": "text/plain",
      "data": "42"
    }
  },
  "dependencies": {
    "provides": ["x"],
    "requires": [],
    "depends_on": []
  }
}
```

#### Get Cell Input Only
```
GET /api/cell/{index}/input
```
Returns just the cell content:
```json
{
  "index": 1,
  "content": "x = 42\nprint(f\"The answer is {x}\")"
}
```

#### Get Cell Output Only
```
GET /api/cell/{index}/output
```
Returns just the execution results:
```json
{
  "index": 1,
  "counter": 1,
  "error": null,
  "stdout": "The answer is 42\n",
  "stderr": "",
  "result": {
    "type": "text/plain",
    "data": "42"
  }
}
```

#### Get Notebook State
```
GET /api/notebook/state
```
Returns overall notebook statistics:
```json
{
  "total_cells": 5,
  "code_cells": 4,
  "markdown_cells": 1,
  "executed_cells": 3,
  "error_cells": 1,
  "last_update": 1640000000000,
  "cells_with_errors": [3]
}
```

#### Search Cells
```
GET /api/search?q=keyword
```
Search for cells containing specific text:
```json
{
  "query": "matplotlib",
  "results": [
    {
      "index": 2,
      "type": "code",
      "lineno": 10,
      "preview": "import matplotlib.pyplot as plt..."
    }
  ]
}
```

### Result Types

The API returns different result types based on cell output:

- **Text**: `{"type": "text/plain", "data": "..."}`
- **HTML**: `{"type": "text/html", "data": "<div>...</div>"}`
- **Images**: `{"type": "image/png", "url": "/images/img_001.png", "data": "base64..."}`
- **DataFrames**: `{"type": "dataframe", "shape": [3, 2], "columns": [...], "data": [...]}`
- **JSON**: `{"type": "application/json", "data": {...}}`
- **Markdown**: `{"type": "text/markdown", "data": "# Header..."}`

### Example Agent Workflow

```python
import requests

# 1. Get notebook overview
response = requests.get('http://localhost:5000/api/cells')
cells = response.json()['cells']

# 2. Find cells with errors
response = requests.get('http://localhost:5000/api/notebook/state')
error_indices = response.json()['cells_with_errors']

# 3. Inspect a specific error
if error_indices:
    response = requests.get(f'http://localhost:5000/api/cell/{error_indices[0]}')
    cell = response.json()
    print(f"Error in cell {cell['index']}: {cell['execution']['error']}")

# 4. Search for specific content
response = requests.get('http://localhost:5000/api/search?q=matplotlib')
results = response.json()['results']
```

### Benefits for AI Agents

- **Selective Access**: Query only the cells you need
- **Structured Data**: JSON responses are easy to parse
- **Error Detection**: Quickly identify problematic cells
- **Dependency Tracking**: Understand cell relationships
- **Real-time Updates**: Poll endpoints to monitor changes
- **Image Support**: Access generated plots and visualizations