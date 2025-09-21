#!/usr/bin/env python3
"""
generate_graphs_userstudy.py

Generate exploratory graphs for the user study dataset.
CSV format expected: ID, time_mimic (right), time_dancer (left), switches, dancing_time(%), notes
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import re
import os

sns.set(style="whitegrid", context="talk", palette="Set2")

TOTAL_TIME = 300.0  # fixed total time in seconds
OUTPUT_DIR = "graphs"  # pasta de saída para os gráficos
os.makedirs(OUTPUT_DIR, exist_ok=True)


def parse_time_percentage(s):
    """Convert '221.97s (74.0%)' into float seconds"""
    match = re.match(r"([\d\.]+)s", str(s))
    return float(match.group(1)) if match else None


def parse_percentage(s):
    """Convert '10.6%' into float"""
    if isinstance(s, str):
        return float(s.strip('%'))
    return s


def boxplot_variable(df, var, ylabel, title, filename):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.boxplot(y=var, data=df, showfliers=True)
    sns.stripplot(y=var, data=df, color="black", alpha=0.6)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def histogram_variable(df, var, title, filename):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.histplot(data=df, x=var, bins=10, color="steelblue", edgecolor="black")
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def scatter_with_regression(df, x, y, title, filename):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.scatterplot(data=df, x=x, y=y, s=80, color="darkred")
    sns.regplot(data=df, x=x, y=y, scatter=False, color="black", ci=95)
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def stacked_bar(df, filename):
    outpath = os.path.join(OUTPUT_DIR, filename)
    agg = df[["time_mimic (right)", "time_dancer (left)"]].mean()
    agg_df = pd.DataFrame({
        "mean_time": [agg["time_mimic (right)"], agg["time_dancer (left)"]],
        "role": ["TOM (mimic)", "JERRY (dancer)"]
    }).set_index("role")
    ax = agg_df.T.plot(kind="bar", stacked=True, figsize=(7, 5), color=["#66c2a5", "#fc8d62"])
    plt.title("Average time distribution: TOM vs JERRY")
    plt.ylabel("Time (s)")
    plt.xticks([])
    plt.legend()
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Generate graphs for user study results")
    parser.add_argument("csv", help="Path to results CSV")
    args = parser.parse_args()

    # Detect delimiter automatically
    try:
        df = pd.read_csv(args.csv, sep=None, engine='python')
    except Exception:
        df = pd.read_csv(args.csv)

    # Clean column names
    df.columns = [re.sub(r'\s+', ' ', col).strip() for col in df.columns]

    print("Colunas lidas do CSV:", df.columns.tolist())

    # Convert columns
    if "time_mimic (right)" in df.columns:
        df["time_mimic (right)"] = df["time_mimic (right)"].apply(parse_time_percentage)
    if "time_dancer (left)" in df.columns:
        df["time_dancer (left)"] = df["time_dancer (left)"].apply(parse_time_percentage)
    if "dancing_time(%)" in df.columns:
        df["dancing_time(%)"] = df["dancing_time(%)"].apply(parse_percentage)

    # Boxplots
    if "time_mimic (right)" in df.columns:
        boxplot_variable(df, "time_mimic (right)", "Time (s)", "Time looking at TOM", "box_time_mimic.png")
    if "switches" in df.columns:
        boxplot_variable(df, "switches", "Count", "Number of gaze switches", "box_switches.png")
    if "dancing_time(%)" in df.columns:
        boxplot_variable(df, "dancing_time(%)", "Percentage (%)", "Dancing time (%)", "box_dancing_time.png")

    # Histograms
    if "switches" in df.columns:
        histogram_variable(df, "switches", "Distribution of gaze switches", "hist_switches.png")
    if "dancing_time(%)" in df.columns:
        histogram_variable(df, "dancing_time(%)", "Distribution of dancing time (%)", "hist_dancing_time.png")

    # Scatter dancing_time vs switches
    if "dancing_time(%)" in df.columns and "switches" in df.columns:
        scatter_with_regression(df, "dancing_time(%)", "switches",
                                "Relation between dancing time (%) and gaze switches", "scatter_dancing_switches.png")

    # Stacked bar (TOM vs JERRY)
    if "time_mimic (right)" in df.columns and "time_dancer (left)" in df.columns:
        stacked_bar(df, "stacked_time.png")

    print(f"✅ Graphs generated successfully! Check the '{OUTPUT_DIR}/' folder.")


if __name__ == "__main__":
    main()
