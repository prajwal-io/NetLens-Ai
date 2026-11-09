"""Versioned feature contract for the UNSW-NB15 binary IDS pipeline."""

DATASET_SLUG = "unsw-nb15"
DATASET_NAME = "UNSW-NB15"
DATASET_SOURCE = "https://research.unsw.edu.au/projects/unsw-nb15-dataset"
MIRROR_SOURCE = "https://github.com/jamshaid120/UNSW_NB15-Complete-dataset"
MIRROR_COMMIT = "161024104f19eea98b5c9aba0499a8fcb867ba1d"
DATASET_LICENSE = "Academic research use; cite the original papers. Commercial use requires author agreement."

TRAINING_FILENAME = "training.csv"
TEST_FILENAME = "testing.csv"
TARGET_COLUMN = "label"
ID_COLUMN = "id"
LABEL_CONTEXT_COLUMN = "attack_cat"

# Keep the source order stable. Identifiers and the descriptive attack category
# are excluded: they are not available or appropriate model inputs.
NUMERIC_FEATURES = (
    "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl",
    "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit",
    "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", "smean",
    "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl",
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm",
    "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst",
    "is_sm_ips_ports",
)
CATEGORICAL_FEATURES = ("proto", "service", "state")

FEATURE_COLUMNS = (
    "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes",
    "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt",
    "dinpkt", "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt",
    "synack", "ackdat", "smean", "dmean", "trans_depth", "response_body_len",
    "ct_srv_src", "ct_state_ttl", "ct_dst_ltm", "ct_src_dport_ltm",
    "ct_dst_sport_ltm", "ct_dst_src_ltm", "is_ftp_login", "ct_ftp_cmd",
    "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports",
)

NORMAL_LABEL = "normal"
MALICIOUS_LABEL = "malicious"
SCHEMA_NAME = "unsw-nb15-flow-v1"

# Remote file names in the pinned GitHub mirror are reversed relative to the
# canonical UNSW split. The downloader validates row counts and writes local
# training.csv / testing.csv using the correct roles.
REMOTE_TRAINING_CONTENT = "UNSW_NB15_testing-set.csv"  # 175,341 rows
REMOTE_TESTING_CONTENT = "UNSW_NB15_training-set.csv"  # 82,332 rows
EXPECTED_TRAIN_ROWS = 175_341
EXPECTED_TEST_ROWS = 82_332
# SHA-256 and byte-size pins for the exact CSV objects at MIRROR_COMMIT.
# UNSW publishes canonical row counts; the mirror commit supplies immutable bytes.
EXPECTED_TRAIN_BYTES = 32_293_018
EXPECTED_TEST_BYTES = 15_380_800
EXPECTED_TRAIN_SHA256 = "bec7dd5ec88dc2a0ccc7a07879d338395ed7421750f675fd0339e07dfe0648fa"
EXPECTED_TEST_SHA256 = "734fe6642edf758f7c94d7d9149426b49d202fe8e7bf0bef47392489c3c0a559"
