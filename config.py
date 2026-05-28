import os

MAX_CONCURRENT = 300
WORKERS = 300

CONNECT_TIMEOUT = 3
READ_TIMEOUT = 5
RETRIES = 2

STABLE_THRESHOLD = 3

PORTS = [443, 8443, 2053, 2083, 2087, 2096]

MAX_IPS_PER_RUN = 50000
MAX_RANGES = 500

SHARDS = 4

RANGE_URLS = [
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/all/all_plain.txt",
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/all/all_plain_ipv4.txt"
]

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "history.json")

LOG_DIR = "logs"
LOG_LEVEL = "INFO"

OUTPUT_DIR = "output"
RESULTS_DIR = "results"

USER_AGENT = "CleanIPScanner/2.0"

for d in [CACHE_DIR, LOG_DIR, OUTPUT_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)
