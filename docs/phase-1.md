# Running the Phase 1 foundation

Use two terminals from the repository root.

## Frontend
~~~powershell
cd frontend
npm.cmd install
npm.cmd run dev
~~~
Open http://127.0.0.1:5173. The API base defaults to http://127.0.0.1:8000/api/v1. Copy .env.example to .env to override it. Fonts are bundled locally.

## Backend
With Python 3.11 or 3.12 installed:
~~~powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~
The current workspace already has backend/.venv installed and can run the last command directly. API docs: http://127.0.0.1:8000/docs.

Optional configuration is in backend/.env.example. NETSIGHT_CORS_ORIGINS accepts a JSON array. SQLite is initialized at backend/data/netsight.db by default. CSV uploads are not saved.

## Verify
~~~powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.pytest-tmp
~~~
~~~powershell
cd frontend
npm.cmd run build
node smoke.mjs
~~~
The browser smoke test requires Chrome at the Windows executable path specified in smoke.mjs, and both servers running. It covers navigation, actual upload success/error, API outage/retry, phone navigation, overflow, and browser errors.

Upload data/samples/valid-flows.csv through Traffic Analyzer, or download the same sample from the interface. Expected: 3 validated flows and a five-row-limited preview; no predictions. Test offline recovery by stopping the backend and refreshing its status.

This phase includes six routes, the dashboard, schema validation, and infrastructure. Replay, inference, trained-model evaluation, analysis history, and report exports remain in later phases. All dashboard activity and flow labels are explicitly sample UI data.

## Editorial interface update
The landing story is now at /. Command Center is at /command-center. The six workspace destinations use a floating horizontal navigation bar. See editorial-redesign.md for interaction and verification details. Backend commands and CSV contracts are unchanged.
