import json
import numpy as np
import argparse


def load_pose_logs(filepath: str):
    """Load pose logs from a line-delimited JSON file."""
    logs = []
    with open(filepath, "r") as f:
        for line in f:
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return logs


def extract_numeric_values(logs):
    """Extract all numeric values from logs, recursively handling nested dicts."""
    data = {}

    def recursive_extract(prefix, d):
        for key, value in d.items():
            var_name = f"{prefix}_{key}" if prefix else key
            if isinstance(value, (int, float)):
                data.setdefault(var_name, []).append(value)
            elif isinstance(value, dict):
                recursive_extract(var_name, value)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        recursive_extract(f"{var_name}_{i}", item)
                    elif isinstance(item, (int, float)):
                        data.setdefault(f"{var_name}_{i}", []).append(item)

    for entry in logs:
        if "data" in entry and isinstance(entry["data"], dict):
            recursive_extract("", entry["data"])

    return data


def summarize_data(data):
    """Summarize numeric variables with basic stats."""
    summary = {}
    for key, values in data.items():
        arr = np.array(values)
        summary[key] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "count": len(arr),
        }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize pose logs from a JSON file.")
    parser.add_argument("logfile", type=str, help="Path to the pose log JSON file")
    args = parser.parse_args()

    pose_logs = load_pose_logs(args.logfile)
    numeric_data = extract_numeric_values(pose_logs)
    summary = summarize_data(numeric_data)

    print(f"\n📊 Summary of {args.logfile}:")
    for var, stats in summary.items():
        print(f"\n{var}:")
        for stat, value in stats.items():
            print(f"  {stat}: {value:.4f}" if isinstance(value, float) else f"  {stat}: {value}")
