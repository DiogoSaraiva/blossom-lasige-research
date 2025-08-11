import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Style configuration
sns.set(style="whitegrid")

# Read the data
df = pd.read_csv('population.csv')

# 1. Bar chart: emotion distribution
plt.figure(figsize=(8, 6))
sns.countplot(x='emotion', data=df, palette='pastel')
plt.title('Emotion Distribution')
plt.xlabel('Emotion')
plt.ylabel('Number of Children')
plt.tight_layout()
# plt.savefig('bar_chart_emotions.png')
plt.show()

# 2. Line chart: time vs IDs
plt.figure(figsize=(12, 6))
plt.plot(df['id'], df['time_front'], label='Time looking at front', color='blue', marker='o')
plt.plot(df['id'], df['time_side'], label='Time looking at side', color='green', marker='o')
plt.title('Looking Time vs Children')
plt.xlabel('Child ID')
plt.ylabel('Time (seconds)')
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
# plt.savefig('line_chart_times.png')
plt.show()

# 3. Boxplot: number of switches
plt.figure(figsize=(8, 6))
sns.boxplot(y='switches', data=df, palette='pastel')
plt.title('Switch Count Distribution')
plt.ylabel('Number of Switches')
plt.tight_layout()
# plt.savefig('boxplot_switches.png')
plt.show()

# 4. Histogram: time looking at front
plt.figure(figsize=(8, 6))
sns.histplot(df['time_front'], bins=10, kde=True, color='skyblue')
plt.title('Distribution of Time Looking at Front')
plt.xlabel('Time (seconds)')
plt.ylabel('Frequency')
plt.tight_layout()
# plt.savefig('histogram_time_front.png')
plt.show()

print("Charts generated successfully!")
