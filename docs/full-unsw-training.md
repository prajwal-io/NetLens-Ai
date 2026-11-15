# Expanded UNSW-NB15 training workflow

## What this adds

The optional training path reads the four original UNSW-NB15 corpus CSVs and adds a reproducible, seeded sample to the canonical 175,341-row training split. The pinned files contain three exact duplicate records at adjacent file boundaries; the loader detects and removes those export overlaps, leaving the official 2,540,044 unique source rows. It retains the canonical official test partition for the final report and removes supplemental rows with matching held-out 42-feature signatures before sampling.

The raw corpus has a different export shape from the prepared model split. The loader maps source names into the versioned 42-feature contract, derives the omitted `rate` feature as packet intervals per second (`max(spkts + dpkts - 1, 0) / dur`, or zero when duration is zero), and verifies each source file against pinned byte sizes and SHA-256 values. The rate derivation matches the prepared split on sampled rows checked during implementation; the project tests protect the mapping and zero-duration behavior.

The default supplemental cap is 500,000 rows. Sampling uses a seeded streamed priority sample, so the pipeline does not retain all 2.54 million normalized rows in memory. When the full corpus is enabled, validation comes only from a grouped holdout of the canonical official training split. Any supplemental row with a matching validation signature is excluded from fitting. This keeps the threshold-selection distribution tied to the prepared official source instead of letting the much larger raw-corpus sample dominate validation. Candidate thresholds are chosen under a maximum 5% validation false-positive-rate policy; the official test remains reporting-only.

## Download and train

From the repository's `backend/` directory, with the locked Python environment active:

```bash
python -m pip install -r requirements.lock.txt
python -m ml.download_dataset
python -m ml.full_unsw
python -m ml.train --include-full-unsw --full-unsw-max-rows 500000 --artifact ml/artifacts/netsight-full-candidate.joblib
python -m ml.evaluate --artifact ml/artifacts/netsight-full-candidate.joblib --publish-to ml/artifacts/netsight-full-evaluated.joblib
```

The default commands write model files under `backend/ml/artifacts/`, which are ignored by Git. Do not publish an evaluated candidate as the active API model solely because it used more rows. Compare validation and held-out false-positive rates, false-alert counts, recall, and the unseen-signature sensitivity result first.

These commands keep the expanded candidate separate from the active artifact. Evaluation metadata is saved into the candidate and a separate evaluated copy; the API's active artifact is unchanged.

```bash
python -m ml.train --include-full-unsw --artifact ml/artifacts/netsight-full-candidate.joblib
python -m ml.evaluate --artifact ml/artifacts/netsight-full-candidate.joblib --publish-to ml/artifacts/netsight-full-evaluated.joblib
```

## Other datasets considered

The official CIC-IDS2017 and CSE-CIC-IDS2018 releases expose labeled traffic with CICFlowMeter features. Those feature definitions do not match NetLens's UNSW-NB15 flow schema. ToN-IoT also contains multiple data modalities, including network traffic and host/IoT telemetry, so only a deliberately selected and mapped network-flow subset could be compared fairly. These should first become separate external-evaluation adapters; their rows should not be appended directly to UNSW training data.

The current expanded path therefore uses only same-source UNSW data. A future cross-dataset evaluation should keep each dataset's capture environment intact, document feature conversions, and report false-positive rate and false-alert count on an untouched external test set. A threshold should not be tuned on that report set.

## Provenance and use

- Official UNSW-NB15 project: <https://research.unsw.edu.au/projects/unsw-nb15-dataset>
- Immutable public mirror revision used by the downloader: <https://github.com/jamshaid120/UNSW_NB15-Complete-dataset/tree/161024104f19eea98b5c9aba0499a8fcb867ba1d>
- Official CIC-IDS2017: <https://www.unb.ca/cic/datasets/ids-2017.html>
- Official CSE-CIC-IDS2018: <https://www.unb.ca/cic/datasets/ids-2018.html>
- Official ToN-IoT: <https://research.unsw.edu.au/projects/toniot-datasets>

The source dataset is for academic research with citation to the original papers; commercial use requires permission from the dataset authors. The public mirror is pinned and checksum-verified to make local reproduction detectable, but it is not the original dataset host.
