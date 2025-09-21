#!/usr/bin/env python3
"""
analyze_pose_log.py

Load a line-delimited JSON pose log and:
 - summarize numeric fields (mean/std/min/max/count)
 - compute gaze time for left/right (based on ratio only)
 - count gaze switches (left <-> right transitions)
 - compute dancing_time (%) based on body movement
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


def classify_gaze_time(entry: Dict) -> Optional[str]:
    try:
        ratio = entry["data"]["gaze"]["ratio"]
        return "left" if ratio >= 0.5 else "right"
    except Exception:
        return None


def classify_gaze_switch(entry: Dict, dead_zone: float = 0.0) -> Optional[str]:
    try:
        ratio = entry["data"]["gaze"]["ratio"]
        if ratio >= 0.5 + dead_zone:
            return "left"
        elif ratio < 0.5 - dead_zone:
            return "right"
        else:
            return None
    except Exception:
        return None


def trim_entries(entries: List[Dict], durations: List[float], analysis_time: float = 300.0, warmup: float = 30.0):
    """Remove first `warmup` seconds and keep only `analysis_time` seconds, rescaling if needed."""
    total_time = 0.0
    trimmed_entries, trimmed_durations = [], []

    # Skip warmup period
    skipped_time = 0.0
    i = 0
    while i < len(durations) and skipped_time < warmup:
        skipped_time += durations[i]
        i += 1

    # Collect analysis period
    while i < len(durations) and total_time < analysis_time:
        trimmed_entries.append(entries[i])
        trimmed_durations.append(durations[i])
        total_time += durations[i]
        i += 1

    # Rescale durations to exactly analysis_time
    if total_time > 0:
        scale = analysis_time / total_time
        trimmed_durations = [d * scale for d in trimmed_durations]

    return trimmed_entries, trimmed_durations


def gaze_analysis(entries: List[Dict], durations: List[float], min_stable: int = 1, dead_zone: float = 0.0):
    counter = Counter()
    labels_for_switch: List[Optional[str]] = []

    for entry, dur in zip(entries, durations):
        label_time = classify_gaze_time(entry)
        if label_time:
            counter[label_time] += dur

        label_switch = classify_gaze_switch(entry, dead_zone=dead_zone)
        labels_for_switch.append(label_switch)

    total_time = sum(counter.values())
    percentages = {k: (v / total_time * 100.0) if total_time > 0 else 0.0 for k, v in counter.items()}

    switches = 0
    switch_types = Counter()
    prev = None
    stable_count = 0

    for lbl in labels_for_switch:
        if lbl == prev:
            stable_count += 1
        elif lbl is not None:
            if prev and stable_count >= min_stable:
                switches += 1
                switch_types[f"{prev}->{lbl}"] += 1
            prev = lbl
            stable_count = 1
        else:
            stable_count = 0

    return dict(counter), percentages, switches, dict(switch_types)


def compute_dancing_time(entries: List[Dict], durations: List[float], threshold: float = 5.0) -> float:
    dancing_seconds = 0.0
    total_seconds = sum(durations)
    prev_axis = None

    for entry, dur in zip(entries, durations):
        try:
            axis = entry["data"]["axis"]
            if prev_axis:
                dpitch = abs(axis["pitch"] - prev_axis["pitch"])
                droll = abs(axis["roll"] - prev_axis["roll"])
                dyaw = abs(axis["yaw"] - prev_axis["yaw"])
                if max(dpitch, droll, dyaw) > threshold:
                    dancing_seconds += dur
            prev_axis = axis
        except Exception:
            continue

    return (dancing_seconds / total_seconds * 100) if total_seconds > 0 else 0.0


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
    parser = argparse.ArgumentParser(description="Analyze pose log (5min after warmup + gaze + switches + dancing).")
    parser.add_argument("logfile", help="line-delimited JSON logfile")
    parser.add_argument("--default-fps", type=float, default=30.0)
    parser.add_argument("--min-stable", type=int, default=1)
    parser.add_argument("--dead-zone", type=float, default=0.0)
    args = parser.parse_args()

    entries = load_pose_logs(args.logfile)
    if not entries:
        print("No entries found.")
        return

    durations = compute_frame_durations(entries, default_fps=args.default_fps)
    entries, durations = trim_entries(entries, durations, analysis_time=300.0, warmup=30.0)

    numeric_data = extract_numeric_values(entries)
    summary = summarize_data(numeric_data)
    print("\n📊 Numeric Summary:")
    for var, stats in sorted(summary.items()):
        print(f"\n{var}:")
        for stat, val in stats.items():
            print(f"  {stat}: {val:.4f}" if isinstance(val, float) else f"  {stat}: {val}")

    counter, percentages, switches, switch_types = gaze_analysis(
        entries, durations, min_stable=args.min_stable, dead_zone=args.dead_zone
    )
    print("\n👀 Gaze time distribution:")
    for lbl in ["left", "right"]:
        print(f"  {lbl}: {counter.get(lbl, 0.0):.2f}s ({percentages.get(lbl, 0.0):.1f}%)")

    print(f"\n🔄 Gaze switches: {switches}")
    for trans, n in switch_types.items():
        print(f"  {trans}: {n}")

    dancing_percent = compute_dancing_time(entries, durations)
    print(f"\n🕺 Dancing time: {dancing_percent:.2f}% of total session")


if __name__ == "__main__":
    main()
