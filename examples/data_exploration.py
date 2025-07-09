"""
# 🌟 Interactive Data Science with Plaque
### A comprehensive example showcasing rich displays and live updates

This notebook demonstrates the power of Plaque for interactive data science workflows.
We'll explore climate data, create visualizations, and build interactive analyses.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from IPython.display import HTML, display
import warnings

warnings.filterwarnings("ignore")

# Set up plotting style
try:
    import seaborn as sns

    plt.style.use("seaborn-v0_8")
    sns.set_palette("husl")
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
    plt.style.use("default")
    plt.rcParams["figure.figsize"] = (10, 6)
    plt.rcParams["axes.grid"] = True

"""
## 📊 Generating Sample Climate Data

Let's create a realistic dataset of temperature and precipitation data for different cities.
This simulates what you might work with in a real climate analysis project.
"""

# Generate sample data
np.random.seed(42)
cities = ["New York", "London", "Tokyo", "Sydney", "São Paulo", "Cairo"]
months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Create temperature data (°C)
temp_data = {
    "New York": [-2, 1, 6, 12, 18, 23, 26, 25, 21, 15, 8, 2],
    "London": [4, 5, 7, 10, 14, 17, 19, 19, 16, 12, 7, 5],
    "Tokyo": [5, 6, 10, 15, 20, 24, 27, 28, 24, 18, 13, 8],
    "Sydney": [22, 22, 20, 17, 14, 11, 10, 12, 15, 18, 20, 21],
    "São Paulo": [21, 21, 20, 18, 16, 15, 15, 17, 19, 19, 20, 20],
    "Cairo": [14, 16, 20, 25, 30, 33, 34, 34, 31, 27, 21, 16],
}

# Add some realistic variation
for city in temp_data:
    temp_data[city] = [temp + np.random.normal(0, 2) for temp in temp_data[city]]

# Create the DataFrame
df_temp = pd.DataFrame(temp_data, index=months)
df_temp.index.name = "Month"

"""
### 📈 Temperature Data Overview
Here's our generated temperature data showing monthly averages across six major cities:
"""

df_temp.round(1)

"""
## 🎨 Interactive Visualizations

Let's create some beautiful visualizations to explore our data patterns.
"""

# Create a comprehensive visualization dashboard
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
fig.suptitle("🌍 Global Climate Analysis Dashboard", fontsize=16, fontweight="bold")

# 1. Line plot of temperature trends
month_indices = range(len(months))
for city in cities:
    ax1.plot(month_indices, df_temp[city], marker="o", linewidth=2, label=city)
ax1.set_title("Monthly Temperature Trends")
ax1.set_ylabel("Temperature (°C)")
ax1.set_xticks(month_indices)
ax1.set_xticklabels(months)
ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
ax1.grid(True, alpha=0.3)

# 2. Heatmap of temperatures
im = ax2.imshow(df_temp.T.values, cmap="RdYlBu_r", aspect="auto")
ax2.set_title("Temperature Heatmap")
ax2.set_xticks(range(len(months)))
ax2.set_xticklabels(months)
ax2.set_yticks(range(len(cities)))
ax2.set_yticklabels(cities)
plt.colorbar(im, ax=ax2, label="Temperature (°C)")

# 3. Temperature distribution
temp_flat = df_temp.values.flatten()
ax3.hist(temp_flat, bins=20, alpha=0.7, color="skyblue", edgecolor="black")
ax3.set_title("Temperature Distribution")
ax3.set_xlabel("Temperature (°C)")
ax3.set_ylabel("Frequency")
ax3.axvline(
    np.mean(temp_flat),
    color="red",
    linestyle="--",
    label=f"Mean: {np.mean(temp_flat):.1f}°C",
)
ax3.legend()

# 4. City temperature ranges
temp_ranges = df_temp.max() - df_temp.min()
city_indices = range(len(cities))
bars = ax4.bar(
    city_indices, temp_ranges, color=plt.cm.viridis(np.linspace(0, 1, len(cities)))
)
ax4.set_title("Temperature Range by City")
ax4.set_ylabel("Temperature Range (°C)")
ax4.set_xticks(city_indices)
ax4.set_xticklabels(cities, rotation=45, ha="right")

# Add value labels on bars
for bar, value in zip(bars, temp_ranges):
    ax4.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        f"{value:.1f}°C",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.show()

"""
## 📊 Statistical Analysis

Let's dive deeper into the data with some statistical insights.
"""

# Calculate statistics
stats_df = df_temp.describe().round(2)
stats_df

"""
### 🔍 Key Insights

Let's extract some interesting patterns from our data:
"""

# Find extreme temperatures
hottest_month = df_temp.max().idxmax()
hottest_temp = df_temp.max().max()
hottest_city = df_temp.loc[:, df_temp.max().idxmax()].idxmax()

coldest_month = df_temp.min().idxmin()
coldest_temp = df_temp.min().min()
coldest_city = df_temp.loc[:, df_temp.min().idxmin()].idxmin()

# Create insights display
insights = f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 20px; border-radius: 10px; color: white; margin: 10px 0;">
    <h3>🌡️ Climate Insights</h3>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
        <div>
            <h4>🔥 Hottest Recorded</h4>
            <p><strong>{hottest_temp:.1f}°C</strong> in {hottest_city} during {hottest_month}</p>
        </div>
        <div>
            <h4>🧊 Coldest Recorded</h4>
            <p><strong>{coldest_temp:.1f}°C</strong> in {coldest_city} during {coldest_month}</p>
        </div>
    </div>
</div>"""

HTML(insights)

"""
## 🌍 Correlation Analysis

Let's see how temperatures in different cities correlate with each other:
"""

# Correlation matrix
corr_matrix = df_temp.corr()

# Create correlation heatmap
plt.figure(figsize=(10, 8))
if HAS_SEABORN:
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True,
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
    )
else:
    im = plt.imshow(corr_matrix, cmap="coolwarm", aspect="auto")
    plt.colorbar(im, label="Correlation")
    plt.xticks(range(len(cities)), cities, rotation=45)
    plt.yticks(range(len(cities)), cities)
    # Add correlation values as text
    for i in range(len(cities)):
        for j in range(len(cities)):
            plt.text(
                j,
                i,
                f"{corr_matrix.iloc[i, j]:.2f}",
                ha="center",
                va="center",
                color="white" if abs(corr_matrix.iloc[i, j]) > 0.5 else "black",
            )
plt.title("🔗 Temperature Correlation Between Cities")
plt.tight_layout()
plt.show()

"""
## 📈 Interactive Data Table

Here's an interactive summary showing seasonal patterns:
"""

# Create seasonal analysis
seasons = {
    "Spring": ["Mar", "Apr", "May"],
    "Summer": ["Jun", "Jul", "Aug"],
    "Fall": ["Sep", "Oct", "Nov"],
    "Winter": ["Dec", "Jan", "Feb"],
}

seasonal_data = {}
for season, season_months in seasons.items():
    seasonal_data[season] = df_temp.loc[season_months].mean()

seasonal_df = pd.DataFrame(seasonal_data).round(1)
seasonal_df.index.name = "City"

# Style the DataFrame
styled_df = (
    seasonal_df.style.background_gradient(cmap="RdYlBu_r", axis=None)
    .set_caption("🍂 Seasonal Temperature Averages (°C)")
    .format(precision=1)
)

styled_df

"""
## 🎯 Advanced Visualization: Temperature Anomalies

Let's create a sophisticated plot showing temperature anomalies from the global average:
"""

# Calculate global average for each month
global_avg = df_temp.mean(axis=1)
anomalies = df_temp.subtract(global_avg, axis=0)

# Create anomaly visualization
fig, ax = plt.subplots(figsize=(14, 8))

# Plot anomalies as stacked area chart
x = np.arange(len(months))
bottom = np.zeros(len(months))

colors = plt.cm.Set3(np.linspace(0, 1, len(cities)))
for i, city in enumerate(cities):
    values = anomalies[city].values
    ax.fill_between(x, bottom, bottom + values, alpha=0.7, label=city, color=colors[i])
    bottom += values

ax.set_title(
    "🌡️ Temperature Anomalies from Global Average", fontsize=14, fontweight="bold"
)
ax.set_xlabel("Month")
ax.set_ylabel("Temperature Anomaly (°C)")
ax.set_xticks(x)
ax.set_xticklabels(months)
ax.axhline(y=0, color="black", linestyle="-", alpha=0.3)
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

"""
## 🚀 Real-time Data Processing

Let's simulate some real-time data processing that you might use with live updates:
"""

# Simulate real-time processing
processing_results = []
for i in range(5):
    # Simulate processing results without delay for notebook rendering
    result = {
        "iteration": i + 1,
        "avg_temp": np.random.normal(18, 5),
        "max_temp": np.random.normal(25, 3),
        "min_temp": np.random.normal(10, 4),
    }
    processing_results.append(result)

# Display processing results
results_df = pd.DataFrame(processing_results)
results_df["avg_temp"] = results_df["avg_temp"].round(1)
results_df["max_temp"] = results_df["max_temp"].round(1)
results_df["min_temp"] = results_df["min_temp"].round(1)

# Style the results
styled_results = (
    results_df.style.highlight_max(color="lightcoral", axis=0)
    .highlight_min(color="lightblue", axis=0)
    .set_caption("⚡ Real-time Processing Results")
)

styled_results

"""
## 🎉 Summary & Next Steps

This example demonstrates several key features of Plaque:

- **📊 Rich Data Display**: Pandas DataFrames render beautifully
- **📈 Interactive Plots**: Matplotlib figures with complex layouts
- **🎨 Custom HTML**: Styled insights and summaries
- **⚡ Live Updates**: Perfect for iterative data exploration
- **🔄 Real-time Processing**: Simulated streaming data analysis

### Try It Yourself!

1. Run `plaque serve examples/data_exploration.py --open` for live development
2. Modify the data generation parameters and see instant updates
3. Add your own analyses and visualizations
4. Experiment with different plotting styles and layouts

**Happy exploring with Plaque! 🌟**
"""

# Final statistics for the curious
print(f"📊 Dataset Summary:")
print(f"   • Cities analyzed: {len(cities)}")
print(f"   • Months covered: {len(months)}")
print(f"   • Total data points: {df_temp.size}")
print(f"   • Global average temperature: {df_temp.values.mean():.1f}°C")
print(
    f"   • Temperature range: {df_temp.values.min():.1f}°C to {df_temp.values.max():.1f}°C"
)
