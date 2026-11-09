# CSV upload and linked workflow review

The current inference contract is `unsw-nb15-flow-v1`: 42 specific features with their original UNSW-NB15 definitions and units. Supporting CSV syntax does not make arbitrary dataset schemas compatible with the trained model. Missing features are rejected; they are not silently fabricated or filled as entire missing columns.

## Supported inputs

- UTF-8 with or without BOM; comma, semicolon, tab, or pipe delimiters.
- Quoted fields, escaped quotes, multiline quoted metadata, CRLF or LF, reordered feature columns, and extra metadata columns.
- Blank individual feature values use the fitted training imputers. Invalid numeric values, infinity, duplicate or missing headers, ragged rows, malformed quoting, binary/non-UTF-8 files, oversized files, and more than 10,000 rows are rejected.
- Uploading another network CSV requires the same feature meanings, units, and feature extraction process. A new exporter/schema requires a documented adapter and independently evaluated model; renaming unrelated columns is unsafe.

## Real-data verification

`backend/tests/test_real_upload.py` uploads 1,000 deterministic held-out benchmark rows from the SHA-256-verified official UNSW-NB15 test partition using UTF-8 BOM encoding. It validates schema, runs the installed evaluated model, and checks every returned label/score and total against direct pipeline inference. It skips when local raw data or the evaluated artifact is unavailable. No dummy predictions are used in this test.

`frontend/linked-workflow-tests.mjs` uploads the same real file through the browser, runs validation and inference, and checks navigation, shared analysis identity/version/totals, filters, pagination, CSV export, mobile overflow, and runtime errors. Run with Vite on 5175, a fresh API on 8002, and the local `data/qa/real-heldout.csv` fixture prepared from the same seeded 1,000-row subset. Set `NETSIGHT_API_PROXY_TARGET=http://127.0.0.1:8002` before starting Vite, then run `node linked-workflow-tests.mjs` from `frontend/`. The fixture remains outside source control.

Local verification: **47 backend tests passed**, production frontend build passed, and the browser workflow passed at desktop and 390-pixel mobile width with no runtime errors or page overflow. The actual browser upload produced **375 normal / 625 malicious** classifications across 1,000 records using `netsight-rf-unsw-v3`, and all four connected pages retained that analysis identity and totals. These are model outputs, not assertions of ground-truth accuracy on the subset.

Prepare the browser fixture from the repository root after installing the pinned backend dependencies and downloading the verified official data:

```powershell
New-Item -ItemType Directory -Force data/qa
backend/.venv/Scripts/python.exe -c "import pandas as pd; pd.read_csv('data/raw/unsw-nb15/testing.csv').sample(n=1000,random_state=2026).to_csv('data/qa/real-heldout.csv',index=False,encoding='utf-8-sig')"
```

One successful upload now supplies Command Center, Network Pulse, Threat Investigation, and Reports through one memory store. The active results survive navigation and are cleared on reload or choosing another upload. Reports export actual predictions. Model Lab remains an optional metadata view and is not required to complete an analysis. Raw traffic is not persisted in browser storage. Only the five feature previews returned by the API are available for detailed feature inspection; all classification rows are available in bounded 50-row pages.

Network Pulse does not invent device addresses, timestamps, or links from the UNSW schema. Until actual source/destination data is provided and preserved, it shows real classification records with an explicit topology limitation.

## Recent data review

Priority candidate: [UNSW-IoTraffic, published August 29, 2025](https://datadryad.org/dataset/doi:10.5061/dryad.w0vt4b94b). The source provides captured IoT flow CSVs with addresses, timestamps, packet statistics, and 27 devices. The publication year must not be presented as a guarantee that packets were captured in 2025. Its schema differs from UNSW-NB15 and its documentation states there are no ground-truth interaction/event annotations. It is suitable for traffic exploration research, but not a drop-in labeled attack dataset for this classifier.

The official `flows.zip` download (file 4322594) returned HTTP 403 during this review. Actual upload/inference on that archive has therefore **not** been completed. The existing model remains UNSW-NB15-based (2015); no claim of training or evaluation on 2025/2026 captured traffic is made. A recent, accessible dataset with compatible extraction and reliable labels is still needed before changing the model's supported schema.
