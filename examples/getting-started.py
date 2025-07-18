"""
# 🌟 Getting Started with Plaque

Welcome to **Plaque** - the interactive Python notebook system that turns your regular Python files into beautiful, live-updating notebooks!

This getting-started guide will teach you everything you need to know to become productive with Plaque in just a few minutes.

## What Makes Plaque Special?

✅ **Local-first** - Your files stay on your computer
✅ **Real Python files** - No special format, just `.py` files
✅ **Live updates** - See changes instantly as you edit
✅ **Rich displays** - Beautiful HTML, plots, and visualizations
✅ **Your favorite editor** - Use any text editor or IDE

Let's dive in!
"""

# %%
# This is a traditional cell marker - one of three ways to create cells in Plaque

print("Hello, Plaque! 🎉")

"""
## 📝 Three Ways to Create Cells

Plaque supports three different cell formats. Let's explore each one:

### 1. Traditional Markers (like above)
Use `# %%` to create code cells, just like in other notebook systems.
"""

# %%
# Another traditional cell
name = "Plaque User"
print(f"Welcome, {name}!")

"""
### 2. Multiline Comment Cells (Recommended)

This cell you're reading right now is a **multiline comment cell**. This is the recommended way to write markdown in Plaque because:

- More readable in your text editor
- Proper syntax highlighting
- Easy to write and edit
- Supports full Markdown and LaTeX: $E = mc^2$

Just use triple quotes with your markdown content!
"""

# Let's create some variables to work with
user_name = "Alice"
favorite_number = 42
hobbies = ["reading", "coding", "hiking"]

print(f"User: {user_name}")
print(f"Favorite number: {favorite_number}")
print(f"Hobbies: {', '.join(hobbies)}")

"""
### 3. Dynamic F-String Cells

The third type uses f-strings for dynamic content that updates based on your variables:
"""

f"""
### 👋 User Profile

**Name:** {user_name}  
**Lucky Number:** {favorite_number}  
**Hobbies:** {len(hobbies)} activities  

The user {user_name} has {len(hobbies)} hobbies and their favorite number is {favorite_number}.
"""

# Create some sample data to use in our examples
student_grades = {"Alice": 95, "Bob": 87, "Charlie": 92, "Diana": 98}

"""
## 🎨 Rich Display Features

One of Plaque's superpowers is rich display support. Let's explore different types of output:
"""

# The last expression in a cell is automatically displayed
student_grades

"""
### 📈 Simple Data Visualization

Stderr and stdout are captured and displayed in the notebook.
"""


def create_text_chart(data, title="Chart"):
    """Create a simple text-based bar chart"""
    max_value = max(data.values())
    print(f"\n📊 {title}")
    print("=" * 30)
    for name, value in data.items():
        bar_length = int((value / max_value) * 20)
        bar = "█" * bar_length
        print(f"{name:10} {bar} {value}")
    print("=" * 30)


create_text_chart(student_grades, "Student Grades")

"""
### 🌈 HTML Rich Display

Plaque supports rich HTML output for beautiful presentations:
"""

from IPython.display import HTML

# Simple HTML example - Plaque displays rich HTML automatically
HTML(f"""
<div style="border: 2px solid #4CAF50; border-radius: 8px; padding: 15px; 
           background: #f0f8ff; font-family: Arial;">
    <h3 style="color: #333; margin-top: 0;">📊 Student Grades</h3>
    <p><strong>Average:</strong> {sum(student_grades.values()) / len(student_grades):.1f}</p>
    <ul>
        {"".join([f"<li><strong>{name}:</strong> {grade}</li>" for name, grade in student_grades.items()])}
    </ul>
</div>
""")

"""
## 🔄 Live Updates & State Management

Plaque solves a key problem with traditional IPython notebooks: **state management**. In Jupyter notebooks, cells can be run out of order, creating confusing state where variables might not match what you see on screen.

Plaque takes a different approach:
- **Top-to-bottom execution**: Your notebook runs like a regular Python file, from top to bottom
- **Smart re-execution**: Only cells that changed (or depend on changed variables) are re-run
- **Predictable state**: What you see is always what you get - no hidden state surprises

Unlike systems like Marimo that have full dependency resolution, Plaque keeps it simple: it runs your code sequentially but only re-executes what's necessary. This gives you the benefits of live updates without the complexity of a full reactive system.

Change any value above and save to see instant, predictable updates!
"""


def fibonacci_sequence(n):
    """Generate the first n Fibonacci numbers"""
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]

    fib = [0, 1]
    for i in range(2, n):
        fib.append(fib[i - 1] + fib[i - 2])

    return fib


# Try changing this number and saving the file!
fib_count = 12
fibonacci_numbers = fibonacci_sequence(fib_count)

print(f"First {fib_count} Fibonacci numbers:")
print(fibonacci_numbers)

"""
### 🎲 Random Experiments

Let's create something fun that generates different results each time:
"""

import random


def roll_dice(num_dice=2, num_sides=6):
    """Roll some dice and return the results"""
    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
    total = sum(rolls)

    return {"rolls": rolls, "total": total, "average": total / num_dice}


# Roll some dice - try saving the file multiple times to see different results!
dice_result = roll_dice(3, 6)
print(f"🎲 Dice rolls: {dice_result['rolls']}")
print(f"Total: {dice_result['total']}")
print(f"Average: {dice_result['average']:.1f}")

"""
### 🎯 Try This Yourself!

Change values above and save to see instant updates:
- Change `fib_count` to 15
- Try `roll_dice(5, 10)` for 5 ten-sided dice  
- Add a new student to `student_grades`
- Modify the `user_name` variable

Each save triggers re-execution and live updates!
"""

"""
## 📊 Rich Data Displays

Plaque automatically displays DataFrames, plots, and other rich objects:
"""

"""
### 🐼 Pandas DataFrames

DataFrames are automatically displayed as HTML tables (requires: pip install pandas):
"""

import pandas as pd

# Create a sample DataFrame
df = pd.DataFrame(
    {
        "Student": list(student_grades.keys()),
        "Grade": list(student_grades.values()),
        "Letter": [
            "A" if g >= 90 else "B" if g >= 80 else "C" for g in student_grades.values()
        ],
    }
)

# DataFrames are automatically displayed as HTML tables
df

# You can also create more complex DataFrames with calculations
summary_df = pd.DataFrame(
    {
        "Metric": ["Total Students", "Average Grade", "Highest Grade", "Lowest Grade"],
        "Value": [
            len(student_grades),
            f"{sum(student_grades.values()) / len(student_grades):.1f}",
            max(student_grades.values()),
            min(student_grades.values()),
        ],
    }
)

summary_df

"""
### 🎬 Matplotlib Plots

Plots are automatically captured and displayed (requires: pip install matplotlib):
"""

import matplotlib.pyplot as plt

# Create a simple plot
x = list(range(1, 11))
y = [i**2 for i in x]

plt.figure(figsize=(10, 6))
plt.plot(x, y, "bo-", linewidth=2, markersize=8)
plt.title("Square Numbers", fontsize=16, fontweight="bold")
plt.xlabel("Number", fontsize=12)
plt.ylabel("Square", fontsize=12)
plt.grid(True, alpha=0.3)
plt.show()

# Also create a bar chart of our student grades
plt.figure(figsize=(10, 6))
names = list(student_grades.keys())
grades = list(student_grades.values())

bars = plt.bar(names, grades, color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"])
plt.title("Student Grades", fontsize=16, fontweight="bold")
plt.ylabel("Grade", fontsize=12)
plt.ylim(0, 100)

# Add value labels on bars
for bar, grade in zip(bars, grades):
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1,
        str(grade),
        ha="center",
        va="bottom",
        fontweight="bold",
    )

plt.tight_layout()
plt.show()

"""
## 🚀 How to Use This Notebook

Now that you've seen what Plaque can do, here's how to use it:

### 💻 Development Mode (Recommended)
```bash
plaque serve getting-started.py --open
```

This starts a live server that:
- ✅ Opens your notebook in the browser
- ✅ Updates automatically when you save changes
- ✅ Shows errors clearly if something goes wrong
- ✅ Lets you experiment and iterate quickly
- ✅ Exposes a REST API for programmatic access (perfect for agentic coding with assistants like Claude Code)

### 📄 Export Mode
```bash
plaque render getting-started.py output.html --open
```

This creates a static HTML file that you can:
- ✅ Share with others
- ✅ View without running Plaque
- ✅ Include in presentations or reports

### 👀 Watch Mode
```bash
plaque watch getting-started.py output.html --open
```

This watches for file changes and automatically regenerates the HTML.
"""


"""
## 🎪 What's Next?

✅ **Try other examples**: `simple_interactive.py`, `data_exploration.py`  
✅ **Create your own**: Any `.py` file can become a Plaque notebook  
✅ **Remember**: Use your favorite editor and save often for live updates!

**Happy coding with Plaque! 🌟**
"""
