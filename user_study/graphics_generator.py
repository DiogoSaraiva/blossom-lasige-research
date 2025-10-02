#!/usr/bin/env python3
"""
generate_graphs_userstudy.py

Generate exploratory graphs for the user study dataset.
CSV format expected: ID, time_mimic, time_dancer, switches, dancing_time(%), notes
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import argparse
import re
import os

sns.set(style="whitegrid", context="talk", palette="Set2")

OUTPUT_DIR = "graphs"  
os.makedirs(OUTPUT_DIR, exist_ok=True)

def parse_percentage(s):
    """Convert '10.6%' into float"""
    if isinstance(s, str):
        return float(s.strip('%'))
    return s

def boxplot_variable(df, var, ylabel, title, filename, color:str):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.boxplot(y=var, data=df, showfliers=True, color=color)
    sns.stripplot(y=var, data=df, color="black", alpha=0.6)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("")
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


def scatter_with_regression(df, x, y, title, filename, color1:str, color2:str):
    outpath = os.path.join(OUTPUT_DIR, filename)
    plt.figure(figsize=(7, 5))
    ax = sns.scatterplot(data=df, x=x, y=y, s=80, color=color1)
    sns.regplot(data=df, x=x, y=y, scatter=False, color=color2, ci=95)
    ax.set_title(title)
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

    # --------- trocamos APENAS a ordem da LEGENDA ---------
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], title="Robot")
    # -------------------------------------------------------

    plt.title("Average time distribution: Mimic vs Dancer")
    plt.ylabel("Time (s)")
    plt.xticks([])
    plt.tight_layout()
    plt.savefig(outpath)
    plt.close()


def main(color1:str, color2:str):
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
    if "time_mimic" in df.columns:
        df["time_mimic"] = df["time_mimic"]
    if "time_dancer" in df.columns:
        df["time_dancer"] = df["time_dancer"]
    if "dancing_time(%)" in df.columns:
        df["dancing_time(%)"] = df["dancing_time"]

    # Boxplots
    if "time_mimic" in df.columns:
        boxplot_variable(df, "time_mimic", "Time (s)", "Time looking at Mimic", "box_time_mimic.png", color1)
    if "switches" in df.columns:
        boxplot_variable(df, "switches", "Participants", "Number of gaze switches", "box_switches.png",  color1)
    if "dancing_time(%)" in df.columns:
        boxplot_variable(df, "dancing_time(%)", "Percentage (%)", "Dancing time (%)", "box_dancing_time.png", color1)

    # Histograms
    if "switches" in df.columns:
        histogram_variable(df, "switches", "Distribution of gaze switches","hist_switches.png",color1)
    if "dancing_time(%)" in df.columns:
        histogram_variable(df,  "dancing_time(%)", "Distribution of dancing time (%)", "hist_dancing_time.png", color1)

    # Scatter dancing_time vs switches
    if "dancing_time(%)" in df.columns and "switches" in df.columns:
        scatter_with_regression(df, "dancing_time(%)", "switches",
                                "Relation between dancing time (%) and gaze switches", "scatter_dancing_switches.png", color1, color2)

    # Stacked bar (TOM vs JERRY)
    if "time_mimic" in df.columns and "time_dancer" in df.columns:
        stacked_bar(df, "stacked_time.png", color1, color2)

    print(f"Graphs generated successfully! Check the '{OUTPUT_DIR}/' folder.")


if __name__ == "__main__":
    main(color1="#C340A2", color2="#A2007B")
