import os

import orjson

from config import OUTPUT_DIR

def publish():
    with open(
        "merged.json",
        "rb"
    ) as f:

        data = orjson.loads(
            f.read()
        )

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    with open(
        f"{OUTPUT_DIR}/top30.txt",
        "w"
    ) as f:

        for x in data[:30]:
            f.write(
                f"{x['ip']}\n"
            )

    with open(
        f"{OUTPUT_DIR}/top100.txt",
        "w"
    ) as f:

        for x in data[:100]:
            f.write(
                f"{x['ip']}:{x['port']}\n"
            )

    with open(
        f"{OUTPUT_DIR}/api.json",
        "wb"
    ) as f:

        f.write(orjson.dumps(data))

    print(
        f"published: {len(data)}"
    )

if __name__ == "__main__":
    publish()
