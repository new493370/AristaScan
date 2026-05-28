import asyncio
import logging
import os
import random
import sys

from netaddr import IPNetwork, AddrFormatError

import uvloop

asyncio.set_event_loop_policy(
    uvloop.EventLoopPolicy()
)

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
    all_ips = []

    for r in ranges[:MAX_RANGES]:

        try:
            net = IPNetwork(r)

            if net.size > 1000:
                stride = max(1, net.size // 100)

                for i in range(0, net.size, stride):
                    all_ips.append(str(net[i]))

            else:
                for ip in net:
                    all_ips.append(str(ip))

            if len(all_ips) >= max_ips:
                break

        except AddrFormatError:
            continue

    return list(dict.fromkeys(all_ips))[:max_ips]

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

        except Exception as e:
            logger.exception(
                f"worker error: {e}"
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

    logger.info("fetching ranges...")

    ranges = await fetch_ranges()

    logger.info(
        f"ranges loaded: {len(ranges)}"
    )

    all_ips = expand_ip_ranges(
        ranges,
        MAX_IPS_PER_RUN
    )

    logger.info(
        f"expanded ips: {len(all_ips)}"
    )

    my_ips = split_into_shards(
        all_ips,
        SHARDS,
        SHARD_ID
    )

    logger.info(
        f"shard size: {len(my_ips)}"
    )

    cache = load_cache()

    queue = asyncio.Queue()

    for ip in my_ips:
        queue.put_nowait(ip)

    results = []

    sem = asyncio.Semaphore(
        MAX_CONCURRENT
    )

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

    await queue.join()

    for w in workers:
        w.cancel()

    save_cache(cache)

    import orjson

    out = os.path.join(
        RESULTS_DIR,
        f"shard_{SHARD_ID}.json"
    )

    with open(out, "wb") as f:
        f.write(orjson.dumps(
            sorted(
                results,
                key=lambda x: x["score"],
                reverse=True
            )
        ))

    logger.info(
        f"valid results: {len(results)}"
    )

if __name__ == "__main__":
    asyncio.run(main())
