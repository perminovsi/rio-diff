import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np
import rasterio
from affine import Affine
from rasterio.coords import BoundingBox
from rasterio.crs import CRS


@dataclass
class RasterProps:
    width: int
    height: int
    bands: int
    dtype: str
    nodata: float | None
    bbox: BoundingBox
    crs: CRS
    transform: Affine
    metadata: list[dict[str, Any]]
    bands_metadata: list
    stats: list


def calc_hash(inp_file: str) -> str:
    hash = hashlib.md5()

    with open(inp_file, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            hash.update(chunk)

    return hash.hexdigest()


def read_raster_props(inp_file: str) -> RasterProps:
    with rasterio.open(inp_file) as ds:
        return RasterProps(
            width=ds.profile["width"],
            height=ds.profile["height"],
            bands=ds.profile["count"],
            dtype=ds.profile["dtype"],
            nodata=ds.profile["nodata"],  # TODO: проверка для разных каналов
            bbox=ds.bounds,
            crs=ds.profile["crs"],
            transform=ds.profile["transform"],
            metadata=ds.tags(),
            bands_metadata=[ds.tags(bidx=bidx) for bidx in range(1, ds.count + 1)],
            stats=ds.stats(),  # TODO: безопаснее будет считать самому по numpy
        )


def calc_diff(base_raster: str, test_raster: str, *, rtol=0, atol=0, equal_nan=True) -> bool:
    """Вычитать первый растр из второго для получения diff-a и его последующего анализа
    Сколько пикселей отличается, насколько они отличаются и т.п.
    Опционально выводить график (картинку) и возможность сохранения diff-a на диск
    """
    with rasterio.open(base_raster) as base, rasterio.open(test_raster) as test:
        if (
            base.count != test.count or
            base.shape != test.shape or
            base.transform != test.transform or
            base.crs != test.crs or
            base.dtypes != test.dtypes
        ):
            return False

        for bidx in range(1, base.count + 1):
            nd_base= base.nodatavals[bidx - 1] if base.nodatavals else base.nodata
            nd_test = test.nodatavals[bidx - 1] if test.nodatavals else test.nodata

            for _, window in base.block_windows(bidx):
                arr_base = base.read(bidx, window=window)
                arr_test = test.read(bidx, window=window)

                if nd_base is not None:
                    mask_base = arr_base == nd_base
                    arr_base = arr_base.astype("float64", copy=False)
                    arr_base[mask_base] = np.nan
                if nd_test is not None:
                    mask_test = arr_test == nd_test
                    arr_test = arr_test.astype("float64", copy=False)
                    arr_test[mask_test] = np.nan

                if not np.allclose(arr_base, arr_test, rtol=rtol, atol=atol, equal_nan=equal_nan):
                    return False

        return True


def compare_rasters(
    base_raster: str,
    test_raster: str,
    *,
    ignore_height: bool = False,
    ignore_width: bool = False,
    ignore_bands: bool = False,
    ignore_dtype: bool = False,
    ignore_nodata: bool = False,
    ignore_bbox: bool = False,
    ignore_crs: bool = False,
    ignore_transform: bool = False,
    ignore_metadata: bool = False,
    ignore_stats: bool = False,
    ignore_pixel_values: bool = False,
) -> bool:
    is_equal = True
    if calc_hash(base_raster) == calc_hash(test_raster):
        return is_equal

    base_props = read_raster_props(base_raster)
    test_props = read_raster_props(test_raster)

    if not ignore_height:
        if base_props.height != test_props.height:
            print(f"< height: {base_props.height}")
            print("---")
            print(f"> height: {test_props.height}")
            print("")
            is_equal = False

    if not ignore_width:
        if base_props.width != test_props.width:
            print(f"< width: {base_props.width}")
            print("---")
            print(f"> width: {test_props.width}")
            print("")
            is_equal = False

    if not ignore_bands:
        if base_props.bands != test_props.bands:
            print(f"< bands: {base_props.bands}")
            print("---")
            print(f"> bands: {test_props.bands}")
            print("")
            is_equal = False

    if not ignore_dtype:
        if base_props.dtype != test_props.dtype:
            print(f"< dtype: {base_props.dtype}")
            print("---")
            print(f"> dtype: {test_props.dtype}")
            print("")
            is_equal = False

    if not ignore_nodata:
        if base_props.nodata != test_props.nodata:
            print(f"< nodata: {base_props.nodata}")
            print("---")
            print(f"> nodata: {test_props.nodata}")
            print("")
            is_equal = False

    if not ignore_bbox:
        if base_props.bbox != test_props.bbox:
            print(f"< bbox: {base_props.bbox}")
            print("---")
            print(f"> bbox: {test_props.bbox}")
            print("")
            is_equal = False

    if not ignore_crs:
        if base_props.crs != test_props.crs:
            print(f"< crs: {base_props.crs}")
            print("---")
            print(f"> crs: {test_props.crs}")
            print("")
            is_equal = False

    if not ignore_transform:
        if base_props.transform != test_props.transform:
            print(f"< geotransform: {base_props.transform}")
            print("---")
            print(f"> geotransform: {test_props.transform}")
            print("")
            is_equal = False

    if not ignore_metadata:
        # TODO: выводить конкретно в чем разница и для какого канала
        if base_props.metadata != test_props.metadata:
            print(f"< metadata: {base_props.metadata}")
            print("---")
            print(f"> metadata: {test_props.metadata}")
            print("")
            is_equal = False

        if base_props.bands_metadata != test_props.bands_metadata:
            print(f"< bands metadata: {base_props.bands_metadata}")
            print("---")
            print(f"> bands metadata: {test_props.bands_metadata}")
            print("")
            is_equal = False

    if not ignore_stats:
        if base_props.stats != test_props.stats:
            # TODO: выводить детально в каких каналах и в чем различия
            print(f"< statistics: {base_props.stats}")
            print("---")
            print(f"> statistics: {test_props.stats}")
            print("")
            is_equal = False

    if not ignore_pixel_values:
        if calc_diff(base_raster, test_raster) is False:
            print("< pixel values: ...") # TODO: добавить подробный вывод в чем отличия у пикселей
            print("---")
            print("> pixel values: ...")
            print("")
            is_equal = False

    return is_equal


if __name__ == "__main__":
    # rs = calc_hash("temp/2025110312/gfs.2025110312.003.cape_180-0.tif")

    # rs = read_raster_props("temp/icon/OLD.icon.2026010200.003.t_2m.tif")

    # rs = calc_diff(
    #     "temp/icon/OLD.icon.2026010200.003.t_2m.tif",
    #     # "temp/icon/NEW.icon.2026010200.003.t_2m.tif",
    #     "temp/icon/OLD.icon.2026010200.003.td_2m.tif",
    # )

    rs = compare_rasters(
        "temp/icon/OLD.icon.2026010200.003.t_2m.tif",
        "temp/icon/NEW.icon.2026010200.003.t_2m.tif",
        # "temp/icon/OLD.icon.2026010200.003.td_2m.tif",
        ignore_height=False,
        ignore_width=False,
        ignore_bands=False,
        ignore_dtype=False,
        ignore_nodata=False,
        ignore_bbox=False,
        ignore_crs=False,
        ignore_transform=False,
        ignore_metadata=True,
        ignore_stats=False,
        ignore_pixel_values=False,
    )

    print(rs)
