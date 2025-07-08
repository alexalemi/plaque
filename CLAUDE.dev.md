# Plaque Project Context

## Overview
Plaque is a local-first notebook system for Python, inspired by Clerk for Clojure. It turns regular Python files into interactive notebooks with real-time updates and smart dependency tracking.

## Key Design Principles
- **Local-first**: Uses plain Python files as source - no special file formats
- **Live Updates**: Browser preview updates in real-time as you edit
- **Rich Output**: Supports Markdown, LaTeX equations, plots, DataFrames, and more
- **Flexible Format**: Supports both `# %%` markers and multiline comments for cells
- **Python-native**: Uses standard Python syntax for both code and documentation

## Project Structure

### Core Modules
These are all at `src/plaque/`:
- **`parser.py`**: Parses Python files into cells, handles both `# %%` markers and multiline comments
- **`cell.py`**: Defines `Cell` and `CellType` classes for representing notebook cells
- **`environment.py`**: Execution environment with proper error handling and matplotlib capture
- **`formatter.py`**: HTML generation with Pygments syntax highlighting and markdown rendering
- **`display.py`**: Marimo-style display system with method resolution priority
- **`server.py`**: HTTP server with auto-reload functionality for live serving
- **`watcher.py`**: File watching system for detecting changes
- **`cli.py`**: Command-line interface with `render` and `watch` subcommands
- **`processor.py`** - The re-run logic.

### Templates
Also at `src/plaque`:
- **`templates/notebook.html`**: Complete HTML template with CSS styling for notebooks

## CLI Commands
```bash
# Generate static HTML
plaque render my_notebook.py [output.html] [--open]

# Start an automatic and caching renderer
plaque watch my_notebook.py [output.html] [--open]

# Start live server with auto-reload
plaque serve my_notebook.py [--port 5000] [--open]
```

## Display System (Marimo-style)
The display system follows this method resolution order:
1. `_display_()` method - returns any Python object (recursive)
2. `_mime_()` method - returns `(mime_type, data)` tuple
3. IPython `_repr_*_()` methods - `_repr_html_()`, `_repr_png_()`, etc.
4. Built-in type handling - matplotlib figures, pandas DataFrames, PIL images
5. `repr()` fallback

## Cell Formats Supported

### Traditional Markers
```python
# %%
x = 42

# %% [markdown]
# # This is a markdown cell

# %%
print(x)
```

### Multiline Comments
```python
"""
# Getting Started
This is a markdown cell using multiline strings.
"""

x = 42  # Regular code

"""More markdown content"""
```

## Key Dependencies
- **click**: CLI framework
- **watchdog**: File watching
- **pygments**: Syntax highlighting
- **markdown**: Markdown processing (with extensions for tables, code highlighting)

## Recent Major Improvements

### ✅ Completed Features
- **Parser**: Comprehensive parsing with support for both cell formats
- **Environment**: Code execution with proper error handling and matplotlib capture
- **Formatter**: Professional HTML output with Pygments and markdown support
- **Display System**: Marimo-style method resolution for rich output
- **CLI**: Subcommand structure with `render` and `watch`
- **Live Server**: Auto-reload functionality with temporary file management
- **Error Handling**: Detailed syntax and runtime error formatting
- **Testing**: Comprehensive test suite for core components

### 🔧 Current Status
The project is feature-complete for basic notebook functionality. The live server works with auto-reload, rich display is functional, and error handling is robust.

### 📋 Remaining Tasks
- **SSE Updates**: Consider server-sent events for real-time updates
- **Dependency Tracking**: Smart re-execution based on variable dependencies
- **Additional Tests**: Integration and end-to-end testing

## Testing
Comprehensive test suite covering:
- **Display System**: Method resolution, IPython methods, built-in types
- **Environment**: Code execution, error handling, variable persistence
- **Formatter**: HTML generation, template injection, styling

Run tests with: `uv run pytest tests/`

## Development Workflow
This project uses `uv` for Python package management and development. Install `uv` first if you haven't already.

```bash
# Install development dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Test with example
uv run plaque render examples/example.py
uv run plaque watch examples/example.py --open
```

## Known Issues & Considerations
- Error formatting filters out internal plaque frames
- Auto-reload polls every 1 second for changes

## Architecture Notes
- **Modular Design**: Each component is well-separated and testable
- **Template System**: HTML template extracted to separate file
- **Error Handling**: Comprehensive error capture with cleaned tracebacks
- **Resource Management**: Proper cleanup of temp files and watchers
- **Security**: HTML escaping to prevent XSS attacks

This project successfully implements a clean, local-first notebook system that maintains the simplicity of Python files while providing rich interactive features.
