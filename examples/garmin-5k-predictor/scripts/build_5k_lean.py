"""Lean 5K predictor: only the lifestyle features a non-runner would have.

Reads daily.csv (produced by flatten.py) and writes predict_5k_lean.csv with
~12 features + the target.

Run:
    python3 build_5k_lean.py --daily ./daily.csv --out ./predict_5k_lean.csv
"""

import argparse
from pathlib import Path

import pandas as pd

WHITELIST = [
    # activity
    "totalSteps", "moderateIntensityMinutes", "vigorousIntensityMinutes",
    "floorsAscendedInMeters", "totalDistanceMeters",
    # heart
    "restingHeartRate", "minHeartRate", "maxHeartRate",
    # hrv
    "hrvWeeklyAverage",
    # sleep
    "deepSleepSeconds", "lightSleepSeconds", "remSleepSeconds", "awakeSleepSeconds",
    "avgSleepStress", "averageRespiration",
    # energy
    "bmrKilocalories", "wellnessTotalKilocalories",
    # target
    "raceTime5K_minutes",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--daily", default="daily.csv", help="Path to daily.csv from flatten.py")
    ap.add_argument("--out", default="predict_5k_lean.csv", help="Output CSV path")
    args = ap.parse_args()

    df = pd.read_csv(args.daily)
    if "raceTime5K" not in df.columns:
        raise SystemExit("raceTime5K column missing — your Garmin export does not include race predictions yet.")

    df = df[df["raceTime5K"].notna()].copy()
    df["raceTime5K_minutes"] = df["raceTime5K"] / 60.0

    available = [c for c in WHITELIST if c in df.columns]
    missing = [c for c in WHITELIST if c not in df.columns]
    if missing:
        print(f"note: {len(missing)} whitelist columns missing from your export — proceeding without them:")
        for m in missing: print(f"  - {m}")

    out = df[available].reset_index(drop=True)
    out.to_csv(args.out, index=False)
    print(f"\nwrote {args.out}")
    print(f"  rows: {len(out)}  cols: {len(out.columns)}")
    print(f"  target raceTime5K_minutes: {out.raceTime5K_minutes.min():.2f} - {out.raceTime5K_minutes.max():.2f} min")


if __name__ == "__main__":
    main()
