# IPython Backend for Plaque

Plaque now supports an optional IPython execution backend that enables advanced features like top-level `await`, magic commands, and shell integration.

## Installation

To use the IPython backend, install the optional dependencies:

```bash
pip install plaque[ipython]
# or
pip install jupyter-client ipykernel
```

## Usage

Enable the IPython backend with the `--ipython` flag:

```bash
# Render with IPython backend
plaque render --ipython notebook.py

# Start live server with IPython backend
plaque serve --ipython notebook.py

# Watch mode with IPython backend
plaque watch --ipython notebook.py output.html
```

## Features

### Top-Level Await

The most exciting feature is support for top-level `await`:

```python
# %%
import asyncio

async def get_data():
    await asyncio.sleep(1)
    return "data ready!"

# This works with --ipython!
result = await get_data()
print(result)
```

### IPython Magic Commands

Access all IPython magic commands:

```python
# %%
# Time a code snippet
%time sum(range(1000000))

# %%
# Profile memory usage
%memit numpy.random.random((1000, 1000))

# %%
# Load external file
%load utils.py
```

### Shell Commands

Run shell commands directly:

```python
# %%
!pip list | grep plaque

# %%
files = !ls *.py
print(f"Found {len(files)} Python files")
```

### Better Introspection

```python
# %%
# Get help on objects
import pandas as pd
pd.DataFrame?

# %%
# See source code
pd.read_csv??
```

## Configuration

### Kernel Timeout

Set execution timeout for long-running cells:

```bash
# 60 second timeout
plaque serve --ipython --kernel-timeout 60 notebook.py
```

### Fallback to Standard Backend

If IPython is not available, Plaque automatically falls back to the standard Python backend:

```bash
# Uses IPython if available, otherwise standard Python
plaque serve --ipython notebook.py
```

## Differences from Standard Backend

### Advantages
- **Top-level await**: Use async/await without wrapper functions
- **Magic commands**: %time, %debug, %load, etc.
- **Shell integration**: !commands
- **Better errors**: Enhanced tracebacks and debugging
- **IPython extensions**: Access to IPython ecosystem

### Trade-offs
- **Startup time**: IPython kernel takes longer to start (~1-2s)
- **Memory usage**: Higher memory footprint due to kernel process
- **Dependencies**: Requires jupyter-client and ipykernel

## Example Notebooks

See `examples/async_example.py` for a complete demonstration of async/await capabilities.

## Troubleshooting

### Kernel Not Starting

If the IPython kernel fails to start:

1. Check dependencies:
   ```bash
   pip install jupyter-client ipykernel
   ```

2. Verify kernel is available:
   ```bash
   jupyter kernelspec list
   ```

3. Try with standard backend:
   ```bash
   plaque serve notebook.py  # without --ipython
   ```

### Performance Issues

If execution is slow:

1. Increase timeout:
   ```bash
   plaque serve --ipython --kernel-timeout 60 notebook.py
   ```

2. Check for blocking async operations
3. Monitor kernel memory usage

## Implementation Details

The IPython backend:
- Uses `jupyter_client` to manage IPython kernels
- Maintains kernel state across cell executions
- Automatically handles message protocol
- Converts IPython output formats to Plaque renderables
- Preserves dependency tracking and caching