# NetSight AI architecture

React and TypeScript call FastAPI through Vite's same-origin `/api` proxy during local development. Supabase Auth signs users in; FastAPI verifies each access token before allowing analysis, replay, history, investigation, or report requests. FastAPI separates routing, response schemas, CSV validation, model loading/inference, configuration, saved history, historical replay, and report generation. Model training and evaluation run as explicit commands outside the request path.

```text
UNSW-NB15 train/test CSVs
        |
        v
Pinned dataset downloader + row/hash checks
        |
        v
Grouped validation / model selection
        |
        v
Candidate preprocessing + classifier artifact
        |
        v
Held-out evaluation succeeds
        |
        v
Publish evaluated active artifact
        |
        +-----------------------------+
                                      |
User signs in --> Supabase Auth --> React session
User CSV or bundled replay --> React API client + bearer token --> FastAPI auth and validation
                                      |
                                      v
                             Evaluated model inference
                                      |
                                      v
                    Normal / malicious + score --> owner-scoped analysis store
                                      |
                    +-----------------+----------------+
                    v                                  v
              Dashboard / UI                   Saved CSV / PDF exports
                                      |
                         +------------+-------------+
                         v                          v
                Local SQLite (demo)       Supabase Postgres + RLS (hosted)
```

## API endpoints

Base URL: `http://127.0.0.1:8000/api/v1`

| Method | Endpoint | Behavior |
|---|---|---|
| GET | `/health` | Backend status and whether the evaluated model loaded |
| GET | `/model/schema` | Static CSV feature contract, available even without a model |
| GET | `/model/info` | Dataset, features, preprocessing, splits, and real evaluation metrics |
| POST | `/traffic/validate` | Validate required CSV columns, rows, values, and return a text preview; no predictions |
| POST | `/traffic/analyze` | Run the saved evaluated model; return `normal`/`malicious` labels and `malicious_score` values |
| GET | `/analyses/{id}/response-decisions` | Read saved, per-flow analyst decisions |
| PUT | `/analyses/{id}/flows/{row_id}/response` | Approve a simulated block or dismiss an alert for a malicious classification |
| DELETE | `/analyses/{id}/flows/{row_id}/response` | Undo the saved simulated decision |

Missing or invalid model artifacts do not prevent the health or schema routes from starting. `/traffic/analyze` and `/model/info` return HTTP 503 until a trained, evaluated artifact is installed. Errors use `{ "error": { "code": ..., "message": ... } }`.

## CSV contract: `unsw-nb15-flow-v1`

The API requires the 42 model features defined in [`backend/ml/schema.py`](../backend/ml/schema.py): 39 numeric flow features and the categorical fields `proto`, `service`, and `state`. The backend publishes these lists through `/model/schema` and `/model/info` so the frontend does not maintain a second feature list.

This pipeline supports UNSW-NB15-compatible flow records with the same feature meanings and units. Arbitrary CSVs and newer datasets are not interchangeable with this trained model; they need a documented schema adapter and a separately trained/evaluated pipeline before inference.

Upload requirements: UTF-8 CSV (optional BOM), comma/semicolon/tab/pipe delimiter, unique headers, maximum 5 MiB and 10,000 rows. Numeric values must be finite or blank; categorical values may be blank or at most 128 characters. Blank values are normalized to the saved imputers' missing-value marker and imputed using training-fitted statistics. Extra columns are shown in the validation preview but excluded from inference. In particular, `id`, `attack_cat`, and `label` never enter the classifier. Parsing and prediction run in worker threads.

An analysis response includes a generated ID, uploaded filename, model version, threshold, total/class counts, one row ID/label/score per input row, and feature values for up to five preview rows. The prediction CSV includes labels and scores for all rows without copying raw input features. Analyses and all validated feature rows are persisted transactionally in SQLite, including the model evaluation context at prediction time. Raw uploaded bytes and ignored extra columns are not retained.

## Training, inference, and evaluation

`backend/ml/download_dataset.py` downloads a pinned UNSW-NB15 mirror revision, normalizes its reversed source filenames using the official 175,341/82,332 row counts, and records SHA-256 hashes. The raw dataset remains under ignored `data/raw/unsw-nb15/`.

Training fits numeric imputation, categorical imputation, and one-hot encoding inside each candidate pipeline. A seeded, stratified validation split groups repeated feature signatures. The pipeline compares Random Forest and Logistic Regression and maximizes malicious recall within a validation false-positive-rate budget of 5%, then refits on the complete official training split. The validation budget is not a guarantee on shifted data; the measured official test false-positive rate is reported separately. `ml.evaluate` checks the data hashes and evaluates the held-out official test split. It additionally reports metrics on test rows whose feature signatures do not appear in training.

The default `python -m ml.train` writes `netsight-candidate.joblib`, leaving the active evaluated model intact. `python -m ml.evaluate` evaluates that candidate and publishes the evaluated, self-contained artifact to `netsight-model.joblib` only after successful evaluation. The API loads the active artifact at startup. A failed training/evaluation run does not replace the active model. Restart the API after publishing to use the new artifact. Explicit `--artifact` paths support controlled experiments without automatically replacing the active model; `--publish-to` explicitly selects an installation destination.

Actual scores, confusion matrices, overlap counts, and limitations are recorded in [model-evaluation.md](model-evaluation.md). `malicious_score` is an uncalibrated `predict_proba` value for benchmark class 1. It is not attack confidence or proof of an incident.

## Authentication, persistence, and boundaries

Health and model metadata are public. Analysis, replay, history, flow investigation, analyst decisions, and exports require a valid Supabase access token. FastAPI verifies the token with Supabase Auth and derives identity only from the verified user ID. Local demos use SQLite and owner-filter every query; existing ownerless rows stay hidden. Hosted storage uses Supabase Postgres through PostgREST with the caller's token and publishable key, so RLS enforces `auth.uid() = user_id`. The `save_analysis` security-invoker RPC saves each snapshot and its features in one transaction. The migration is in [`supabase/migrations`](../supabase/migrations/).

Both stores keep immutable analysis snapshots and per-flow features, plus reversible simulated IPS decisions keyed by analysis and row. Deleting an analysis cascades to its flow records and decisions. The browser keeps the selected analysis ID only; refresh restores it from the backend and reloads the decisions. A shared store drives Command Center, Network Pulse, Threat Investigation, and Reports. History summaries are paginated; prediction tables render 50 rows at a time and fetch individual flow features on demand. Model Lab remains an optional metadata view.

Historical replay scenarios are small hash-verified excerpts of the existing official UNSW-NB15 holdout. Uploads and replays call the same validation, ordered features, fitted preprocessing, model, and persistence service. Playback is a sequential demonstration rate, not reconstructed capture timing. Ground-truth labels in the source never enter inference. Replay requests run in FastAPI worker threads.

Optional context is separate from model input: `source_ip` / `src_ip` / `srcip`, `destination_ip` / `dst_ip` / `dstip`, and `timestamp` / `start_time`. Addresses must be valid IPv4 or IPv6. Times must be timezone-aware ISO 8601. Invalid recognized context is rejected, not silently drawn. Only provided source/destination pairs form topology connections. No live capture is implemented.

CSV and PDF endpoints read the saved snapshot and its response decisions, so later model changes cannot change past reports. CSV contains all predictions, available network context, and any saved simulated action; PDF includes the action summary and every classification. Reports explicitly state that no live traffic was blocked. PDF generation runs in a worker thread through a synchronous FastAPI route. Reports are generated on demand, not stored as duplicate files.

## Saved workflow endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/analyses?limit=20&offset=0` | Paginated summaries (maximum 100 per page) |
| GET | `/analyses/{id}` | Restore a saved analysis |
| GET | `/analyses/{id}/flows/{row_id}` | Classification, context and original validated model features |
| GET | `/analyses/{id}/response-decisions` | Saved analyst response decisions for the analysis |
| PUT | `/analyses/{id}/flows/{row_id}/response` | Save a simulated block approval or alert dismissal |
| DELETE | `/analyses/{id}/flows/{row_id}/response` | Undo a saved simulated decision |
| DELETE | `/analyses/{id}` | Delete a snapshot and its feature records |
| GET | `/analyses/{id}/export.csv` | Export saved classifications and context |
| GET | `/analyses/{id}/report.pdf` | Export a paginated PDF |
| GET | `/replays` | Bundled scenario provenance and descriptions |
| POST | `/replays/{id}/analyze` | Run the active evaluated model, then save results |

See [release completion](release-completion.md) for checks, local operation and remaining model limitations.
