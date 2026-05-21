---
name: garmin-5k
description: Walk the user end-to-end through building a personal 5K race-time predictor on JITM.ai from their own Garmin Connect export. Use when the user types /garmin-5k or asks to reproduce the jitm-examples Garmin 5K demo.
---

# Garmin 5K Predictor — reproduction skill

You are guiding the user through reproducing the
[jitm-examples/garmin-5k-predictor](https://github.com/Just-In-Time-Models-JITM-ai/jitm-examples/tree/main/examples/garmin-5k-predictor)
recipe on their own Garmin Connect data. The goal: a trained JITM.ai model
that predicts the user's 5K race time from their lifestyle metrics.

## Steps

### 1. Locate the Garmin export

Ask the user where their Garmin Connect export is unzipped. They should
have a folder that contains `DI_CONNECT/` somewhere underneath. If they
don't have an export yet, point them at
<https://www.garmin.com/account/datamanagement/exportdata/> and tell them
to come back after the email arrives (Garmin typically takes a few hours
to a day).

Verify the path is correct by checking `DI_CONNECT/DI-Connect-Aggregator/`
contains `UDSFile_*.json` files. If not, the path is pointing at the wrong
level — likely needs to go one folder deeper.

### 2. Flatten the export

Run the bundled `flatten.py`:

```bash
python3 flatten.py --export <user-path> --out <out-dir>
```

Confirm `daily.csv` was written and report the row count + date range to
the user. If row count is under 100, warn them — the model needs at least
a few months of data to be useful.

### 3. Build the lean training CSV

```bash
python3 build_5k_lean.py --daily <out-dir>/daily.csv --out <out-dir>/predict_5k_lean.csv
```

The script will warn about any missing whitelist columns. If `raceTime5K`
is missing entirely, stop and tell the user their Garmin doesn't have race
predictions enabled — they need a newer running-capable watch.

### 4. Upload and train on JITM.ai

Use the JITM MCP tools in this order:

1. `jitm_account_info` — confirm the user has capacity (Free tier: 1 model
   slot)
2. `jitm_request_upload(filename="predict_5k_lean.csv")` — get a presigned
   `upload_url`
3. PUT the CSV to `upload_url` via `curl -X PUT -T ... 'url'`
4. `jitm_confirm_upload(dataset_id=...)`
5. Poll `jitm_list_datasets` every few seconds until the dataset status is
   `analysed`. Confirm the target candidates include `raceTime5K_minutes`
   with `problem_type: regression`.
6. `jitm_create_model(dataset_id=..., target_column="raceTime5K_minutes", problem_type="regression")`
7. Poll `jitm_model_status` every 3–5 seconds until status is `trained`.
   For Builder+ tier, continue polling until `phase2_status` is `improved`
   or `completed`.
8. `jitm_model_detail` — show the user the final metrics and top features.

### 5. Frame the result

Report:
- **MAE in seconds** (multiply `mae` by 60). This is the headline number.
- **Top 5 features** with a one-line physiological gloss each
  (e.g. "restingHeartRate — your aerobic fitness floor").
- **R²** as a "how much of the variance the model explains" callout.

### 6. Offer the daily schedule

Ask if the user wants to **schedule a daily refresh** so they can watch
their predicted 5K time move over weeks and months. If yes, walk them
through the bundled `scripts/daily_refresh.py`:

1. Install deps: `pip install garminconnect requests`
2. Mint a model PAT in the JITM dashboard (or via the API)
3. Export env vars: `GARMIN_EMAIL`, `GARMIN_PASSWORD`, `JITM_MODEL_ID`, `JITM_MODEL_PAT`
4. Run once to confirm it works → it prints yesterday's predicted 5K time
   and appends to `predictions_log.csv`
5. Wrap it in `/schedule` (Claude Code), cron, or a systemd timer

Be honest: `garminconnect` is unofficial and may break with API changes.
For long-term production use point them at Garmin's Health API. If the
user enables Garmin MFA, garminconnect supports it via a `prompt_mfa`
callback — they may need to extend the script.

## Tone

The user is doing this for fun and to own their health data. Keep the
language plain — avoid `acwr`, `hrv`, `vo2max` jargon without translating.
When the model finishes, lead with the headline ("we predict your 5K time
within ~30 seconds") before any technical metrics.

## Things to avoid

- Don't promise the model will predict a real race time — the target is
  Garmin's *own* predicted 5K time. The wow factor is that we reproduce
  Garmin's fitness assessment from lifestyle data alone.
- Don't include `vo2MaxValue`, `maxMet`, or any race time other than
  `raceTime5K_minutes` in the training CSV — those leak the answer.
- Don't include `calendarDate` as a feature — same reason (date proxies
  fitness trajectory).
