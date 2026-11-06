# Local development

NetSight AI runs as two local development services: the Vite frontend and the FastAPI backend.

## Requirements

- Node.js and npm
- Python 3.11 or 3.12

## Backend

From the repository root, open a terminal and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The checked-in application can start without the raw Kaggle dataset. To rebuild the local model artifact, download and evaluate the selected dataset:

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

## Frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal (normally `http://127.0.0.1:5173`). Vite forwards `/api` requests to the FastAPI service on port 8000. The frontend displays backend and model availability from the real health endpoint.

## Verify upload and inference

Open **Traffic Analyzer**, choose `data/samples/valid-flows.csv`, validate it, then run analysis. Validation checks the CSV structure; analysis sends the rows to the evaluated local model and returns its actual output. If the model artifact is unavailable, analysis returns an error rather than fabricated predictions.

The selected Kaggle label describes network performance anomalies, not verified malicious traffic. Review [the model evaluation record](model-evaluation.md) before interpreting predictions.
