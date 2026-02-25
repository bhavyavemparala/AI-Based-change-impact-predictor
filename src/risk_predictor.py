#!/usr/bin/env python3
# Rule-based Change Impact Predictor (prototype)

import argparse
import json
import os
from typing import List, Dict, Tuple

CRITICAL_COMPONENTS = {"PAD", "RPSW", "ALSW", "Auth", "Billing", "DB", "Core", "NIC"}
HIGH_RISK_CHANGE_TYPES = {"config_core", "schema", "dependency_upgrade_major"}
MEDIUM_RISK_CHANGE_TYPES = {"config", "dependency_upgrade_minor"}

def magnitude_score(lines_added: int, lines_removed: int) -> float:
    """Score based on magnitude of change."""
    delta = max(0, lines_added) + max(0, lines_removed)
    if delta >= 800:
        return 55.0
    if delta >= 500:
        return 45.0
    if delta >= 200:
        return 30.0
    if delta >= 50:
        return 15.0
    return 5.0 if delta > 0 else 0.0

def spread_score(num_files: int, num_components: int) -> float:
    """Score based on spread/blast radius."""
    s = 0.0
    if num_files >= 5:
        s += 20.0
    elif num_files >= 3:
        s += 12.0
    elif num_files >= 2:
        s += 6.0
    if num_components >= 3:
        s += 20.0
    elif num_components == 2:
        s += 10.0
    elif num_components == 1:
        s += 3.0
    return s

def criticality_bonus(components: List[str]) -> float:
    """Extra risk if critical components touched."""
    touched = set(components)
    overlap = touched & CRITICAL_COMPONENTS
    if not overlap:
        return 0.0
    return 10.0 + 5.0 * (len(overlap) - 1)

def change_type_modifier(change_type: str) -> float:
    if change_type in HIGH_RISK_CHANGE_TYPES:
        return 20.0
    if change_type in MEDIUM_RISK_CHANGE_TYPES:
        return 10.0
    return 0.0

def clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))

def score_record(rec: Dict) -> Tuple[float, str]:
    la = int(rec.get("lines_added", 0) or 0)
    lr = int(rec.get("lines_removed", 0) or 0)
    files = rec.get("files_changed", []) or []
    comps = rec.get("components", []) or []
    ctype = (rec.get("change_type") or "code").strip().lower()

    score = 0.0
    score += magnitude_score(la, lr)
    score += spread_score(len(files), len(comps))
    score += criticality_bonus(comps)
    score += change_type_modifier(ctype)

    desc = (rec.get("description") or "").lower()
    risky_terms = ["rewrite", "refactor", "driver", "schema", "index", "perf", "optimize", "concurrency", "timeout"]
    if any(t in desc for t in risky_terms):
        score += 5.0

    score = clamp(score)

    if score >= 70:
        level = "High"
    elif score >= 40:
        level = "Medium"
    else:
        level = "Low"

    return score, level

def predict(records: List[Dict]) -> List[Dict]:
    out = []
    for rec in records:
        score, level = score_record(rec)
        out.append({
            "change_id": rec.get("change_id"),
            "risk_score": round(score, 1),
            "risk_level": level
        })
    return out

def main():
    ap = argparse.ArgumentParser(description="Rule-based Change Impact Predictor")
    ap.add_argument("--input", required=True, help="Path to input JSON (list of records)")
    ap.add_argument("--output", required=False, help="Path to output predictions JSON")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        records = json.load(f)

    preds = predict(records)

    total = len(preds)
    by_level = {"High": 0, "Medium": 0, "Low": 0}
    for p in preds:
        by_level[p["risk_level"]] += 1
    print(f"Processed {total} changes.")
    for level in ["High", "Medium", "Low"]:
        print(f"  {level:>6}: {by_level[level]:3d}")

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(preds, f, indent=2)
        print(f"\nPredictions written to: {args.output}")

if __name__ == "__main__":
    main()
