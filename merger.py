import glob
import os

import orjson

from config import RESULTS_DIR

def merge_all_shards():
    all_results = []

    for file in glob.glob(
        os.path.join(
            RESULTS_DIR,
            "shard_*.json"
        )
    ):
        with open(file, "rb") as f:
            all_results.extend(
                orjson.loads(f.read())
            )

    unique = {}

    for item in all_results:
        key = f"{item['ip']}:{item['port']}"

        if (
            key not in unique or
            unique[key]["score"] < item["score"]
        ):
            unique[key] = item

    merged = sorted(
        unique.values(),
        key=lambda x: (
            x["score"],
            -x["latency"]
        ),
        reverse=True
    )

    with open(
        "merged.json",
        "wb"
    ) as f:
        f.write(orjson.dumps(merged))

    print(
        f"merged results: {len(merged)}"
    )

if __name__ == "__main__":
    merge_all_shards()
