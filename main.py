import asyncio
import logging
import os
import random
import sys

from netaddr import IPNetwork, AddrFormatError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scanner.fetcher import fetch_ranges
from scanner.probe import probe
from scanner.scorer import score
from scanner.cache import load_cache, save_cache
from scanner.stability import is_stable, update_stability
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

LOG_FILE = os.path.join(LOG_DIR, f"shard_{SHARD_ID}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def expand_ip_ranges(ranges, max_ips):
    """استخراج هوشمند آیپی‌ها با نمونه‌برداری تصادفی"""
    all_ips = []
    seen = set()
    
    # شافل کردن رنج‌ها برای تنوع بیشتر
    shuffled_ranges = list(ranges[:MAX_RANGES])
    random.shuffle(shuffled_ranges)
    
    for r in shuffled_ranges:
        if len(all_ips) >= max_ips:
            break
            
        try:
            net = IPNetwork(r)
            remaining = max_ips - len(all_ips)
            if remaining <= 0:
                break
            
            # نمونه‌برداری هوشمند بر اساس سایز رنج
            if net.size > 10000:
                sample_size = min(500, remaining)
                sample = random.sample(list(net), sample_size)
            elif net.size > 1000:
                sample_size = min(200, remaining)
                sample = random.sample(list(net), sample_size)
            else:
                sample = list(net)[:remaining]
            
            for ip in sample:
                ip_str = str(ip)
                if ip_str not in seen:
                    seen.add(ip_str)
                    all_ips.append(ip_str)
                    if len(all_ips) >= max_ips:
                        break
                        
        except (AddrFormatError, Exception) as e:
            logger.debug(f"Error processing range {r}: {e}")
            continue
    
    logger.info(f"Expanded {len(all_ips)} unique IPs from ranges")
    return all_ips[:max_ips]

async def scan_ip(ip, domains, cache):
    """اسکن یک آیپی با چند دامنه و پورت"""
    if is_stable(cache, ip):
        return None
    
    # اولویت با دامنه‌های موفق قبلی
    prioritized_domains = sorted(domains, key=lambda d: 0 if d in ['discord.com', 'github.com', 'google.com'] else 1)
    
    for domain in prioritized_domains:
        for port in PORTS:
            for _ in range(RETRIES):
                result = await probe(ip, domain, port)
                if result:
                    update_stability(cache, ip, True)
                    stable_hits = cache.get(ip, {}).get("success", 0)
                    
                    return {
                        "ip": ip,
                        "domain": domain,
                        "port": port,
                        "score": score(result["latency"], result["tls"], result["http"], stable_hits),
                        "latency": round(result["latency"], 2),
                        "tls": result["tls"],
                        "http": result["http"],
                        "stable": stable_hits >= 2
                    }
    
    update_stability(cache, ip, False)
    return None

async def worker(queue, domains, cache, results, sem):
    """کارگر همزمان"""
    while True:
        ip = await queue.get()
        try:
            async with sem:
                result = await scan_ip(ip, domains, cache)
                if result:
                    results.append(result)
                    if len(results) % 50 == 0:
                        logger.info(f"✅ Found {len(results)} valid IPs so far")
        except Exception as e:
            logger.exception(f"Worker error for IP {ip}: {e}")
        finally:
            queue.task_done()

async def main():
    # بارگذاری دامنه‌ها
    with open("domains.txt") as f:
        domains = [x.strip() for x in f if x.strip()]
    
    logger.info(f"Loaded {len(domains)} domains")
    logger.info("Fetching IP ranges...")
    
    ranges = await fetch_ranges()
    logger.info(f"Ranges loaded: {len(ranges)}")
    
    all_ips = expand_ip_ranges(ranges, MAX_IPS_PER_RUN)
    logger.info(f"Total IPs to scan: {len(all_ips)}")
    
    my_ips = split_into_shards(all_ips, SHARDS, SHARD_ID)
    logger.info(f"Shard {SHARD_ID} size: {len(my_ips)} IPs")
    
    cache = load_cache()
    logger.info(f"Cache loaded: {len(cache)} entries")
    
    queue = asyncio.Queue()
    for ip in my_ips:
        queue.put_nowait(ip)
    
    results = []
    sem = asyncio.Semaphore(MAX_CONCURRENT)
    
    workers = [asyncio.create_task(worker(queue, domains, cache, results, sem)) for _ in range(WORKERS)]
    
    total = len(my_ips)
    last_log = 0
    
    while not queue.empty():
        await asyncio.sleep(5)
        processed = total - queue.qsize()
        if processed - last_log >= 1000:
            logger.info(f"Progress: {processed}/{total} IPs processed, found {len(results)} valid")
            last_log = processed
    
    await queue.join()
    
    for w in workers:
        w.cancel()
    
    save_cache(cache)
    logger.info(f"Cache saved with {len(cache)} entries")
    
    # ذخیره نتایج
    import orjson
    out = os.path.join(RESULTS_DIR, f"shard_{SHARD_ID}.json")
    
    results_sorted = sorted(results, key=lambda x: (x["score"], -x["latency"]), reverse=True)
    
    with open(out, "wb") as f:
        f.write(orjson.dumps(results_sorted))
    
    logger.info(f"✅ Shard {SHARD_ID} completed: {len(results)} valid IPs found")
    
    # نمایش نمونه نتایج
    if results_sorted:
        top3 = results_sorted[:3]
        for r in top3:
            logger.info(f"  🚀 {r['ip']}:{r['port']} - {r['domain']} - {r['latency']}ms - Score: {r['score']}")

if __name__ == "__main__":
    asyncio.run(main())2
