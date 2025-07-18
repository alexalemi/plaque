# Plaque Project Context

## Overview
Plaque is a local-first notebook system for Python, inspired by Clerk for Clojure. It turns regular Python files into interactive notebooks with real-time updates and smart dependency tracking.

**Current Version**: 0.3.0

## Key Design Principles
- **Local-first**: Uses plain Python files as source - no special file formats
- **Live Updates**: Browser preview updates in real-time as you edit
- **Rich Output**: Supports Markdown, LaTeX equations, plots, DataFrames, and more
- **Flexible Format**: Supports both `# %%` markers and multiline comments for cells
- **Python-native**: Uses standard Python syntax for both code and documentation

## Project Structure

### Core Modules
These are all at `src/plaque/`:
- **`ast_parser.py`**: AST-based parser for robust Python file parsing, handles both `# %%` markers and multiline comments with proper cell boundary detection
- **`cell.py`**: Defines `Cell` and `CellType` classes for representing notebook cells
- **`environment.py`**: Execution environment with proper error handling and matplotlib capture
- **`formatter.py`**: HTML generation with Pygments syntax highlighting and markdown rendering
- **`api_formatter.py`**: JSON API formatter for converting Cell objects to JSON for AI agent consumption
- **`display.py`**: Marimo-style display system with method resolution priority
- **`renderables.py`**: Structured data classes for rich display types (HTML, PNG, JPEG, SVG, Markdown, etc.)
- **`dependency_analyzer.py`**: Variable dependency tracking system analyzing which variables each cell provides/requires
- **`server.py`**: HTTP server with auto-reload functionality and REST API endpoints for live serving
- **`watcher.py`**: File watching system for detecting changes
- **`cli.py`**: Command-line interface with `render`, `watch`, and `serve` subcommands
- **`processor.py`**: Smart re-execution logic with dependency-based caching
- **`iowrapper.py`**: Output stream wrapper for capturing stdout/stderr during cell execution

### Templates
Also at `src/plaque`:
- **`templates/notebook.html`**: Complete HTML template with CSS styling for notebooks

## CLI Commands
```bash
# Generate static HTML
plaque render my_notebook.py [output.html] [--open]
plaque render directory/ [--open]  # Can process entire directories

# Start an automatic and caching renderer with file watching
plaque watch my_notebook.py [output.html] [--open]
plaque watch directory/ [--open]   # Can watch entire directories

# Start live server with auto-reload and REST API
plaque serve my_notebook.py [--port 5000] [--open]
```

The `serve` command includes:
- Live browser updates on file changes
- REST API endpoints at `/api/*` for agent integration
- Image serving at `/images/*` for generated plots
- Auto-reload polling every second

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

### F-String Comments (Programmatic Templates)
```python
f"""
# Dynamic Report for {dataset_name}
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary Statistics
- Total samples: {len(data)}
- Mean value: {np.mean(data):.2f}
"""

dataset_name = "Sales Data Q4"
data = [1, 2, 3, 4, 5]

f"""
## Analysis Results
The dataset '{dataset_name}' contains {len(data)} data points.
Maximum value observed: {max(data)}
"""
```

F-string comments allow dynamic markdown generation with embedded variables and expressions, perfect for automated reports and templated notebooks.

## Key Dependencies
- **click**: CLI framework
- **watchdog**: File watching
- **pygments**: Syntax highlighting
- **markdown**: Markdown processing (with extensions for tables, code highlighting)

## Recent Major Improvements

### ✅ Completed Features
- **AST Parser**: Robust parsing using Python's AST module with support for all cell formats
- **Environment**: Code execution with proper error handling and matplotlib capture
- **Formatter**: Professional HTML output with Pygments and markdown support
- **Display System**: Marimo-style method resolution for rich output with structured renderables
- **CLI**: Complete subcommand structure with `render`, `watch`, and `serve`
- **Live Server**: Auto-reload functionality with REST API and temporary file management
- **Dependency Tracking**: Smart re-execution based on variable dependencies
- **REST API**: Comprehensive API endpoints for AI agent integration
- **F-String Support**: Dynamic templated markdown cells with variable interpolation
- **Error Handling**: Detailed syntax and runtime error formatting with clean tracebacks
- **Testing**: Comprehensive test suite covering all components (11 test files)

### 🔧 Current Status
The project is feature-complete and production-ready. Major features include AST-based parsing, dependency tracking, REST API for agents, and sophisticated rich display support. Version 0.3.0 represents a mature, stable release.

### 📋 Remaining Tasks
- **SSE Updates**: Consider server-sent events for real-time updates
- **Additional Tests**: Integration and end-to-end testing
- **Enhanced Plotting**: Additional matplotlib and plotting support
- **Additional MIME Types**: Support for PDF, video, and other rich media

## REST API for AI Agents

When running `plaque serve`, Plaque exposes comprehensive REST API endpoints that enable AI agents to interact with notebooks programmatically. This allows agents to query individual cells, inspect outputs, and understand notebook state without parsing HTML.

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

#### Get Cell Input/Output
```
GET /api/cell/{index}/input   # Returns just cell content
GET /api/cell/{index}/output  # Returns just execution results
```

#### Get Notebook State
```
GET /api/notebook/state
```
Returns overall notebook statistics including error cells and execution status.

#### Search Cells
```
GET /api/search?q=keyword
```
Search for cells containing specific text.

### Result Types
The API returns different result types based on cell output:
- **Text**: `{"type": "text/plain", "data": "..."}`
- **HTML**: `{"type": "text/html", "data": "<div>...</div>"}`
- **Images**: `{"type": "image/png", "url": "/images/img_001.png"}`
- **DataFrames**: `{"type": "dataframe", "shape": [3, 2], "columns": [...]}` 
- **JSON**: `{"type": "application/json", "data": {...}}`

## Dependency Tracking & Smart Re-execution

Plaque now includes sophisticated dependency analysis that tracks which variables each cell provides and requires. This enables smart re-execution where only modified cells and their dependents are re-run.

### How It Works
- **Variable Analysis**: Uses AST parsing to identify variable assignments (provides) and usage (requires)
- **Dependency Graph**: Builds relationships between cells based on variable flow
- **Smart Caching**: Only re-executes cells when their dependencies change
- **Execution Ordering**: Ensures cells run in dependency order, not just file order

### Benefits
- **Performance**: Expensive computations are cached until dependencies change
- **Consistency**: Guarantees notebook runs as if executed top-to-bottom
- **Reactivity**: Changes automatically propagate to dependent cells

## Testing
Comprehensive test suite covering:
- **Display System**: Method resolution, IPython methods, built-in types
- **Environment**: Code execution, error handling, variable persistence
- **Formatter**: HTML generation, template injection, styling
- **AST Parser**: Robust parsing of all cell formats and boundary detection
- **Dependency Analyzer**: Variable tracking and dependency graph construction
- **API Integration**: REST endpoints and JSON formatting
- **F-String Execution**: Dynamic template rendering
- **Server API**: Live server endpoints and agent integration

Run tests with: `uv run pytest tests/`

Test files include:
- `test_display.py`, `test_environment.py`, `test_formatter.py`
- `test_ast_parser.py`, `test_dependency_analyzer.py` 
- `test_api_formatter.py`, `test_api_integration.py`, `test_server_api.py`
- `test_fstring_execution.py`, `test_processor.py`
- `test_single_quote_strings.py`

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
- **AST-Based Parsing**: Robust parsing using Python's AST module for accurate cell boundary detection
- **Template System**: HTML template extracted to separate file for easy customization
- **Error Handling**: Comprehensive error capture with cleaned tracebacks filtering internal frames
- **Resource Management**: Proper cleanup of temp files, image assets, and file watchers
- **Security**: HTML escaping to prevent XSS attacks, safe code execution environment
- **API Architecture**: Clean separation between HTML rendering and JSON API for agent consumption
- **Dependency Management**: Sophisticated variable tracking with smart caching and re-execution
- **Stream Handling**: Proper stdout/stderr capture with mirroring for development visibility

This project successfully implements a clean, local-first notebook system that maintains the simplicity of Python files while providing rich interactive features.
