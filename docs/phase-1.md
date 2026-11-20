# Local development

NetSight AI runs as two local development services: the Vite frontend and the FastAPI backend.

Authentication and user data ownership are described in [the Supabase auth and deployment guide](auth-and-deployment.md). Supabase Auth must be configured before the protected workspace can be used.

## Requirements

- Node.js and npm
- Python 3.12 (the supported and pinned backend runtime)
- Docker Desktop and Supabase CLI for the local authentication stack ([setup](auth-and-deployment.md))

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
python -m scripts.check_setup
```

The check exits successfully only when the health endpoint responds, an evaluated model version is loaded, and Supabase Auth URL/key values are configured. If the model is missing, run the dataset download, training, and evaluation commands in [the ML pipeline guide](../backend/ml/README.md), then restart the API.

## Frontend

In a second terminal from the repository root:

```powershell
cd frontend
npm ci
npm run dev
```

Open the local Vite URL shown in the terminal (normally `http://127.0.0.1:5173`). Vite forwards `/api` requests to the FastAPI service on port 8000. The frontend displays backend and model availability from the real health endpoint.

The model artifact and raw training dataset are local generated files and are not committed. Prepare them once on a new demo machine with the download, train, and evaluate commands in [the ML pipeline guide](../backend/ml/README.md). Prepare the local Supabase containers and demo account too; after these are installed and running, the [faculty demo workflow](faculty-demo.md) runs without a cloud Auth connection.

## Verify upload and inference

Open **Traffic Analyzer**, choose `data/samples/valid-flows.csv`, validate it, then run analysis. Validation checks the CSV structure; analysis sends up to 10,000 rows to the evaluated local model in a worker thread and returns its actual output. Larger files must be split before upload. If the model artifact is unavailable, analysis returns an error rather than fabricated predictions.

The classifier predicts the binary UNSW-NB15 benchmark label. A malicious result is a signal for review, not proof of an incident. Review [the model evaluation record](model-evaluation.md) for measured test results, overlap caveats, and limitations.

Training stages `backend/ml/artifacts/netsight-candidate.joblib` by default. The default evaluation command publishes it to `netsight-model.joblib` only after successful held-out evaluation. The active API model stays intact if evaluation fails. Restart FastAPI after publication. With a custom `--artifact`, evaluation updates that experiment artifact only unless `--publish-to` is supplied.


## Completed workflow and release checks

Uploads and historical replays save owner-scoped analysis snapshots and per-row validated features. Local demos use SQLite; hosted storage uses Supabase Postgres with RLS. Open **Saved analyses** to restore or delete your analyses. **Network Pulse** can analyze two bundled real benchmark excerpts and play their classifications sequentially. In **Threat Investigation**, analysts can approve a simulated block or dismiss an alert on malicious predictions; decisions persist with the analysis and appear in CSV/PDF reports. This does not alter live traffic or firewall settings. **Reports** exports the selected saved analysis. Optional IP/time columns are described in [the API contract](architecture.md).

With the API running, from `backend/`:

```powershell
$env:NETSIGHT_TEST_EMAIL='your-dedicated-local-test-account@example.test'
$env:NETSIGHT_TEST_PASSWORD='local-test-password'
python -m scripts.check_release
python -m pytest tests -q
```

The runtime check signs in to the configured Supabase Auth with that dedicated test account, uses bundled real benchmark rows, performs five checks, and deletes the analyses it creates. It does not download data or retrain the model. The account must exist in the configured Auth project.

For browser release checks, run Vite normally, then from `frontend/`:

```powershell
$env:NETSIGHT_TEST_URL='http://127.0.0.1:5173'
$env:NETSIGHT_TEST_EMAIL='your-dedicated-local-test-account@example.test'
$env:NETSIGHT_TEST_PASSWORD='local-test-password'
$env:NETSIGHT_TEST_SUPABASE_URL='http://127.0.0.1:54321'
npm run test:release
```

The account must exist in the local Supabase stack. `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` must be set for the Vite server. The runner uses Chrome on Windows if available; otherwise install Playwright Chromium with `npx playwright install chromium`. `CHROME_PATH` can select an installed Chrome binary. It checks real uploads, restoration, linked views, topology context fixtures, replay controls, exports, mobile layout, offline errors, keyboard navigation, and axe WCAG rules. See [the completion record](release-completion.md).
