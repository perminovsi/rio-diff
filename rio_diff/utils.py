import hashlib
import os
from collections.abc import Callable

_HASH_CHUNK_BYTES = 1024 * 1024


def calc_hash(inp_file: str, progress: Callable[[float], None] | None = None) -> str:
    hash = hashlib.md5()
    total = os.path.getsize(inp_file)
    done = 0

    with open(inp_file, "rb") as file:
        for chunk in iter(lambda: file.read(_HASH_CHUNK_BYTES), b""):
            hash.update(chunk)
            if progress is not None and total:
                done += len(chunk)
                progress(done / total)

    return hash.hexdigest()
