import glob
import os

import orjson

from config import RESULTS_DIR

def merge_all_shards():
    all_results = []
    
    files = glob.glob(os.path.join(RESULTS_DIR, "shard_*.json"))
    print(f"Found {len(files)} shard files")
    
    for file in files:
        try:
            with open(file, "rb") as f:
                data = orjson.loads(f.read())
                all_results.extend(data)
                print(f"Loaded {len(data)} results from {os.path.basename(file)}")
        except Exception as e:
            print(f"Error loading {file}: {e}")

    # حذف duplicates (همان IP و پورت)
    unique = {}
    for item in all_results:
        key = f"{item['ip']}:{item['port']}"
        if key not in unique or unique[key]["score"] < item["score"]:
            unique[key] = item

    merged = sorted(
        unique.values(),
        key=lambda x: (x["score"], -x["latency"]),
        reverse=True
    )

    with open("merged.json", "wb") as f:
        f.write(orjson.dumps(merged))

    print(f"Merged results: {len(merged)} unique IP:PORT combinations")
    return merged

if __name__ == "__main__":
    merge_all_shards()
