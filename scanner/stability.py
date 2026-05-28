from config import STABLE_THRESHOLD

def is_stable(cache, ip):
    return cache.get(ip, {}).get("success", 0) >= STABLE_THRESHOLD

def update_stability(cache, ip, success):
    item = cache.get(ip, {
        "success": 0,
        "fail": 0
    })

    if success:
        item["success"] += 1
    else:
        item["fail"] += 1

    cache[ip] = item

    return item["success"] >= STABLE_THRESHOLD
