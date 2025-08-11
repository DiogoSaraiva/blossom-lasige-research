import pandas as pd

df = pd.read_csv('population.csv')

stats_summary = {}

# Calculate statistics
stats_summary['time_forward_mean'] = df['time_forward'].mean()
stats_summary['time_forward_median'] = df['time_forward'].median()
stats_summary['time_forward_std'] = df['time_forward'].std()
stats_summary['time_forward_mode'] = df['time_forward'].mode()[0]

stats_summary['time_side_mean'] = df['time_side'].mean()
stats_summary['time_side_median'] = df['time_side'].median()
stats_summary['time_side_std'] = df['time_side'].std()
stats_summary['time_side_mode'] = df['time_side'].mode()[0]

stats_summary['switches_mean'] = df['switches'].mean()
stats_summary['switches_median'] = df['switches'].median()
stats_summary['switches_std'] = df['switches'].std()
stats_summary['switches_mode'] = df['switches'].mode()[0]

emotion_counts = df['emotion'].value_counts()

# Open file to write
with open('statistics.txt', 'w', encoding='utf-8') as f:
    f.write("=== Descriptive Statistics ===\n")
    for k, v in stats_summary.items():
        f.write(f"{k}: {v:.2f}\n")

    f.write("\n=== Emotion Counts ===\n")
    f.write(f"{emotion_counts.to_string()}\n")

    f.write("\n=== Automatic Conclusions ===\n")
    if stats_summary['time_forward_mean'] > stats_summary['time_side_mean']:
        f.write(f"On average, children spent more time looking at the front robot ({stats_summary['time_forward_mean']:.1f}s) than the side robot ({stats_summary['time_side_mean']:.1f}s).\n")
    else:
        f.write(f"On average, children spent more time looking at the side robot ({stats_summary['time_side_mean']:.1f}s) than the front robot ({stats_summary['time_forward_mean']:.1f}s).\n")

    f.write(f"The standard deviation for front observation time is {stats_summary['time_forward_std']:.1f}, indicating {'higher' if stats_summary['time_forward_std'] > stats_summary['time_side_std'] else 'lower'} variation compared to the side observation time ({stats_summary['time_side_std']:.1f}).\n")

    most_common_emotion = emotion_counts.idxmax()
    f.write(f"The most common emotion was '{most_common_emotion}' with {emotion_counts.max()} occurrences.\n")

    f.write(f"On average, each child switched gaze direction about {stats_summary['switches_mean']:.1f} times during the 10 minutes.\n")

    f.write("\nAnalysis complete.\n")

print("Statistics saved to statistics.txt")
