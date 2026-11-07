# Network data

## Training source

The model is trained from the UNSW-NB15 benchmark. Its official project page describes labeled normal and attack flow records, the standard training/test partitions, and nine attack categories: [UNSW-NB15 dataset](https://research.unsw.edu.au/projects/unsw-nb15-dataset). Academic research use is permitted with attribution to the original papers; commercial use requires author agreement.

The downloader uses a fixed public mirror revision because the official download is hosted through a gated SharePoint link. The pinned mirror is [jamshaid120/UNSW_NB15-Complete-dataset](https://github.com/jamshaid120/UNSW_NB15-Complete-dataset/tree/161024104f19eea98b5c9aba0499a8fcb867ba1d). The mirror reverses the names of the two standard split files, so the downloader verifies canonical row counts before writing `raw/unsw-nb15/training.csv` (175,341 rows) and `testing.csv` (82,332 rows). SHA-256 hashes and mirror provenance are recorded in a local download manifest.

Run `python -m ml.download_dataset` from `backend/` to acquire the data. Raw benchmark files and model artifacts are local generated data; they are not committed to this repository. Cite the five publications listed on the [official UNSW page](https://research.unsw.edu.au/projects/unsw-nb15-dataset) when using the dataset.

## Sample input

`samples/valid-flows.csv` and `frontend/public/sample-flows.csv` contain six benchmark flow examples with model features only. The sample has no identifiers or target labels, is for exercising validation and inference, and is not a model result or live traffic.

## Dataset screening

- **UNSW-NB15:** selected. It includes normal and attack labels, structured flow features, and predefined train/test partitions.
- **CIC-IDS2017:** also relevant and includes benign plus attack flows, but the official download requires a request form and the published captures total about 51 GB. A smaller academic mirror exists, but its current Kaggle download requires account consent; it was not used for this run.
- **Kaggle Network Anomaly Dataset:** not selected for intrusion classification. Its labels describe network performance anomalies, not normal versus attack-labeled network flows.
- **UCI/Kaggle `UNSW-NB15_Dataset2.csv`:** rejected for binary classification. Inspection found 340,693 records but only five attack categories and no normal class.

The local dataset cache and downloads stay outside Git. Do not add personal packet captures or unrelated network records.
