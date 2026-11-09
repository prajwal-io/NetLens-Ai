# NetSight AI architecture

React and TypeScript call the FastAPI service through Vite's same-origin `/api` proxy during local development. FastAPI separates routing, response schemas, CSV validation, model loading/inference, configuration, and SQLite initialization. Model training and evaluation run as explicit commands outside the request path.

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
User CSV --> React API client --> FastAPI validation
                                      |
                                      v
                             Evaluated model inference
                                      |
                                      v
                         Normal / malicious + score
                                      |
                    +-----------------+----------------+
                    v                                  v
              Dashboard / UI                   Prediction CSV export
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

Missing or invalid model artifacts do not prevent the health or schema routes from starting. `/traffic/analyze` and `/model/info` return HTTP 503 until a trained, evaluated artifact is installed. Errors use `{ "error": { "code": ..., "message": ... } }`.

## CSV contract: `unsw-nb15-flow-v1`

The API requires the 42 model features defined in [`backend/ml/schema.py`](../backend/ml/schema.py): 39 numeric flow features and the categorical fields `proto`, `service`, and `state`. The backend publishes these lists through `/model/schema` and `/model/info` so the frontend does not maintain a second feature list.

Upload requirements: UTF-8 CSV (optional BOM), comma/semicolon/tab/pipe delimiter, unique headers, maximum 5 MiB and 10,000 rows. Numeric values must be finite or blank; categorical values may be blank or at most 128 characters. Blank values are normalized to the saved imputers' missing-value marker and imputed using training-fitted statistics. Extra columns are shown in the validation preview but excluded from inference. In particular, `id`, `attack_cat`, and `label` never enter the classifier. Parsing and prediction run in worker threads.

An analysis response includes a generated ID, uploaded filename, model version, threshold, total/class counts, one row ID/label/score per input row, and feature values for up to five preview rows. The prediction CSV includes labels and scores for all rows without copying raw input features. Uploaded analyses are not persisted.

## Training, inference, and evaluation

`backend/ml/download_dataset.py` downloads a pinned UNSW-NB15 mirror revision, normalizes its reversed source filenames using the official 175,341/82,332 row counts, and records SHA-256 hashes. The raw dataset remains under ignored `data/raw/unsw-nb15/`.

Training fits numeric imputation, categorical imputation, and one-hot encoding inside each candidate pipeline. A seeded, stratified validation split groups repeated feature signatures. The pipeline compares Random Forest and Logistic Regression and maximizes malicious recall within a validation false-positive-rate budget of 5%, then refits on the complete official training split. The validation budget is not a guarantee on shifted data; the measured official test false-positive rate is reported separately. `ml.evaluate` checks the data hashes and evaluates the held-out official test split. It additionally reports metrics on test rows whose feature signatures do not appear in training.

The default `python -m ml.train` writes `netsight-candidate.joblib`, leaving the active evaluated model intact. `python -m ml.evaluate` evaluates that candidate and publishes the evaluated, self-contained artifact to `netsight-model.joblib` only after successful evaluation. The API loads the active artifact at startup. A failed training/evaluation run does not replace the active model. Restart the API after publishing to use the new artifact. Explicit `--artifact` paths support controlled experiments without automatically replacing the active model; `--publish-to` explicitly selects an installation destination.

Actual scores, confusion matrices, overlap counts, and limitations are recorded in [model-evaluation.md](model-evaluation.md). `malicious_score` is an uncalibrated `predict_proba` value for benchmark class 1. It is not attack confidence or proof of an incident.

## Persistence and boundaries

SQLite initializes application version state. Uploaded rows and inference history are not stored. Browser receipts retain validation metadata only. A shared, in-memory analysis store supplies actual predictions to Command Center, Network Pulse, Threat Investigation, and Reports after upload; reload or selecting another file clears it. Reports export actual classification CSVs. Only five feature previews are returned for inspection; all prediction rows are available with pagination. Model Lab reads evaluation metadata independently and is optional in the upload workflow.

The evaluated model and its JSON metadata are generated locally by the ML scripts. Historical replay, saved analysis history, backend report export endpoints, and PDF reports are not implemented. Network Pulse shows actual classifications when an upload is active and an explicitly conceptual walkthrough otherwise. It cannot reconstruct device relationships or time series from a CSV without addresses or timestamps. Neither view is live packet capture.

See [the architecture review](architecture-review.md) for the README-to-code mapping and verified boundaries.
