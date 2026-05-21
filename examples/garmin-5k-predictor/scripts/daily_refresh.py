"""Pull yesterday's Garmin metrics and predict your 5K with a trained JITM model.

Uses the unofficial `garminconnect` library (https://github.com/cyberjunky/python-garminconnect)
to fetch the metrics, builds the feature row the lean model expects, and calls
the JITM.ai predict endpoint with your model PAT.

Run:
    pip install garminconnect requests
    export GARMIN_EMAIL=...
    export GARMIN_PASSWORD=...
    export JITM_MODEL_ID=<your-model-id>
    export JITM_MODEL_PAT=pat_...
    python3 daily_refresh.py

Schedule it daily (e.g. via cron, Claude Code /schedule, or a systemd timer)
and append the result to a local log to track your fitness trajectory.

NOTE: garminconnect is unofficial and may break with Garmin API changes.
Garmin's published Health API is the supported long-term path.
"""

import csv
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

try:
    from garminconnect import Garmin
except ImportError:
    sys.exit("Install garminconnect first: pip install garminconnect")


LOG = Path("predictions_log.csv")
TARGET_DATE = (date.today() - timedelta(days=1)).isoformat()


def fetch_metrics() -> dict:
    """Pull yesterday's metrics from Garmin Connect into the lean feature row."""
    email = os.environ.get("GARMIN_EMAIL")
    pw = os.environ.get("GARMIN_PASSWORD")
    if not email or not pw:
        sys.exit("Set GARMIN_EMAIL and GARMIN_PASSWORD env vars.")

    g = Garmin(email, pw)
    g.login()

    # The exact method names below are best-effort against the public
    # garminconnect API surface. Confirm with the package's README — Garmin
    # changes these endpoints occasionally and the unofficial wrapper follows.
    stats = g.get_stats(TARGET_DATE)
    sleep = g.get_sleep_data(TARGET_DATE)
    hrv = g.get_hrv_data(TARGET_DATE)  # may not be supported on all watches

    sleep_levels = (sleep or {}).get("dailySleepDTO", {}) or {}
    hrv_summary = (hrv or {}).get("hrvSummary", {}) or {}

    return {
        # activity
        "totalSteps": stats.get("totalSteps"),
        "moderateIntensityMinutes": stats.get("moderateIntensityMinutes"),
        "vigorousIntensityMinutes": stats.get("vigorousIntensityMinutes"),
        "floorsAscendedInMeters": stats.get("floorsAscendedInMeters"),
        "totalDistanceMeters": stats.get("totalDistanceMeters"),
        # heart
        "restingHeartRate": stats.get("restingHeartRate"),
        "minHeartRate": stats.get("minHeartRate"),
        "maxHeartRate": stats.get("maxHeartRate"),
        # hrv
        "hrvWeeklyAverage": hrv_summary.get("weeklyAvg"),
        # sleep
        "deepSleepSeconds": sleep_levels.get("deepSleepSeconds"),
        "lightSleepSeconds": sleep_levels.get("lightSleepSeconds"),
        "remSleepSeconds": sleep_levels.get("remSleepSeconds"),
        "awakeSleepSeconds": sleep_levels.get("awakeSleepSeconds"),
        "avgSleepStress": sleep_levels.get("avgSleepStress"),
        "averageRespiration": sleep_levels.get("averageRespiration"),
        # energy
        "bmrKilocalories": stats.get("bmrKilocalories"),
        "wellnessTotalKilocalories": stats.get("wellnessTotalKilocalories"),
    }


def predict(features: dict) -> float:
    model_id = os.environ["JITM_MODEL_ID"]
    pat = os.environ["JITM_MODEL_PAT"]
    r = requests.post(
        f"https://api.jitm.ai/api/predict/{model_id}",
        headers={"Authorization": f"Bearer {pat}"},
        json={"features": features},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["prediction"]


def log(prediction: float, features: dict):
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "predicted_5k_minutes", "predicted_5k_pace_per_km", "restingHeartRate", "hrvWeeklyAverage", "totalSteps"])
        pace = prediction / 5.0  # min per km
        w.writerow([TARGET_DATE, f"{prediction:.2f}", f"{pace:.2f}", features.get("restingHeartRate"), features.get("hrvWeeklyAverage"), features.get("totalSteps")])


def main():
    features = fetch_metrics()
    prediction = predict(features)
    mins = int(prediction)
    secs = int((prediction - mins) * 60)
    pace_total_sec = (prediction / 5.0) * 60
    pace_m, pace_s = int(pace_total_sec // 60), int(pace_total_sec % 60)
    print(f"\n{TARGET_DATE} → predicted 5K: {mins}:{secs:02d} ({pace_m}:{pace_s:02d}/km)")
    log(prediction, features)
    print(f"appended to {LOG}")


if __name__ == "__main__":
    main()
