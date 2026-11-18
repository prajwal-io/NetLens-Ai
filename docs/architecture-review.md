# README architecture review

The implemented CSV analysis path follows README section 7. Replay, persistence, and reporting now follow the same path; their service boundaries are documented below. New dataset support and live packet capture remain outside this release.

| README stage or principle | Application implementation | Assessment |
|---|---|---|
| User / React dashboard | Sign in through Supabase, then upload, validate, and analyze in Traffic Analyzer | Implemented; hosted account not provisioned |
| Frontend / FastAPI boundary | Central API client sends Supabase bearer tokens; same-origin development proxy and typed API responses | Implemented |
| Authentication / API access | FastAPI verifies Supabase user tokens; analysis and user data endpoints require authentication | Implemented; remote Auth runtime not configured in this workspace |
| CSV validation | Encoding, dialect, unique headers, required schema, row shape, numeric/category checks, byte and row limits | Implemented |
| Preprocessing | Saved training-fitted numeric median and categorical mode imputation, one-hot encoding | Implemented; missing category markers corrected during review |
| Feature processing | One canonical ordered 42-feature contract; ID, target, and attack category excluded | Implemented for extracted flow CSVs; raw packet feature extraction is outside this path |
| ML classifier | Local evaluated Random Forest pipeline; Logistic Regression comparison during offline training | Implemented; selected production artifact is Random Forest |
| Normal / malicious classification | Saved validation-selected threshold applied to malicious-class scores | Implemented; scores are uncalibrated benchmark outputs |
| FastAPI response | Analysis ID, model version, threshold, counts, ordered predictions, five feature previews | Implemented |
| Dashboard / visualization | Shared analysis state drives Command Center, Network Pulse, Threat Investigation, Reports | Implemented for classification records; actual topology requires address data |
| Report export | Saved snapshot -> backend CSV and paginated PDF export | Implemented |
| IDS / simulated IPS | Actual model classifications -> analyst approves or dismisses malicious alerts -> reversible owner-scoped decision -> CSV/PDF | Implemented; no real packet or firewall changes |
| Training separate from inference | CLI-only training/evaluation; API only loads and runs the saved pipeline | Implemented |
| Evaluation before installation | Training stages a candidate; successful evaluation publishes the active pipeline | Corrected during review; failed evaluation preserves active artifact |
| Historical replay input | Bundled verified holdout excerpts -> shared inference service -> saved snapshot | Implemented; playback is sequential, not original packet timing |
| Persistence / analysis history | Owner-scoped SQLite locally or Supabase Postgres with RLS when hosted; paginated history, restore and cascade delete | Implemented; hosted database not provisioned |

## Straightforward user flow

1. Sign in, then open Traffic Analyzer and select a compatible UTF-8 network-flow CSV.
2. Validate the file; correct any schema or value errors.
3. Run the installed evaluated model. Missing/invalid models produce a visible error.
4. Review labels and scores in the analyzer or navigate to the connected main pages. The analysis ID and totals remain the same.
5. For a malicious classification, approve a simulated block or dismiss the alert. The action is saved with the analysis; no live traffic is blocked.
6. Export the actual classifications and saved analyst decisions from Reports. Model Lab is an optional explanation of the installed model, not a required processing step.

## ML pipeline review

Dataset loading verifies the pinned training/test split sizes, row counts, headers, and SHA-256 values. Deterministic type cleaning happens before splitting, but learned imputers, encoding, scaling where used, and model fitting remain inside the candidate pipelines fitted on the fit partition only. Duplicate feature signatures stay together in the seeded validation split. Thresholds and model selection use validation results within the 5% validation false-positive budget. The chosen pipeline is refitted on official training data; official test records are used for held-out reporting, not training or threshold selection. Both full and novel-signature results are disclosed.

Training now writes a separate candidate artifact. Evaluation checks dataset identity, model feature order/classes, threshold, and finite probability scores before publishing the evaluated active artifact. The API rejects unavailable or unevaluated artifacts. Training and inference normalize missing categories to `np.nan`, ensuring the same fitted categorical imputer is used in both paths.

The active v4 model was independently re-evaluated on the hash-verified official test split on November 18, 2026. Its held-out false-positive rate is 16.89% (6,248 false alerts among 37,000 normal flows), above the 5% validation threshold-selection budget. This is a material model limitation; the threshold was not changed using test results. The classifier is a benchmark review aid, not an unattended detector.

## Verification

The pre-authentication release suite passed 66 backend tests on November 18, 2026, including the real held-out upload/inference test, failed-evaluation preservation of the active artifact, successful evaluated publication, and equivalence between blank categorical inputs and training-fitted mode replacements. One non-blocking Starlette/httpx deprecation warning remains. The existing v4 model was re-evaluated without retraining or publishing a replacement. The focused auth/ownership tests pass with mocked Supabase responses; a live Supabase migration and RLS session test still require a NetLens project.

The completion pass also passed five runtime checks against the active evaluated model, frontend production build, and Chrome workflow/accessibility checks. See [release evidence and limits](release-completion.md).
