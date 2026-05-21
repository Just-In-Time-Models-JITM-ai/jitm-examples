"""Flatten a Garmin Connect export into 3 CSVs keyed on calendarDate.

Run:
    python3 flatten.py --export /path/to/<your-garmin-export-id> --out ./out

Outputs (in --out directory):
  - daily.csv             : one row per day (UDS + sleep + readiness + load + race preds + VO2max)
  - activities.csv        : one row per workout
  - race_predictions.csv  : one row per day with predicted race times
"""

import argparse
import glob
import json
from pathlib import Path

import pandas as pd


def load_many(pattern: str, root: Path) -> list:
    rows = []
    for p in sorted(glob.glob(str(root / pattern))):
        with open(p) as f:
            d = json.load(f)
        if isinstance(d, list):
            rows.extend(d)
        elif isinstance(d, dict):
            rows.append(d)
    return rows


def _coerce_date(val):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (int, float)) and val > 10_000_000_000:
        return pd.to_datetime(int(val), unit="ms", errors="coerce").date().isoformat()
    parsed = pd.to_datetime(val, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def dedupe_by_date(df: pd.DataFrame, date_col: str = "calendarDate") -> pd.DataFrame:
    if df.empty or date_col not in df.columns:
        return df
    df = df.copy()
    df[date_col] = df[date_col].map(_coerce_date)
    df = df.dropna(subset=[date_col])
    df = df.drop_duplicates(subset=[date_col], keep="last")
    return df


def build_uds(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Aggregator/UDSFile_*.json", di)
    df = pd.DataFrame(rows)
    drop = [c for c in df.columns if c in {
        "uuid", "userProfilePK",
        "wellnessStartTimeGmt", "wellnessEndTimeGmt",
        "wellnessStartTimeLocal", "wellnessEndTimeLocal",
        "isVigorousDay",
    }]
    df = df.drop(columns=drop, errors="ignore")
    return dedupe_by_date(df)


def build_sleep(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Wellness/*sleepData.json", di)
    flat = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        out = {
            "calendarDate": r.get("calendarDate"),
            "deepSleepSeconds": r.get("deepSleepSeconds"),
            "lightSleepSeconds": r.get("lightSleepSeconds"),
            "remSleepSeconds": r.get("remSleepSeconds"),
            "awakeSleepSeconds": r.get("awakeSleepSeconds"),
            "unmeasurableSeconds": r.get("unmeasurableSeconds"),
            "averageRespiration": r.get("averageRespiration"),
            "lowestRespiration": r.get("lowestRespiration"),
            "highestRespiration": r.get("highestRespiration"),
            "awakeCount": r.get("awakeCount"),
            "avgSleepStress": r.get("avgSleepStress"),
            "restlessMomentCount": r.get("restlessMomentCount"),
        }
        scores = r.get("sleepScores") or {}
        if isinstance(scores, dict):
            for k, v in scores.items():
                if isinstance(v, dict):
                    if "value" in v:
                        out[f"sleepScore_{k}_value"] = v.get("value")
                    if "qualifierKey" in v:
                        out[f"sleepScore_{k}_qualifier"] = v.get("qualifierKey")
        flat.append(out)
    return dedupe_by_date(pd.DataFrame(flat))


def build_readiness(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Metrics/TrainingReadinessDTO_*.json", di)
    df = pd.DataFrame(rows)
    keep = [
        "calendarDate", "level", "score",
        "sleepScore", "sleepScoreFactorPercent",
        "recoveryTime", "recoveryTimeFactorPercent",
        "acwrFactorPercent", "stressHistoryFactorPercent",
        "hrvFactorPercent", "sleepHistoryFactorPercent",
        "validSleep", "hrvWeeklyAverage", "acuteLoad",
    ]
    df = df[[c for c in keep if c in df.columns]]
    df = df.rename(columns={
        "level": "readiness_level",
        "score": "readiness_score",
        "sleepScore": "readiness_sleepScore",
    })
    return dedupe_by_date(df)


def build_training_load(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Metrics/MetricsAcuteTrainingLoad_*.json", di)
    df = pd.DataFrame(rows)
    keep = [
        "calendarDate", "acwrPercent", "acwrStatus",
        "dailyTrainingLoadAcute", "dailyTrainingLoadChronic",
        "dailyAcuteChronicWorkloadRatio",
    ]
    df = df[[c for c in keep if c in df.columns]]
    return dedupe_by_date(df)


def build_race_predictions(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Metrics/RunRacePredictions_*.json", di)
    df = pd.DataFrame(rows)
    keep = ["calendarDate", "raceTime5K", "raceTime10K", "raceTimeHalf", "raceTimeMarathon"]
    df = df[[c for c in keep if c in df.columns]]
    return dedupe_by_date(df)


def build_vo2max(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Metrics/MetricsMaxMetData_*.json", di)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    if "updateTimestamp" in df.columns:
        df["calendarDate"] = pd.to_datetime(df["updateTimestamp"], errors="coerce").dt.date.astype(str)
    keep = ["calendarDate", "vo2MaxValue", "maxMet", "maxMetCategory"]
    df = df[[c for c in keep if c in df.columns]]
    return dedupe_by_date(df)


def build_heat_alt(di: Path) -> pd.DataFrame:
    rows = load_many("DI-Connect-Metrics/MetricsHeatAltitudeAcclimation_*.json", di)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    drop = [c for c in df.columns if c in {"userProfilePK", "deviceId", "timestamp"}]
    df = df.drop(columns=drop, errors="ignore")
    return dedupe_by_date(df)


def build_activities(di: Path) -> pd.DataFrame:
    candidates = list(glob.glob(str(di / "DI-Connect-Fitness" / "*_summarizedActivities.json")))
    if not candidates:
        return pd.DataFrame()
    with open(candidates[0]) as f:
        d = json.load(f)
    acts = d[0]["summarizedActivitiesExport"]
    df = pd.DataFrame(acts)
    if "startTimeLocal" in df.columns:
        df["calendarDate"] = pd.to_datetime(df["startTimeLocal"], errors="coerce").dt.date.astype(str)
    drop_prefix = ("uuid", "device", "split", "summarized")
    drop = [c for c in df.columns if c.startswith(drop_prefix)]
    df = df.drop(columns=drop, errors="ignore")
    if "calendarDate" in df.columns:
        cols = ["calendarDate"] + [c for c in df.columns if c != "calendarDate"]
        df = df[cols]
    return df


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--export", required=True, help="Path to your Garmin export folder (the one containing DI_CONNECT/)")
    ap.add_argument("--out", default=".", help="Output directory for CSVs (default: current dir)")
    args = ap.parse_args()

    export = Path(args.export).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    di = export / "DI_CONNECT"
    if not di.exists():
        raise SystemExit(f"DI_CONNECT not found under {export}. Point --export at the folder that contains DI_CONNECT/.")

    print(f"Loading from {di}")
    parts = {
        "uds": build_uds(di),
        "sleep": build_sleep(di),
        "readiness": build_readiness(di),
        "load": build_training_load(di),
        "race": build_race_predictions(di),
        "vo2": build_vo2max(di),
        "heat_alt": build_heat_alt(di),
    }
    for k, v in parts.items():
        print(f"  {k:10s} rows={len(v):>6} cols={len(v.columns):>3}")

    daily = parts["uds"]
    for k in ("sleep", "readiness", "load", "race", "vo2", "heat_alt"):
        right = parts[k]
        if right.empty or "calendarDate" not in right.columns:
            continue
        overlap = set(daily.columns) & set(right.columns) - {"calendarDate"}
        right = right.rename(columns={c: f"{c}_{k}" for c in overlap})
        daily = daily.merge(right, on="calendarDate", how="left")
    daily = daily.sort_values("calendarDate").reset_index(drop=True)
    daily.to_csv(out_dir / "daily.csv", index=False)
    print(f"\nwrote {out_dir / 'daily.csv'}  rows={len(daily)} cols={len(daily.columns)}")

    acts = build_activities(di)
    if not acts.empty:
        acts.to_csv(out_dir / "activities.csv", index=False)
        print(f"wrote {out_dir / 'activities.csv'}  rows={len(acts)} cols={len(acts.columns)}")

    race = parts["race"].sort_values("calendarDate")
    if not race.empty:
        race.to_csv(out_dir / "race_predictions.csv", index=False)
        print(f"wrote {out_dir / 'race_predictions.csv'}  rows={len(race)} cols={len(race.columns)}")

    if not daily.empty:
        print(f"\nDate range in daily.csv: {daily.calendarDate.min()} -> {daily.calendarDate.max()}")


if __name__ == "__main__":
    main()
