# README architecture review

The implemented CSV analysis path follows README section 7. The full target architecture also includes planned replay, persistence, and reporting capabilities, so it is not accurate to describe the entire target as complete.

| README stage or principle | Application implementation | Assessment |
|---|---|---|
| User / React dashboard | Upload, validate, then analyze in Traffic Analyzer | Implemented |
| Frontend / FastAPI boundary | Central API client, same-origin development proxy, typed API responses | Implemented |
| CSV validation | Encoding, dialect, unique headers, required schema, row shape, numeric/category checks, byte and row limits | Implemented |
| Preprocessing | Saved training-fitted numeric median and categorical mode imputation, one-hot encoding | Implemented; missing category markers corrected during review |
| Feature processing | One canonical ordered 42-feature contract; ID, target, and attack category excluded | Implemented for extracted flow CSVs; raw packet feature extraction is outside this path |
| ML classifier | Local evaluated Random Forest pipeline; Logistic Regression comparison during offline training | Implemented; selected production artifact is Random Forest |
| Normal / malicious classification | Saved validation-selected threshold applied to malicious-class scores | Implemented; scores are uncalibrated benchmark outputs |
| FastAPI response | Analysis ID, model version, threshold, counts, ordered predictions, five feature previews | Implemented |
| Dashboard / visualization | Shared analysis state drives Command Center, Network Pulse, Threat Investigation, Reports | Implemented for classification records; actual topology requires address data |
| Report export | Browser CSV export from actual predictions | Implemented; backend report endpoints and PDF export remain planned |
| Training separate from inference | CLI-only training/evaluation; API only loads and runs the saved pipeline | Implemented |
| Evaluation before installation | Training stages a candidate; successful evaluation publishes the active pipeline | Corrected during review; failed evaluation preserves active artifact |
| Historical replay input | Only a clearly labeled conceptual walkthrough exists | Planned API/scenario integration remains incomplete |
| Persistence / analysis history | SQLite version-state setup and browser validation receipts | Persistent analysis records remain incomplete |

## Straightforward user flow

1. Open Traffic Analyzer and select a compatible UTF-8 network-flow CSV.
2. Validate the file; correct any schema or value errors.
3. Run the installed evaluated model. Missing/invalid models produce a visible error.
4. Review labels and scores in the analyzer or navigate to the connected main pages. The analysis ID and totals remain the same.
5. Export the actual classifications from Reports or Traffic Analyzer. Model Lab is an optional explanation of the installed model, not a required processing step.

## ML pipeline review

Dataset loading verifies the pinned training/test split sizes, row counts, headers, and SHA-256 values. Deterministic type cleaning happens before splitting, but learned imputers, encoding, scaling where used, and model fitting remain inside the candidate pipelines fitted on the fit partition only. Duplicate feature signatures stay together in the seeded validation split. Thresholds and model selection use validation results within the 5% validation false-positive budget. The chosen pipeline is refitted on official training data; official test records are used for held-out reporting, not training or threshold selection. Both full and novel-signature results are disclosed.

Training now writes a separate candidate artifact. Evaluation checks dataset identity, model feature order/classes, threshold, and finite probability scores before publishing the evaluated active artifact. The API rejects unavailable or unevaluated artifacts. Training and inference normalize missing categories to `np.nan`, ensuring the same fitted categorical imputer is used in both paths.

The held-out false-positive rate remains 16.58%, above the validation budget, and a newer dataset is not yet integrated. These are model/data limitations, not architectural conformance guarantees. Tests cover the application boundaries and workflow; they cannot prove generalization to arbitrary networks.

## Verification

All 48 backend tests passed after the review fixes, including the real held-out upload/inference test, failed-evaluation preservation of the active artifact, successful evaluated publication, and equivalence between blank categorical inputs and training-fitted mode replacements. One non-blocking Starlette/httpx deprecation warning remains. No new model weights were trained during this review; the existing evaluated active model is preserved.
