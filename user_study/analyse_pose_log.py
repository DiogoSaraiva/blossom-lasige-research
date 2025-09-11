#!/usr/bin/env python3
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
    """Try to parse timestamp value (float seconds or ISO string) -> unix seconds float."""
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
    """Return list of durations (seconds) for each entry.
    Use timestamp difference if timestamps present; otherwise use per-entry fps or default_fps.
    """
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
                try:
                    durations.append(max(0.0, 1.0 / float(fps)))
                except Exception:
                    durations.append(1.0 / default_fps)
            else:
                if i < n - 1 and ts_list[i + 1] is not None:
                    delta = ts_list[i + 1] - t
                    durations.append(max(0.0, float(delta)))
                else:
                    fps = entries[i].get("fps", default_fps)
                    try:
                        durations.append(max(0.0, 1.0 / float(fps)))
                    except Exception:
                        durations.append(1.0 / default_fps)
        return durations
    else:
        durations = []
        for e in entries:
            fps = e.get("fps", default_fps)
            try:
                durations.append(max(0.0, 1.0 / float(fps)))
            except Exception:
                durations.append(1.0 / default_fps)
        return durations


def find_gaze_label(obj: Any) -> Optional[str]:
    """Recursively search for a dict with key 'gaze' containing 'label' and return it."""
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


def gaze_time_distribution(entries: List[Dict], default_fps: float = 30.0):
    durations = compute_frame_durations(entries, default_fps=default_fps)
    counter = Counter()
    frames_with_label = 0
    frames_without_label = 0
    unknown_labels = Counter()

    for entry, dur in zip(entries, durations):
        raw = find_gaze_label(entry)
        label = normalize_gaze_label(raw)
        if label:
            counter[label] += dur
            frames_with_label += 1
        else:
            frames_without_label += 1
            if raw:
                unknown_labels[raw] += 1

    total_time = sum(counter.values())
    percentages = {k: (v / total_time * 100.0) if total_time > 0 else 0.0 for k, v in counter.items()}

    meta = {
        "frames_total": len(entries),
        "frames_with_label": frames_with_label,
        "frames_without_label": frames_without_label,
        "unknown_raw_labels": dict(unknown_labels),
        "total_gaze_time_seconds": total_time,
    }

    return dict(counter), percentages, meta


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
        for key, val in entry.items():
            if key == "data" and isinstance(val, dict):
                recursive_extract("", val)
            else:
                if isinstance(val, (int, float)):
                    data.setdefault(key, []).append(float(val))
                else:
                    recursive_extract(key, val)
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


def pretty_print_summary(summary: Dict[str, Dict]):
    print("\n📊 Summary of numeric variables:")
    for var, stats in sorted(summary.items()):
        print(f"\n{var}:")
        for stat, value in stats.items():
            if isinstance(value, float):
                print(f"  {stat}: {value:.4f}")
            else:
                print(f"  {stat}: {value}")


def pretty_print_gaze(counter: Dict[str, float], percentages: Dict[str, float], meta: Dict):
    print("\n👀 Gaze time distribution (seconds):")
    for label in ["center", "left", "right"]:
        t = counter.get(label, 0.0)
        pct = percentages.get(label, 0.0)
        print(f"  {label}: {t:.2f} s ({pct:.1f}%)")
    print("\nGaze meta:")
    for k, v in meta.items():
        print(f"  {k}: {v}")


def main():
    parser = argparse.ArgumentParser(description="Analyze pose log (numeric summary + gaze time).")
    parser.add_argument("logfile", help="line-delimited JSON logfile")
    parser.add_argument("--default-fps", type=float, default=30.0, help="fallback FPS if timestamps/fps missing")
    parser.add_argument("--use-timestamps", action="store_true", help="prefer timestamps if present")
    args = parser.parse_args()

    entries = load_pose_logs(args.logfile)
    if not entries:
        print("No entries found in log.")
        return

    # numeric summary
    numeric_data = extract_numeric_values(entries)
    summary = summarize_data(numeric_data)
    pretty_print_summary(summary)

    # gaze
    counter, percentages, meta = gaze_time_distribution(entries, default_fps=args.default_fps)
    pretty_print_gaze(counter, percentages, meta)


if __name__ == "__main__":
    main()
