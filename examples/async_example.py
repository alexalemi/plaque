"""
# Async/Await Example

This notebook demonstrates top-level await support in Plaque when using the IPython backend.

Run with: `plaque serve --ipython examples/async_example.py`
"""

# %%
import asyncio
import time

"""
## Defining Async Functions

First, let's define some async functions to work with:
"""


# %%
async def fetch_data(delay: float, data: str) -> str:
    """Simulate fetching data with a delay."""
    await asyncio.sleep(delay)
    return f"Fetched: {data}"


async def process_data(data: str) -> str:
    """Simulate processing data."""
    await asyncio.sleep(0.1)
    return f"Processed: {data.upper()}"


"""
## Using Top-Level Await

With the IPython backend, you can use `await` directly at the top level:
"""

# %%
# This works with --ipython flag!
result = await fetch_data(0.5, "hello world")
print(result)

# %%
# You can chain async operations
data = await fetch_data(0.3, "plaque notebook")
processed = await process_data(data)
processed

# %%
"""
## Running Multiple Async Tasks

You can also run multiple async tasks concurrently:
"""

# %%
# Run multiple tasks concurrently
start = time.time()

task1 = asyncio.create_task(fetch_data(1.0, "task 1"))
task2 = asyncio.create_task(fetch_data(1.0, "task 2"))
task3 = asyncio.create_task(fetch_data(1.0, "task 3"))

results = await asyncio.gather(task1, task2, task3)
elapsed = time.time() - start

print(f"Completed {len(results)} tasks in {elapsed:.2f} seconds")
for r in results:
    print(f"  - {r}")

# %%
"""
## Async Context Managers

Top-level async context managers also work:
"""


# %%
class AsyncResource:
    def __init__(self, name: str):
        self.name = name

    async def __aenter__(self):
        print(f"Acquiring {self.name}")
        await asyncio.sleep(0.2)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f"Releasing {self.name}")
        await asyncio.sleep(0.1)

    async def do_work(self):
        return f"Work done by {self.name}"


# %%
# Use async context manager at top level
async with AsyncResource("my-resource") as resource:
    result = await resource.do_work()
    print(result)

# %%
"""
## Benefits of IPython Backend

When using `plaque serve --ipython`:

1. **Top-level await**: Use `await` directly without wrapping in async functions
2. **Magic commands**: Access to IPython magics like `%time`, `%timeit`
3. **Shell commands**: Run shell commands with `!command`
4. **Better introspection**: Use `?object` for help
5. **Rich display**: Enhanced output formatting

Try running this notebook with:
```bash
plaque serve --ipython examples/async_example.py
```

Then compare with the standard Python backend:
```bash
plaque serve examples/async_example.py
```

(The standard backend will show errors for top-level await)
"""
