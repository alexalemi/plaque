"""
# 🚀 Simple Interactive Example with Plaque

This example demonstrates Plaque's core features with minimal dependencies.
Perfect for getting started or troubleshooting!
"""

import math
import random
from IPython.display import HTML

"""
## 🔢 Basic Math Operations

Let's start with some simple calculations and see how Plaque displays results:
"""

# Basic arithmetic
x = 42
y = 7
result = x + y

print(f"Adding {x} + {y} = {result}")

"""
The result above shows how Plaque captures and displays print output beautifully.
"""

result

"""
## 📊 Working with Lists and Data

Let's create some sample data and manipulate it:
"""

# Generate sample data
data = [random.randint(1, 100) for _ in range(10)]
print("Sample data:", data)

# Calculate statistics
mean_value = sum(data) / len(data)
max_value = max(data)
min_value = min(data)

stats = {
    'mean': round(mean_value, 2),
    'max': max_value,
    'min': min_value,
    'range': max_value - min_value
}

stats

"""
## 🎨 HTML Visualization

Plaque supports rich HTML output for custom visualizations:
"""

# Create a simple HTML bar chart
def create_bar_chart(data, title="Bar Chart"):
    max_val = max(data)
    bars = []
    
    for i, value in enumerate(data):
        height = int((value / max_val) * 100)
        bar = f"""
        <div style="display: inline-block; margin: 2px; text-align: center; vertical-align: bottom;">
            <div style="background: linear-gradient(to top, #4CAF50, #81C784); 
                        width: 30px; height: {height}px; margin-bottom: 5px;
                        border-radius: 3px 3px 0 0;"></div>
            <div style="font-size: 12px; color: #666;">{value}</div>
        </div>
        """
        bars.append(bar)
    
    chart_html = f"""
    <div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px; 
                background: #f9f9f9; margin: 10px 0;">
        <h3 style="color: #333; margin-top: 0;">{title}</h3>
        <div style="display: flex; align-items: end; justify-content: center; 
                    padding: 20px; background: white; border-radius: 4px;">
            {''.join(bars)}
        </div>
    </div>
    """
    return HTML(chart_html)

create_bar_chart(data, "📊 Sample Data Distribution")

"""
## 🔄 Interactive Functions

Let's create some functions that you can easily modify and see results instantly:
"""

def fibonacci(n):
    """Generate Fibonacci sequence up to n terms"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    
    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i-1] + fib[i-2])
    return fib

# Generate Fibonacci sequence
fib_sequence = fibonacci(10)
print("Fibonacci sequence (10 terms):", fib_sequence)

"""
## 🎲 Random Experiments

Let's simulate some random experiments:
"""

# Simulate coin flips (using random module imported at the top)
def coin_flip_simulation(n_flips):
    flips = ['H' if random.random() > 0.5 else 'T' for _ in range(n_flips)]
    heads = flips.count('H')
    tails = flips.count('T')
    
    return {
        'flips': flips,
        'heads': heads,
        'tails': tails,
        'head_percentage': round(heads / n_flips * 100, 1)
    }

# Run simulation
coin_results = coin_flip_simulation(20)
print(f"Coin flips: {''.join(coin_results['flips'])}")
print(f"Heads: {coin_results['heads']}, Tails: {coin_results['tails']}")
print(f"Head percentage: {coin_results['head_percentage']}%")

"""
## 🎯 Mathematical Visualizations

Let's create some mathematical patterns using basic HTML:
"""

def create_multiplication_table(n):
    """Create a colorful multiplication table"""
    table_html = f"""
    <div style="border: 1px solid #ddd; padding: 15px; border-radius: 8px; 
                background: #f5f5f5; margin: 10px 0;">
        <h3 style="color: #333; margin-top: 0;">🔢 Multiplication Table ({n}×{n})</h3>
        <table style="border-collapse: collapse; margin: 0 auto;">
    """
    
    for i in range(1, n + 1):
        table_html += "<tr>"
        for j in range(1, n + 1):
            product = i * j
            # Color based on value
            if product <= 10:
                color = "#e8f5e8"
            elif product <= 25:
                color = "#fff3cd"
            else:
                color = "#f8d7da"
            
            table_html += f"""
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center; 
                       background: {color}; min-width: 40px;">
                {product}
            </td>
            """
        table_html += "</tr>"
    
    table_html += "</table></div>"
    return HTML(table_html)

create_multiplication_table(8)

"""
## 📈 Simple Data Analysis

Let's analyze our random data:
"""

# Analyze the data we created earlier
def analyze_data(data):
    analysis = {
        'count': len(data),
        'sum': sum(data),
        'mean': round(sum(data) / len(data), 2),
        'median': sorted(data)[len(data) // 2],
        'mode': max(set(data), key=data.count),
        'unique_values': len(set(data))
    }
    return analysis

analysis_results = analyze_data(data)

# Display as a nice formatted table
analysis_html = """
<div style="border: 1px solid #ddd; padding: 20px; border-radius: 8px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; margin: 10px 0;">
    <h3 style="margin-top: 0;">📊 Data Analysis Results</h3>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;"> """

for key, value in analysis_results.items():
    analysis_html += f"""
    <div style="background: rgba(255,255,255,0.1); padding: 10px; 
                border-radius: 5px; text-align: center;">
        <div style="font-size: 12px; opacity: 0.8;">{key.replace('_', ' ').title()}</div>
        <div style="font-size: 18px; font-weight: bold;">{value}</div>
    </div> """

analysis_html += """
    </div>
</div> """

HTML(analysis_html)

"""
## 🎪 Fun with Patterns

Let's create some visual patterns:
"""

def create_pattern(pattern_type="triangle", size=5):
    """Create ASCII art patterns"""
    if pattern_type == "triangle":
        pattern = []
        for i in range(1, size + 1):
            pattern.append("*" * i)
        return "\n".join(pattern)
    elif pattern_type == "diamond":
        pattern = []
        # Upper half
        for i in range(1, size + 1):
            pattern.append(" " * (size - i) + "*" * (2 * i - 1))
        # Lower half
        for i in range(size - 1, 0, -1):
            pattern.append(" " * (size - i) + "*" * (2 * i - 1))
        return "\n".join(pattern)

# Display patterns
print("🔺 Triangle Pattern:")
print(create_pattern("triangle", 7))

print("\n💎 Diamond Pattern:")
print(create_pattern("diamond", 5))

"""
## 🎯 Final Summary

This example demonstrates:

- **✅ Basic Python operations** with live output
- **📊 Data manipulation** and analysis
- **🎨 Rich HTML displays** for custom visualizations
- **🔄 Interactive functions** that update in real-time
- **📈 Simple data analysis** techniques
- **🎪 Creative patterns** and visualizations

### 🚀 Try It Yourself!

1. Run `plaque serve examples/simple_interactive.py --open`
2. Modify any values and save to see instant updates
3. Experiment with the functions and create your own!

**Perfect for learning, experimenting, and having fun with Plaque!**
"""

# One final calculation to show the magic
magic_number = sum(range(1, 11))  # Sum of 1 to 10
print(f"🎯 The magic number is: {magic_number}")
print("🎉 Thanks for trying Plaque!")
