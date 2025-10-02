#!/usr/bin/env python3
"""
generate_graphs_userstudy.py

Generate exploratory graphs for the user study dataset.
CSV format expected: ID, time_mimic, time_dancer, switches, notes
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import re
import os
import numpy as np

sns.set(style="whitegrid", context="talk", palette="Set2")

OUTPUT_DIR = "graphs"  
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_percentage(s):
    """Convert '10.6%' into float"""
    if isinstance(s, str):
        return float(s.strip('%'))
    return s

def boxplot_variable(df, var, ylabel, min, max, title, filename, color:str):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.boxplot(y=var, data=df, showfliers=True, color=color)
    sns.stripplot(y=var, data=df, color="black", alpha=0.6)
    ax.set_ylim(min, max)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()

def pie_chart(data, labels, title, filename, colors):
    outpath = os.path.join(OUTPUT_DIR, filename)
    colors=sns.color_palette(colors)

    plt.pie(data, labels=labels, colors=colors, autopct='%1.0f%%')
    plt.title(title)
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()

def histogram_variable(df, var, title, filename, color:str):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.histplot(data=df, x=var, bins=10, color=color, edgecolor="black")
    ax.set_title(title)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_ylabel("Participants")
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def stacked_bar(df, filename, color1:str, color2:str):
    outpath = os.path.join(OUTPUT_DIR, filename)

    # médias nas duas colunas do CSV
    agg = df[["time_mimic", "time_dancer"]].mean()

    # mantém a mesma construção do DF (nada muda no gráfico)
    agg_df = pd.DataFrame({
        "mean_time": [agg["time_mimic"], agg["time_dancer"]],
        "role": ["Mimic", "Dancer"]
    }).set_index("role")

    ax = agg_df.T.plot(kind="bar", stacked=True, figsize=(7, 5),
                       color=[color1, color2])  # mesmas cores do gráfico

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], title="Robot")

    plt.title("Average time distribution: Mimic vs Dancer")
    plt.ylabel("Time (s)")
    plt.xticks([])
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def main(colors):
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

    # Boxplots
    if "time_mimic" in df.columns:
        boxplot_variable(df, "time_mimic",  "Time (s)", 25, 100, "Time looking at Mimic", "box_time_mimic.png", colors[0])
    if "time_dancer" in df.columns:
        boxplot_variable(df, "time_dancer", "Time (s)", 25, 100, "Time looking at Dancer", "box_time_dancing.png", colors[0])

    if "switches" in df.columns:
        boxplot_variable(df, "switches", "Participants", 0, 40, "Number of gaze switches", "box_switches.png",  colors[0])

    # Histograms
    if "switches" in df.columns:
        histogram_variable(df, "switches", "Distribution of gaze switches","hist_switches.png",colors[0])

    # Stacked bar (TOM vs JERRY)
    if "time_mimic" in df.columns and "time_dancer" in df.columns:
        stacked_bar(df, "stacked_time.png", colors[2], colors[0])

    # Pie chart
    bins = np.arange(0, int(df["switches"].max()) + 5, 5)
    labels = [f"{bins[i]} - {bins[i + 1] - 1}" for i in range(len(bins) - 1)]
    groups = pd.cut(df["switches"], bins=bins, labels=labels, right=False)
    counts = groups.value_counts().sort_index()
    counts = counts[counts > 0]
    pie_chart(
        data=counts.values,
        labels=counts.index,
        title="Gaze switches (grouped)",
        filename="switches_pie_chart.png",
        colors=colors
    )

    print(f"Graphs generated successfully! Check the '{OUTPUT_DIR}/' folder.")


if __name__ == "__main__":
    main(colors=["#C340A2", "#BA1B92", "#830062", "#A2007A"])
