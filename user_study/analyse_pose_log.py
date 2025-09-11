#!/usr/bin/env python3
"""
analyze_pose_log.py

Load a line-delimited JSON pose log and:
 - summarize numeric fields (mean/std/min/max/count)
 - compute gaze time per label (center/left/right)
 - count gaze switches (center<->left<->right transitions)
 - print a short report
"""
import json
import argparse
from collections import Counter
from datetime import datetime
import numpy as np
from typing import List, Any, Dict, Optional


def load_pose_logs(filepath: str) -> List[Dict]:
    logs = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return logs


def safe_parse_timestamp(ts_val: Any) -> Optional[float]:
    if ts_val is None:
        return None
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str):
        s = ts_val.strip()
        try:
            return float(s)
        except Exception:
            pass
        try:
            if s.endswith("Z"):
                s = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            return dt.timestamp()
        except Exception:
            return None
    return None


def compute_frame_durations(entries: List[Dict], default_fps: float) -> List[float]:
    ts_list: List[Optional[float]] = []
    for e in entries:
        ts = e.get("timestamp") or e.get("ts") or e.get("time")
        ts_list.append(safe_parse_timestamp(ts))

    if any(t is not None for t in ts_list):
        durations: List[float] = []
        n = len(entries)
        for i in range(n):
            t = ts_list[i]
            if t is None:
                fps = entries[i].get("fps", default_fps)
                durations.append(1.0 / float(fps))
            else:
                if i < n - 1 and ts_list[i + 1] is not None:
                    durations.append(max(0.0, ts_list[i + 1] - t))
                else:
                    fps = entries[i].get("fps", default_fps)
                    durations.append(1.0 / float(fps))
        return durations
    else:
        durations = []
        for e in entries:
            fps = e.get("fps", default_fps)
            durations.append(1.0 / float(fps))
        return durations


def find_gaze_label(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        if "gaze" in obj and isinstance(obj["gaze"], dict):
            lbl = obj["gaze"].get("label")
            if isinstance(lbl, str):
                return lbl.lower().strip()
        for v in obj.values():
            res = find_gaze_label(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = find_gaze_label(item)
            if res:
                return res
    return None


def normalize_gaze_label(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    r = raw.lower()
    if "center" in r or "centre" in r or "middle" in r:
        return "center"
    if "left" in r:
        return "left"
    if "right" in r:
        return "right"
    return None


def gaze_analysis(entries: List[Dict], default_fps: float = 30.0):
    durations = compute_frame_durations(entries, default_fps=default_fps)
    counter = Counter()
    frames_labels: List[Optional[str]] = []

    for entry, dur in zip(entries, durations):
        raw = find_gaze_label(entry)
        label = normalize_gaze_label(raw)
        frames_labels.append(label)
        if label:
            counter[label] += dur

    # Percentages
    total_time = sum(counter.values())
    percentages = {k: (v / total_time * 100.0) if total_time > 0 else 0.0 for k, v in counter.items()}

    # Switches
    switches = 0
    switch_types = Counter()
    prev = None
    for lbl in frames_labels:
        if lbl and prev and lbl != prev:
            switches += 1
            switch_types[f"{prev}->{lbl}"] += 1
        if lbl:
            prev = lbl

    return dict(counter), percentages, switches, dict(switch_types)


def extract_numeric_values(logs: List[Dict]) -> Dict[str, List[float]]:
    data: Dict[str, List[float]] = {}

    def recursive_extract(prefix: str, d: Any):
        if isinstance(d, dict):
            for k, v in d.items():
                name = f"{prefix}_{k}" if prefix else k
                if isinstance(v, (int, float)):
                    data.setdefault(name, []).append(float(v))
                else:
                    recursive_extract(name, v)
        elif isinstance(d, list):
            for i, item in enumerate(d):
                recursive_extract(f"{prefix}_{i}" if prefix else str(i), item)

    for entry in logs:
        if "data" in entry and isinstance(entry["data"], dict):
            recursive_extract("", entry["data"])
    return data


def summarize_data(data: Dict[str, List[float]]) -> Dict[str, Dict]:
    summary = {}
    for key, vals in data.items():
        arr = np.array(vals, dtype=float)
        summary[key] = {
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "count": int(arr.size),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Analyze pose log (numeric + gaze + switches).")
    parser.add_argument("logfile", help="line-delimited JSON logfile")
    parser.add_argument("--default-fps", type=float, default=30.0)
    args = parser.parse_args()

    entries = load_pose_logs(args.logfile)
    if not entries:
        print("No entries found.")
        return

    # Numeric
    numeric_data = extract_numeric_values(entries)
    summary = summarize_data(numeric_data)
    print("\n📊 Numeric Summary:")
    for var, stats in sorted(summary.items()):
        print(f"\n{var}:")
        for stat, val in stats.items():
            print(f"  {stat}: {val:.4f}" if isinstance(val, float) else f"  {stat}: {val}")

    # Gaze + Switches
    counter, percentages, switches, switch_types = gaze_analysis(entries, default_fps=args.default_fps)
    print("\n👀 Gaze time distribution:")
    for lbl in ["center", "left", "right"]:
        print(f"  {lbl}: {counter.get(lbl, 0.0):.2f}s ({percentages.get(lbl, 0.0):.1f}%)")

    print(f"\n🔄 Gaze switches: {switches}")
    for trans, n in switch_types.items():
        print(f"  {trans}: {n}")


if __name__ == "__main__":
    main()
