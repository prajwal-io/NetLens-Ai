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
