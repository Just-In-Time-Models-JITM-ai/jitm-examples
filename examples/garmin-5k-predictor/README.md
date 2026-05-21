# Garmin 5K Predictor

**Predict your 5K race time from sleep, steps, and resting heart rate alone.**
No running data, no fitness test, no jargon.

## What this is

You hand a year of your Garmin data to [JITM.ai](https://jitm.ai). It learns
the relationship between your everyday lifestyle metrics (steps, sleep stages,
resting heart rate, HRV, basal metabolic rate) and the 5K race time Garmin
itself predicts for you. The trained model can then estimate your 5K time
from any new day's lifestyle data — no run required.

Then you schedule it. Each morning, an agent (Claude Code, a cron job, your
own scheduler) pulls the latest day from your Garmin export and asks the
model: *what's my race-time-shaped fitness right now?* You watch the line
move. You own the data and the model.

## Results

Trained on **1,228 days** of one author's Garmin export (2022–2026):

| Metric | Value |
|---|---|
| Validation | 15-fold CV, full dataset |
| Ensemble size | 135 models |
| **R²** | 0.605 |
| **MAE** | 0.57 min (~34 seconds) |
| **RMSE** | 0.78 min (~47 seconds) |

The model predicts a 5K race time within roughly **30 seconds** using only
12 lifestyle inputs.

### Top features (Phase 2 importance)

1. `bmrKilocalories` — basal metabolic rate (scales with body composition)
2. `restingHeartRate` — the classic aerobic-fitness signal
3. `wellnessTotalKilocalories` — total daily energy burn
4. `hrvWeeklyAverage` — heart rate variability, recovery capacity
5. `avgSleepStress` — autonomic stress during sleep
6. `totalSteps`
7. `floorsAscendedInMeters`
8. `maxHeartRate` (daily)
9. `totalDistanceMeters`
10. `vigorousIntensityMinutes`

Reads like a sports-science textbook, not a feature-engineering trick.

## Reproduce it with your own data

### 1. Export your Garmin data

Go to [Garmin's account management](https://www.garmin.com/account/datamanagement/exportdata/)
and request a full export. It arrives as a zip with a folder named like
`5774c07f-75fa-4f7a-b169-7106c71136d0_1/`. Unzip somewhere.

### 2. Flatten the export to CSVs

```bash
cd scripts
pip install pandas
python3 flatten.py --export /path/to/your-garmin-export --out ./out
```

You get three CSVs:
- `daily.csv` — one row per day, all the metrics joined
- `activities.csv` — one row per workout
- `race_predictions.csv` — daily Garmin race-time predictions

### 3. Build the lean training CSV

```bash
python3 build_5k_lean.py --daily ./out/daily.csv --out ./out/predict_5k_lean.csv
```

12 lifestyle features + the target. Schema preview in [`sample/schema.csv`](sample/schema.csv).

### 4. Train on JITM.ai

The fastest path is the **MCP tools**. From inside Claude Code (or any
MCP-capable client) with the JITM MCP server connected:

1. `jitm_request_upload(filename="predict_5k_lean.csv")` → get an upload URL
2. PUT the CSV to that URL
3. `jitm_confirm_upload(dataset_id=...)`
4. Wait until `jitm_list_datasets` shows status `analysed`
5. `jitm_create_model(dataset_id=..., target_column="raceTime5K_minutes", problem_type="regression")`
6. Poll `jitm_model_status` until trained

Or open [jitm.ai](https://jitm.ai), upload via the web UI, pick the target,
click train.

### 5. (Optional) Schedule it daily — take your health data into your own hands

This is the fun part. The bundled [`scripts/daily_refresh.py`](scripts/daily_refresh.py)
uses the community [`garminconnect`](https://github.com/cyberjunky/python-garminconnect)
library to pull yesterday's metrics, build the lean feature row, call your
trained model, and append the result to `predictions_log.csv`.

```bash
pip install garminconnect requests
export GARMIN_EMAIL=...
export GARMIN_PASSWORD=...
export JITM_MODEL_ID=<your-model-id>
export JITM_MODEL_PAT=pat_...   # mint one in the JITM dashboard

python3 scripts/daily_refresh.py
# → 2026-05-20 → predicted 5K: 22:48 (4:34/km)
```

Wrap that in `/schedule` from Claude Code, or a cron job, or a systemd timer.
Every morning you get a fresh prediction and a growing log. Deltas over time
become the actual signal — *am I trending faster or slower than last
quarter?* You own the model, the data, and the schedule.

Note: `garminconnect` is **unofficial** and may break with Garmin API
changes. For production use, Garmin's published Health API is the long-term
supported path; this script demonstrates the pattern.

## Caveats and honest notes

- The training target (`raceTime5K`) was originally shaped by your
  historical running activities. That's what calibrated the model.
  From this point onwards, every prediction rests purely on your
  underlying health metrics: sleep, resting heart rate, HRV, daily
  activity. Once trained, you don't need to run to get a forecast.
  The lifestyle physiology does the work.
- A heavier 89-feature version of this model hits MAE ~22 seconds, but a
  chunk of its accuracy comes from "which Garmin metrics existed yet"
  acting as a time-of-day proxy. The lean 12-feature version is the honest
  one and the only one to deploy.
- HRV and sleep-stage columns require Garmin's newer wearables. If your
  watch is older you'll be missing some features — the script will tell you.

## What's in this folder

```
garmin-5k-predictor/
├── README.md              ← you are here
├── skill.md               ← Claude Code skill that runs the whole recipe
├── scripts/
│   ├── flatten.py         ← Garmin export → daily.csv
│   ├── build_5k_lean.py   ← daily.csv → predict_5k_lean.csv
│   └── daily_refresh.py   ← pulls yesterday's metrics, predicts, logs
└── sample/
    └── schema.csv         ← 3 synthetic rows showing the training schema
```
