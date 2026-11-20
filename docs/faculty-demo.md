# Offline faculty demonstration

This runbook keeps the demo on one Windows laptop. Use the local Supabase Auth stack for sign-in and SQLite for user-owned history. Prepare the containers and evaluated Random Forest v4 model before the presentation; see [authentication setup](auth-and-deployment.md).

## Prepare once, while online

From the repository root, install the locked dependencies:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
cd ..\frontend
npm ci
```

The trained model and raw dataset are intentionally excluded from Git. If the demo laptop does not already have the evaluated model artifact, prepare it from the pinned dataset:

```powershell
cd ..\backend
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
python -m scripts.check_setup
```

Dataset preparation and dependency installation need an internet connection. Keep the generated model at `backend/ml/artifacts/netsight-model.joblib`, the environment folders, and the bundled replay files on the demo laptop. Do not clean these between setup and the presentation.

## Start offline

Start the local Supabase containers first. The stack, migrations, demo account, and environment files must already be prepared as described in [authentication setup](auth-and-deployment.md). Keep three PowerShell terminals open from the project root.

Terminal 1:

```powershell
supabase start
```

Terminal 2:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 3:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173` and sign in with the prepared local demo account. Confirm the backend and model status are connected. Optional preflight from a fourth terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m scripts.check_setup
python -m scripts.check_release
```

SQLite history is stored locally under `backend/data/netsight.db`; do not copy this database into the repository. Analyses created during the demo remain available after a refresh.

## Suggested five-minute flow

1. **Command Center:** show the API/model status and v4 evaluation evidence. Point out the false-positive rate before presenting predictions.
2. **Traffic Analyzer:** upload `backend/data/replays/attack-benchmark.csv`, validate it, then analyze it. This is a real, 100-row benchmark excerpt with model features, not a generated prediction fixture.
3. **Command Center:** review the saved total and normal/malicious counts for that same analysis.
4. **Network Pulse:** select the normal or attack historical replay and choose **Analyze historical replay**. The application runs the active model, saves the result, and provides sequential playback. Repeat with the other scenario if time allows.
5. **Threat Investigation:** inspect a malicious classification and, if useful, save a **simulated** block or dismissal decision. This records an analyst action only; it does not change a firewall or block network traffic.
6. **Reports:** export CSV and PDF for the selected saved analysis. The analysis ID, model version, threshold, labels, and totals should agree with the workspace result.
7. **Saved analyses:** reopen the same result after a page change or browser refresh to show persistence. Model Lab is optional supporting detail, not part of the inference path.

The bundled excerpts are from UNSW-NB15 (2015). Historical replay is not live monitoring, the model's binary label is a review signal rather than proof of an attack, and the current schema accepts UNSW-NB15-compatible flow features only. Network topology appears only when validated source and destination addresses are present.

## If something is unavailable

- If the API indicator is offline, check that Uvicorn is still running on port 8000.
- If the model is not loaded, run the preparation commands above and restart Uvicorn.
- If an upload is rejected, confirm it is a UTF-8 CSV matching the published 42-feature schema and is within the 5 MiB / 10,000-row limits.
- If a report or replay fails, keep the API terminal visible and retry once; do not describe a missing result as a successful detection.
