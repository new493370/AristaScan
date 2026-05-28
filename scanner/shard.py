def split_into_shards(items, num_shards, shard_id):
    if not items:
        return []

    size = len(items) // num_shards

    start = shard_id * size

    if shard_id == num_shards - 1:
        end = len(items)
    else:
        end = start + size

    return items[start:end]
