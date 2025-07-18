"""
# MCP Test Notebook
This notebook demonstrates the MCP (Model Context Protocol) server functionality.
"""

import pandas as pd
import numpy as np

# Create some test data
data = {"x": [1, 2, 3, 4, 5], "y": [2, 4, 6, 8, 10]}
df = pd.DataFrame(data)

"""
## Data Analysis
Let's analyze the data:
"""

# Basic statistics
mean_x = df["x"].mean()
mean_y = df["y"].mean()

print(f"Mean of x: {mean_x}")
print(f"Mean of y: {mean_y}")

# Create a relationship
z = df["x"] * df["y"]
print(f"Product sum: {z.sum()}")

"""
## Potential Issues
This cell demonstrates some code quality issues:
"""

# TODO: This should be refactored
password = "secret123"  # Security issue
result = eval("2 + 2")  # Security issue

# Performance issue example
for i in range(len(df)):
    print(df.iloc[i])

"""
## Error Example
This cell will produce an error:
"""

error_result = 1 / 0  # This will cause a ZeroDivisionError
