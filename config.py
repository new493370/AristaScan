import os

# ===== تنظیمات همزمانی پیشرفته =====
MAX_CONCURRENT = 200    # افزایش برای سرعت بیشتر
WORKERS = 200           # هماهنگ با همزمانی

# ===== تایم‌اوت‌های تهاجمی =====
CONNECT_TIMEOUT = 2     # کاهش برای سرعت
READ_TIMEOUT = 3        # کاهش برای سرعت
RETRIES = 1             # کاهش تلاش مجدد

STABLE_THRESHOLD = 2    # کاهش برای کشف سریع‌تر

# ===== پورت‌های بهینه =====
PORTS = [443, 8443, 2053, 2087]  # حذف پورت‌های کند

# ===== افزایش حجم اسکن =====
MAX_IPS_PER_RUN = 50000  # افزایش به ۵۰,۰۰۰ آیپی
MAX_RANGES = 500         # افزایش رنج‌ها

# ===== شاردهای بیشتر برای موازی‌سازی =====
SHARDS = 8              # افزایش از ۴ به ۸

# ===== منبع رنج‌ها (بدون تغییر) =====
RANGE_URLS = [
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/all/all_plain.txt",
    "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/all/all_plain_ipv4.txt"
]

# ===== مسیرها =====
CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "history.json")
LOG_DIR = "logs"
LOG_LEVEL = "INFO"
OUTPUT_DIR = "output"
RESULTS_DIR = "results"
USER_AGENT = "CleanIPScanner/3.0"

# ایجاد دایرکتوری‌ها
for d in [CACHE_DIR, LOG_DIR, OUTPUT_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)
