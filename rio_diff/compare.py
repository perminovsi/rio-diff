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
            or base_ds.count == test_ds.count
            or base_ds.transform == test_ds.transform
            or base_ds.crs == test_ds.crs
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
        bands_stats = []

        diff_profile = None
        diff_data = None
        if diff_raster_path is not None:
            diff_profile = base_ds.profile
            diff_profile.update({
                "dtype": "float32",
                "nodata": None,
            })
            diff_data = np.zeros((base_ds.count, base_ds.height, base_ds.width), dtype="float32")

        total_pixels = base_ds.width * base_ds.height

        for bidx in range(1, base_ds.count + 1):
            diff_count = 0
            max_diff = 0.0
            sum_squared_diff = 0.0

            nd_base = base_ds.nodatavals[bidx - 1] if base_ds.nodatavals else base_ds.nodata
            nd_test = test_ds.nodatavals[bidx - 1] if test_ds.nodatavals else test_ds.nodata

            for _, window in base_ds.block_windows(bidx):
                arr_base = base_ds.read(bidx, window=window)
                arr_test = test_ds.read(bidx, window=window)

                if nd_base is not None:
                    mask_base = arr_base == nd_base
                    arr_base = arr_base.astype("float32", copy=False)
                    arr_base[mask_base] = np.nan

                if nd_test is not None:
                    mask_test = arr_test == nd_test
                    arr_test = arr_test.astype("float32", copy=False)
                    arr_test[mask_test] = np.nan

                arr_diff = arr_base - arr_test

                if diff_data is not None:
                    diff_data[bidx - 1, window.row_off:window.row_off + window.height,
                              window.col_off:window.col_off + window.width] = arr_diff

                close_mask = np.isclose(arr_base, arr_test, rtol=rtol, atol=atol, equal_nan=equal_nan)
                diff_count += np.sum(~close_mask)

                diff_finite = arr_diff[np.isfinite(arr_diff)]
                if diff_finite.size > 0:
                    max_diff = max(max_diff, np.max(np.abs(diff_finite)))

                sum_squared_diff += np.nansum(arr_diff ** 2)

            bands_stats.append(models.PixelDiffStats(
                diff_count=int(diff_count),
                total_count=total_pixels,
                diff_percent=float((diff_count / total_pixels) * 100),
                max_diff=float(max_diff),
                rmse=float(np.sqrt(sum_squared_diff / total_pixels))
            ))

        if diff_raster_path is not None:
            Path(diff_raster_path).parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(diff_raster_path, 'w', **diff_profile) as dst:
                dst.write(diff_data)

        return bands_stats


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
