"""Shared feature contract for training, validation, and inference."""

DATASET_SLUG = "kaiser14/network-anomaly-dataset"
LABELED_FILENAME = "network_dataset_labeled.csv"
TARGET_COLUMN = "anomaly"
TIMESTAMP_COLUMN = "timestamp"

# These are measured network-quality values. Timestamp, target fields, and the
# dataset's auxiliary anomaly_* labels are intentionally excluded.
FEATURE_COLUMNS = (
    "throughput",
    "congestion",
    "packet_loss",
    "latency",
    "jitter",
    "Percentage video occupancy",
    "Bitrate video",
    "Number videos",
)

NORMAL_LABEL = "normal"
ANOMALOUS_LABEL = "anomalous"
