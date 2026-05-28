import os
import tempfile

import orjson
import portalocker

from config import CACHE_FILE

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with portalocker.Lock(
            CACHE_FILE,
            "rb",
            timeout=10
        ) as f:

            raw = f.read()

            if not raw:
                return {}

            return orjson.loads(raw)

    except Exception:
        return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

    fd, temp_path = tempfile.mkstemp()

    try:
        with os.fdopen(fd, "wb") as tmp:
            tmp.write(orjson.dumps(cache))

        with portalocker.Lock(
            CACHE_FILE,
            "wb",
            timeout=10
        ) as f:

            with open(temp_path, "rb") as tmp:
                f.write(tmp.read())

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
