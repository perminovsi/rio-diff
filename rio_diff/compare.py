import warnings
from pathlib import Path

import numpy as np
import rasterio

from rio_diff import models, utils


def read_raster_props(inp_file: str) -> models.RasterProps:
    with rasterio.open(inp_file) as ds:
        return models.RasterProps(
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


def is_compatible_rasters(base_raster: str, test_raster: str) -> bool:
    """Проверить совместимость двух растров.

    Учитывается:
    - количество ячеек растра (столбцов и строк);
    - количество каналов;
    - система координат;
    - геопривязка (параметры афинного преобразования).
    """
    with rasterio.open(base_raster) as base_ds, rasterio.open(test_raster) as test_ds:
        if (
            base_ds.shape == test_ds.shape
            and base_ds.count == test_ds.count
            and base_ds.transform == test_ds.transform
            and base_ds.crs == test_ds.crs
        ):
            return True
    return False


def calc_diff(
    base_raster: str,
    test_raster: str,
    *,
    rtol=0,
    atol=0,
    equal_nan=True,
    diff_raster_path: str | None = None,
) -> list[models.PixelDiffStats]:
    """Вычитать первый растр из второго для получения diff-a и его последующего анализа
    Сколько пикселей отличается, насколько они отличаются и т.п.
    Опционально выводить график (картинку) и возможность сохранения diff-a на диск
    """
    with rasterio.open(base_raster) as base_ds, rasterio.open(test_raster) as test_ds:
        count = base_ds.count
        total_pixels = base_ds.width * base_ds.height

        nd_base = base_ds.nodatavals
        nd_test = test_ds.nodatavals

        diff_count = np.zeros(count, dtype=np.int64)
        valid_count = np.zeros(count, dtype=np.int64)
        max_diff = np.zeros(count, dtype=np.float64)
        sum_squared_diff = np.zeros(count, dtype=np.float64)

        diff_ds = None
        if diff_raster_path is not None:
            diff_profile = base_ds.profile
            diff_profile.update({
                "dtype": "float32",
                "nodata": None,
            })
            Path(diff_raster_path).parent.mkdir(parents=True, exist_ok=True)
            diff_ds = rasterio.open(diff_raster_path, "w", **diff_profile)

        try:
            # Обрабатываем растр окно за окном (по всем каналам сразу), чтобы не
            # держать весь diff в памяти и читать каждый блок только один раз.
            for _, window in base_ds.block_windows(1):
                arr_base = base_ds.read(window=window).astype("float32")
                arr_test = test_ds.read(window=window).astype("float32")

                for b in range(count):
                    if nd_base[b] is not None:
                        arr_base[b][arr_base[b] == nd_base[b]] = np.nan
                    if nd_test[b] is not None:
                        arr_test[b][arr_test[b] == nd_test[b]] = np.nan

                arr_diff = arr_base - arr_test
                finite_mask = np.isfinite(arr_diff)
                valid_count += np.count_nonzero(finite_mask, axis=(1, 2))

                if diff_ds is not None:
                    diff_ds.write(arr_diff, window=window)

                close_mask = np.isclose(arr_base, arr_test, rtol=rtol, atol=atol, equal_nan=equal_nan)
                diff_count += np.count_nonzero(~close_mask, axis=(1, 2))

                abs_diff = np.abs(arr_diff)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)  # окно целиком из NaN
                    band_max = np.nanmax(abs_diff, axis=(1, 2))
                band_max = np.nan_to_num(band_max, nan=0.0)
                max_diff = np.maximum(max_diff, band_max)

                sum_squared_diff += np.nansum(arr_diff ** 2, axis=(1, 2))
        finally:
            if diff_ds is not None:
                diff_ds.close()

        return [
            models.PixelDiffStats(
                diff_count=int(diff_count[b]),
                total_count=total_pixels,
                diff_percent=float((diff_count[b] / total_pixels) * 100),
                max_diff=float(max_diff[b]),
                rmse=float(np.sqrt(sum_squared_diff[b] / valid_count[b])) if valid_count[b] else 0.0,
            )
            for b in range(count)
        ]


def compare_rasters(base_raster: str, test_raster: str) -> models.RasterDiff:
    base_md5 = utils.calc_hash(base_raster)
    test_md5 = utils.calc_hash(test_raster)

    base_props = read_raster_props(base_raster)
    test_props = read_raster_props(test_raster)

    pixel_values = None
    if is_compatible_rasters(base_raster, test_raster):
        pixel_values = calc_diff(base_raster, test_raster)

    return models.RasterDiff(
        checksum=models.DiffStr(
            equal=base_md5 == test_md5,
            base=base_md5,
            test=test_md5,
        ),
        bands=models.DiffInt(
            equal=base_props.bands == test_props.bands,
            base=base_props.bands,
            test=test_props.bands,
        ),
        width=models.DiffInt(
            equal=base_props.width == test_props.width,
            base=base_props.width,
            test=test_props.width,
        ),
        height=models.DiffInt(
            equal=base_props.height == test_props.height,
            base=base_props.height,
            test=test_props.height,
        ),
        dtype=models.DiffStr(
            equal=base_props.dtype == test_props.dtype,
            base=base_props.dtype,
            test=test_props.dtype,
        ),
        nodata=models.DiffOptionalFloat(
            equal=base_props.nodata == test_props.nodata,
            base=base_props.nodata,
            test=test_props.nodata,
        ),
        bbox=models.DiffBbox(
            equal=base_props.bbox == test_props.bbox,
            base=base_props.bbox,
            test=test_props.bbox,
        ),
        crs=models.DiffCRS(
            equal=base_props.crs == test_props.crs,
            base=base_props.crs,
            test=test_props.crs,
        ),
        transform=models.DiffTransform(
            equal=base_props.transform == test_props.transform,
            base=base_props.transform,
            test=test_props.transform,
        ),
        metadata=models.DiffList(
            equal=base_props.metadata == test_props.metadata,
            base=base_props.metadata,
            test=test_props.metadata,
        ),
        bands_metadata=models.DiffList(
            equal=base_props.bands_metadata == test_props.bands_metadata,
            base=base_props.bands_metadata,
            test=test_props.bands_metadata,
        ),
        stats=models.DiffList(
            equal=base_props.stats == test_props.stats,
            base=base_props.stats,
            test=test_props.stats,
        ),
        pixel_values=pixel_values,
    )
