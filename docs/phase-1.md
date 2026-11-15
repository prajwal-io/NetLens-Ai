# Local development

NetSight AI runs as two local development services: the Vite frontend and the FastAPI backend.

## Requirements

- Node.js and npm
- Python 3.12 (the supported and pinned backend runtime)

## Backend

From the repository root, open a terminal and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
```

The checked-in application can start without the raw UNSW-NB15 dataset. To build or rebuild the local model artifact, download the pinned dataset splits, train the candidates, and evaluate the selected pipeline:

```powershell
python -m ml.download_dataset
python -m ml.train
python -m ml.evaluate
```

Then start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API is available at `http://127.0.0.1:8000`; health is at `/api/v1/health`, and interactive API docs are at `/docs`.

With the API running, verify API and evaluated-model availability from `backend/`:

```powershell
python scripts/check_setup.py
```

The check exits successfully only when the health endpoint responds and reports a loaded model version. If the model is missing, run the dataset download, training, and evaluation commands in [the ML pipeline guide](../backend/ml/README.md), then restart the API.

## Frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal (normally `http://127.0.0.1:5173`). Vite forwards `/api` requests to the FastAPI service on port 8000. The frontend displays backend and model availability from the real health endpoint.

## Verify upload and inference

Open **Traffic Analyzer**, choose `data/samples/valid-flows.csv`, validate it, then run analysis. Validation checks the CSV structure; analysis sends up to 10,000 rows to the evaluated local model in a worker thread and returns its actual output. Larger files must be split before upload. If the model artifact is unavailable, analysis returns an error rather than fabricated predictions.

The classifier predicts the binary UNSW-NB15 benchmark label. A malicious result is a signal for review, not proof of an incident. Review [the model evaluation record](model-evaluation.md) for measured test results, overlap caveats, and limitations.

Training stages `backend/ml/artifacts/netsight-candidate.joblib` by default. The default evaluation command publishes it to `netsight-model.joblib` only after successful held-out evaluation. The active API model stays intact if evaluation fails. Restart FastAPI after publication. With a custom `--artifact`, evaluation updates that experiment artifact only unless `--publish-to` is supplied.


## Completed workflow and release checks

Uploads and historical replays now save analysis snapshots and per-row validated features in local SQLite. Open **Saved analyses** to restore or delete them. **Network Pulse** can analyze two bundled real benchmark excerpts and play their classifications sequentially. **Reports** exports CSV and PDF from the selected saved analysis. Optional IP/time columns are described in [the API contract](architecture.md).

With the API running, from `backend/`:

```powershell
python scripts/check_release.py
python -m pytest tests -q
```

The runtime check uses bundled real benchmark rows, performs five checks, and deletes its own analysis records. It does not download data or retrain the model.

For browser release checks, run Vite normally, then from `frontend/`:

```powershell
$env:NETSIGHT_TEST_URL='http://127.0.0.1:5173'
npm run test:release
```

The runner uses Chrome on Windows if available; otherwise install Playwright Chromium with `npx playwright install chromium`. `CHROME_PATH` can select an installed Chrome binary. It checks real uploads, restoration, linked views, topology context fixtures, replay controls, exports, mobile layout, offline errors, keyboard navigation, and axe WCAG rules. See [the completion record](release-completion.md).
