import aiohttp
import asyncio

from config import RANGE_URLS, USER_AGENT

HEADERS = {
    "User-Agent": USER_AGENT
}

async def fetch_single(session, url):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status == 200:
                return (await resp.text()).splitlines()

    except Exception:
        return []

    return []

async def fetch_ranges():
    connector = aiohttp.TCPConnector(
        limit=20,
        ssl=False
    )

    async with aiohttp.ClientSession(
        connector=connector,
        headers=HEADERS
    ) as session:

        tasks = [
            fetch_single(session, url)
            for url in RANGE_URLS
        ]

        results = await asyncio.gather(*tasks)

    merged = []

    for lines in results:
        merged.extend(lines)

    clean = []

    for x in merged:
        x = x.strip()

        if not x:
            continue

        if x.startswith("#"):
            continue

        clean.append(x)

    return list(dict.fromkeys(clean))
