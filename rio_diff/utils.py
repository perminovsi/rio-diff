import hashlib


def calc_hash(inp_file: str) -> str:
    hash = hashlib.md5()

    with open(inp_file, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash.update(chunk)

    return hash.hexdigest()
