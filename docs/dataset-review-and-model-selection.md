# Dataset review and model selection

Reviewed 2026-11-15 before changing the active binary UNSW-NB15 model.

## Dataset fit

The current API and trained pipeline use the `unsw-nb15-flow-v1` contract: 39 numeric fields and the categorical `proto`, `service`, and `state` fields. The official UNSW description lists 2,540,044 raw records, 49 features, and the canonical 175,341-row training / 82,332-row test partitions. The source grants academic research use with citation; the raw files and model weights stay out of Git. See the [official UNSW-NB15 dataset page](https://research.unsw.edu.au/projects/unsw-nb15-dataset).

The local KaggleHub cache contained a second file named `UNSW-NB15_Dataset2.csv` (340,693 rows, 40 columns). It contains only 39 numeric features and five attack labels; it has no normal rows and omits `proto`, `service`, and `state`. Comparing its 39-feature signatures with both canonical splits found all 340,693 rows already represented there, including 198,253 repeated signatures inside the cached file. It adds no independent flows, so using it would repeat benchmark examples and risk leakage. It was not added to training.

The cached `network-anomaly-dataset` contains 1,001 rows of QoS measurements such as throughput, congestion, packet loss, latency, and jitter. Its anomaly targets represent network-quality behavior, not the malicious / normal intrusion labels used by this model. It was not relabeled or mixed into IDS training.

## Other sources reviewed

- [CIC-IDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) is a relevant labeled flow benchmark with CICFlowMeter fields and multiple attack scenarios. Its feature contract differs from UNSW-NB15, and the publisher's download flow asks for contact information. No contact details were submitted and the data was not used in this run.
- [CIC IoT-DIAD 2024](https://www.unb.ca/cic/iot-diad-2024.html) provides a separately labeled IoT flow schema. It is a useful future cross-environment benchmark, but requires a schema adapter and an independent evaluation path before its rows can be combined safely.
- [CIC-YNU-IoTMal 2026](https://www.unb.ca/cic/datasets/ynu-iot-2026.html) combines network captures with system traces and activity features for IoT malware behavior. Its target and input contract differ from this network-flow classifier, so it is not an additional sample pool for the current model.

The CIC catalog includes recent IoT datasets, but a newer publication date does not make their features or labels interchangeable with UNSW-NB15. The active classifier remains scoped to its named, reproducible benchmark until an independently evaluated schema-specific pipeline is added.

## Candidate model check

The revised Random Forest (260 trees, maximum depth 24, minimum leaf size 1) and Logistic Regression were fit on the same grouped 80% training subset. The validation threshold was selected under the maximum 5% false-positive-rate policy. The official test partition was not used for model or threshold selection. Extra Trees was also tried previously and did not beat the v3 Random Forest on validation.

| Candidate | Validation accuracy | Balanced accuracy | Precision | Malicious recall | False-positive rate |
|---|---:|---:|---:|---:|---:|
| Random Forest v3 (140 trees) | 95.15% | 95.11% | 97.74% | 95.21% | 5.00% |
| Random Forest v4 (260 trees) | 95.40% | 95.29% | 97.75% | 95.57% | 4.99% |
| Logistic Regression | 91.78% | 92.68% | 97.62% | 90.36% | 4.99% |
| Extra Trees (trial) | 93.68% | 94.05% | 97.69% | 93.09% | 4.99% |

After selection, v4 was refit on all 175,341 official training rows and evaluated once on the official 82,332-row test partition. Held-out accuracy is 90.69%, slightly below the v3 report's 90.82%; malicious recall is 96.87% versus 96.85%, and false-positive rate is 16.89% versus 16.58%. The v4 candidate therefore improves validation recall slightly but does not demonstrate improved held-out accuracy. These models remain benchmark-only and experimental.

The cached extra dataset was not added: the additional UNSW-named file duplicates signatures already present in the canonical splits, and the QoS anomaly dataset has a different target. CIC-IDS2017, IoT-DIAD 2024 and YNU-IoTMal 2026 have different schemas or targets. They should be evaluated through separate schema-specific pipelines and holdouts, rather than appended as if they shared the UNSW feature contract. A real increase in independent traffic diversity requires a compatible dataset and an evaluation split that does not overlap training.
