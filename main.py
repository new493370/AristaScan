import asyncio
import logging
import os
import random
import sys

from netaddr import IPNetwork, AddrFormatError

# uvloop حذف شد - در GitHub Actions مشکل داشت

sys.path.insert(
    0,
    os.path.dirname(os.path.abspath(__file__))
)

from scanner.fetcher import fetch_ranges
from scanner.probe import probe
from scanner.scorer import score
from scanner.cache import load_cache, save_cache
from scanner.stability import (
    is_stable,
    update_stability
)
from scanner.shard import split_into_shards

from config import (
    MAX_CONCURRENT,
    MAX_IPS_PER_RUN,
    MAX_RANGES,
    PORTS,
    RETRIES,
    SHARDS,
    LOG_DIR,
    RESULTS_DIR,
    WORKERS
)

SHARD_ID = int(os.getenv("SHARD", "0"))

random.seed(SHARD_ID)

LOG_FILE = os.path.join(
    LOG_DIR,
    f"shard_{SHARD_ID}.log"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def expand_ip_ranges(ranges, max_ips):
    """
    بهینه‌سازی شده: نمونه‌برداری هوشمندتر و جلوگیری از expand کردن رنج‌های خیلی بزرگ
    """
    all_ips = []
    seen = set()  # برای حذف duplicates سریعتر
    
    for r in ranges[:MAX_RANGES]:
        if len(all_ips) >= max_ips:
            break
            
        try:
            net = IPNetwork(r)
            
            # محاسبه حداکثر تعداد IP برای این رنج
            remaining = max_ips - len(all_ips)
            if remaining <= 0:
                break
            
            # برای رنج‌های خیلی بزرگ، نمونه‌برداری می‌کنیم
            if net.size > 5000:
                # حداکثر 200 IP از هر رنج بزرگ
                sample_size = min(200, remaining)
                stride = max(1, net.size // sample_size)
                
                for i in range(0, net.size, stride):
                    ip_str = str(net[i])
                    if ip_str not in seen:
                        seen.add(ip_str)
                        all_ips.append(ip_str)
                        if len(all_ips) >= max_ips:
                            break
                            
            elif net.size > 1000:
                # رنج متوسط: حداکثر 100 IP
                sample_size = min(100, remaining)
                stride = max(1, net.size // sample_size)
                
                for i in range(0, net.size, stride):
                    ip_str = str(net[i])
                    if ip_str not in seen:
                        seen.add(ip_str)
                        all_ips.append(ip_str)
                        if len(all_ips) >= max_ips:
                            break
            else:
                # رنج کوچک: همه IPها
                for ip in net:
                    ip_str = str(ip)
                    if ip_str not in seen:
                        seen.add(ip_str)
                        all_ips.append(ip_str)
                        if len(all_ips) >= max_ips:
                            break
                            
        except AddrFormatError:
            continue
        except Exception as e:
            logger.warning(f"Error processing range {r}: {e}")
            continue
    
    logger.info(f"Expanded {len(all_ips)} unique IPs from ranges")
    return all_ips[:max_ips]

async def scan_ip(ip, domains, cache):
    if is_stable(cache, ip):
        return None

    for domain in domains:
        for port in PORTS:
            for _ in range(RETRIES):
                result = await probe(
                    ip,
                    domain,
                    port
                )

                if result:
                    stable = update_stability(
                        cache,
                        ip,
                        True
                    )

                    stable_hits = cache.get(ip, {}).get("success", 0)

                    return {
                        "ip": ip,
                        "domain": domain,
                        "port": port,
                        "score": score(
                            result["latency"],
                            result["tls"],
                            result["http"],
                            stable_hits
                        ),
                        "latency": round(
                            result["latency"],
                            2
                        ),
                        "tls": result["tls"],
                        "http": result["http"],
                        "stable": stable
                    }

    update_stability(cache, ip, False)
    return None

async def worker(queue, domains, cache, results, sem):
    while True:
        ip = await queue.get()

        try:
            async with sem:
                result = await scan_ip(
                    ip,
                    domains,
                    cache
                )

                if result:
                    results.append(result)
                    
                    # لاگ پیشرفت هر 100 ایپی
                    if len(results) % 100 == 0:
                        logger.info(f"Found {len(results)} valid IPs so far")

        except Exception as e:
            logger.exception(
                f"worker error for IP {ip}: {e}"
            )

        finally:
            queue.task_done()

async def main():
    with open("domains.txt") as f:
        domains = [
            x.strip()
            for x in f
            if x.strip()
        ]

    logger.info(f"Loaded {len(domains)} domains")
    logger.info("Fetching IP ranges...")

    ranges = await fetch_ranges()

    logger.info(f"Ranges loaded: {len(ranges)}")

    all_ips = expand_ip_ranges(
        ranges,
        MAX_IPS_PER_RUN
    )

    logger.info(f"Total IPs to scan: {len(all_ips)}")

    my_ips = split_into_shards(
        all_ips,
        SHARDS,
        SHARD_ID
    )

    logger.info(f"Shard {SHARD_ID} size: {len(my_ips)} IPs")

    cache = load_cache()
    logger.info(f"Cache loaded: {len(cache)} entries")

    queue = asyncio.Queue()
    for ip in my_ips:
        queue.put_nowait(ip)

    results = []
    sem = asyncio.Semaphore(MAX_CONCURRENT)

    workers = [
        asyncio.create_task(
            worker(
                queue,
                domains,
                cache,
                results,
                sem
            )
        )
        for _ in range(WORKERS)
    ]

    # پیشرفت را نشان بده
    total = len(my_ips)
    last_log = 0
    
    while not queue.empty():
        await asyncio.sleep(10)
        processed = total - queue.qsize()
        if processed - last_log >= 500:
            logger.info(f"Progress: {processed}/{total} IPs processed, found {len(results)} valid")
            last_log = processed

    await queue.join()

    for w in workers:
        w.cancel()

    save_cache(cache)
    logger.info(f"Cache saved with {len(cache)} entries")

    import orjson

    out = os.path.join(
        RESULTS_DIR,
        f"shard_{SHARD_ID}.json"
    )

    # مرتب‌سازی بر اساس امتیاز (بالاترین اولویت)
    results_sorted = sorted(
        results,
        key=lambda x: (x["score"], -x["latency"]),
        reverse=True
    )

    with open(out, "wb") as f:
        f.write(orjson.dumps(results_sorted))

    logger.info(f"Shard {SHARD_ID} completed: {len(results)} valid IPs found")

if __name__ == "__main__":
    asyncio.run(main())
