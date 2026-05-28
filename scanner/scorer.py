def score(latency, tls_ok, http_ok, stable_hits=0):
    s = 100

    s -= min(45, int(latency / 8))

    if not tls_ok:
        s -= 25

    if not http_ok:
        s -= 35

    s += min(15, stable_hits * 3)

    return max(0, min(100, s))
