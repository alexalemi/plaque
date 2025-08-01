# Plaque

A local-first notebook system for Python, inspired by
[Clerk](https://clerk.vision/) for Clojure. Plaque turns regular Python files
into interactive notebooks with real-time updates and smart dependency
tracking.

**👉 Check out [`examples/getting-started.py`](examples/getting-started.py) and its rendered version at [`examples/getting-started.html`](https://htmlpreview.github.io/?https://github.com/alexalemi/plaque/blob/main/examples/getting-started.html) to see Plaque in action or watch the 🎥[Demo Video](https://youtu.be/DlbA1aOMsFw?si=gq8EFQ6LpcweRSu7)**

## Features

- **Local-first**: Uses plain Python files as the source - and your own editor - no special file formats
- **Live Updates**: Browser preview updates in real-time as you edit
- **Rich Output**: Supports Markdown, LaTeX equations, plots, DataFrames, and more
- **Flexible Format**: Supports both `# %%` markers and multiline comments for cells
- **Python-native**: Use standard Python syntax for both code and documentation

## Principles

Many systems support reactive notebooks, like [clerk](https://clerk.vision/),
[marimo](https://marimo.io/),
[observable](https://observablehq.com/framework/),
[pluto](https://plutojl.org/), etc. Plaque is meant to be a simple thing that
provides 80% of the utility with a very simple package.  The core idea is that
your files should only run as they would if you ran them from scratch from top
to bottom, but we don't actually have to rerun every cell every time.  Instead,
we only ever re-execute any cell you modify and any cells later in the document.

In this way, you can have most of the benefits for reactivity and live
updating, but still get caching and some gaurentee that you don't have to
re-evaluate expensive computations.  

## Usage

Plaque supports two different styles for creating notebooks:

### 1. Traditional Cell Markers

Using `# %%` markers, similar to VS Code notebooks:

```python
# Code cell
x = 42
print(f"The answer is {x}")

# %% [markdown]
# # This is a markdown cell
#
# With support for:
# - Lists
# - **Bold text**
# - And more!

# %%
# Another code cell
import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [1, 4, 9])
plt.show()
```

### 2. Multiline Comments as Cells

Using Python's multiline strings (`"""` or `'''`) for documentation:

```python
"""
# Getting Started

This notebook demonstrates using multiline comments as markdown cells.
All standard markdown features are supported:

1. **Bold text**
2. *Italic text*
3. Code blocks
4. LaTeX equations: $E = mc^2$
"""

# Code is automatically treated as a code cell
x = 42
print(f"The answer is {x}")

"""
## Data Visualization

Now let's make a plot:
"""

import matplotlib.pyplot as plt
plt.plot([1, 2, 3], [1, 4, 9])
plt.show()

"""
The plot shows a quadratic relationship between x and y.
"""
```

### 3. F-style Top Level Comments (Programmatic Templates)

Using f-string style comments for programmatic templated output:

```python
f"""
# Dynamic Report for {dataset_name}

Results generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics
- Total samples: {len(data)}
- Mean value: {np.mean(data):.2f}
- Standard deviation: {np.std(data):.2f}
"""

dataset_name = "Sales Data Q4"
data = [1, 2, 3, 4, 5]

f"""
## Analysis Results

The dataset '{dataset_name}' contains {len(data)} data points.
Maximum value observed: {max(data)}
"""
```

F-style comments allow you to create dynamic markdown cells that incorporate variables and expressions, making them perfect for automated reports and templated notebooks.

Both styles support:
- Markdown formatting with bold, italic, lists, etc.
- LaTeX equations (both inline and display)
- Code syntax highlighting
- Rich output (plots, DataFrames, etc.)

### Guidelines for Multiline Comments

When using multiline comments as cells:
1. Top-level comments become markdown cells
2. Function/method docstrings remain as code
3. You can mix code and documentation freely
4. Both `"""` and `'''` are supported

## Installation

You can install Plaque using either pip or uv:

### Install from PyPI

```bash
# Using pip
pip install plaque

# Using uv (recommended)
uv pip install plaque
```

### Local Development

```bash
# Clone the repository
git clone https://github.com/alexalemi/plaque.git
cd plaque

# Install in development mode
uv pip install -e .
# or
pip install -e .
```

### Development Setup with Dependencies

For development work with testing and additional tools:

```bash
# Clone the repository
git clone https://github.com/alexalemi/plaque.git
cd plaque

# Create and activate a virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
uv pip install -e ".[dev]"
# or
pip install -e ".[dev]"
```

## Running a Notebook

To render a notebook:

```bash
# Generate static HTML
plaque render my_notebook.py

# Generate static HTML with custom output path
plaque render my_notebook.py output.html

# Start a live re-render with caching.
plaque watch my_notebook.py

# Start live server with auto-reload
plaque serve my_notebook.py

# Specify a custom port (default is 5000)
plaque serve my_notebook.py --port 8000

# Open browser automatically
plaque serve my_notebook.py --open
```
