import hashlib

import rasterio


def calc_hash(inp_file: str) -> str:
    hash = hashlib.md5()

    with open(inp_file, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash.update(chunk)

    return hash.hexdigest()


def read_raster_props(inp_file: str):
    with rasterio.open(inp_file) as ds:
        print(ds.bounds)
        print(ds.profile)
        print(ds.tags())
        print(ds.stats())  # безопаснее будет считать самому по numpy


def calc_diff():
    """Вычитать первый растр из второго для получения diff-a и его последующего анализа
    Сколько пикселей отличается, насколько они отличаются и т.п.
    Опционально выводить график (картинку) и возможность сохранения diff-a на диск
    """
    pass


def raster_diff(*args, verbose: bool = False) -> bool:
    hash_list = []
    for inp_file in args:
        hash_list.append(calc_hash(inp_file))

    if len(set(hash_list)) == 1:
        return True

    return False


if __name__ == "__main__":
    # rs = calc_hash("temp/2025110312/gfs.2025110312.003.cape_180-0.tif")

    rs = read_raster_props("temp/2025110312/gfs.2025110312.003.cape_180-0.tif")

    # rs = raster_diff(
    #     "temp/2025110312/gfs.2025110312.003.cape_180-0.tif",
    #     # "temp/2025110312/gfs.2025110312.003.cape_180-0.tif",
    #     "temp/2025110312/gfs.2025110312.006.cape_180-0.tif",
    # )

    print(rs)
