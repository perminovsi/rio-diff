import math
import warnings
from collections.abc import Callable
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import MaskFlags

from rio_diff import models, utils

# Ограничение блок-кэша GDAL. По умолчанию GDAL отводит под кэш ~5% ОЗУ, из-за
# чего сквозной обход всех тайлов растра раздувает потребление памяти до
# нескольких ГБ. Каждый тайл здесь читается ровно один раз, поэтому кэш
# бесполезен и его можно держать маленьким.
GDAL_CACHEMAX_BYTES = 256 * 1024 * 1024


_EXCLUDED_TAG_NAMESPACES = {"IMAGE_STRUCTURE", "DERIVED_SUBDATASETS", "RPC"}


def _read_colormaps(ds) -> list:
    colormaps = []
    for bidx in range(1, ds.count + 1):
        try:
            colormaps.append(ds.colormap(bidx))
        except ValueError:
            colormaps.append(None)
    return colormaps


def _read_metadata(ds) -> dict:
    namespaces = [ns for ns in ds.tag_namespaces() if ns not in _EXCLUDED_TAG_NAMESPACES]
    return {"default": ds.tags(), **{ns: ds.tags(ns=ns) for ns in namespaces}}


def read_raster_props(inp_file: str) -> models.RasterProps:
    with rasterio.open(inp_file) as ds:
        gcp_points, gcp_crs = ds.gcps
        return models.RasterProps(
            width=ds.profile["width"],
            height=ds.profile["height"],
            bands=ds.profile["count"],
            dtype=ds.profile["dtype"],
            nodata=ds.nodatavals,
            bbox=ds.bounds,
            crs=ds.profile["crs"],
            transform=ds.profile["transform"],
            gcps={
                "points": [point.asdict() for point in gcp_points],
                "crs": str(gcp_crs) if gcp_crs else None,
            },
            rpcs=ds.rpcs.to_dict() if ds.rpcs else None,
            scales=ds.scales,
            offsets=ds.offsets,
            units=ds.units,
            colorinterp=tuple(ci.name for ci in ds.colorinterp),
            descriptions=ds.descriptions,
            colormap=_read_colormaps(ds),
            mask_flags=[[flag.name for flag in flags] for flags in ds.mask_flag_enums],
            overviews=[ds.overviews(bidx) for bidx in range(1, ds.count + 1)],
            image_structure={
                "driver": ds.driver,
                "compression": ds.compression.name if ds.compression else None,
                "interleave": ds.interleaving.name if ds.interleaving else None,
                "photometric": ds.photometric.name if ds.photometric else None,
                "block_shapes": ds.block_shapes,
                "subdatasets": ds.subdatasets,
            },
            metadata=_read_metadata(ds),
            bands_metadata=[ds.tags(bidx=bidx) for bidx in range(1, ds.count + 1)],
        )


def _nodata_equal(base: tuple, test: tuple) -> bool:
    if len(base) != len(test):
        return False
    return all(
        b == t or (b is not None and t is not None and math.isnan(b) and math.isnan(t))
        for b, t in zip(base, test)
    )


class _StatsAccumulator:
    """Потоковый расчёт min/max/mean/std по каналам.

    ``ds.stats()`` не подходит: GDAL предпочитает статистику из тегов
    STATISTICS_* и может вернуть устаревшие значения, не соответствующие
    данным. Считаем сами по окнам, не держа растр в памяти целиком.
    """

    def __init__(self, count: int):
        self.valid = np.zeros(count, dtype=np.int64)
        self.total = np.zeros(count, dtype=np.float64)
        self.total_sq = np.zeros(count, dtype=np.float64)
        self.min = np.full(count, np.inf)
        self.max = np.full(count, -np.inf)

    def update(self, arr: np.ndarray) -> None:
        self.valid += np.count_nonzero(np.isfinite(arr), axis=(1, 2))
        self.total += np.nansum(arr, axis=(1, 2))
        self.total_sq += np.nansum(arr ** 2, axis=(1, 2))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # окно целиком из NaN
            self.min = np.fmin(self.min, np.nanmin(arr, axis=(1, 2)))
            self.max = np.fmax(self.max, np.nanmax(arr, axis=(1, 2)))

    def result(self) -> list[models.BandStats]:
        stats = []
        for b in range(len(self.valid)):
            n = int(self.valid[b])
            if not n:
                stats.append(models.BandStats(min=None, max=None, mean=None, std=None))
                continue
            mean = self.total[b] / n
            variance = max(self.total_sq[b] / n - mean * mean, 0.0)
            stats.append(models.BandStats(
                min=float(self.min[b]),
                max=float(self.max[b]),
                mean=float(mean),
                std=float(math.sqrt(variance)),
            ))
        return stats


def _needs_mask_read(ds) -> bool:
    return any(
        MaskFlags.per_dataset in flags or MaskFlags.alpha in flags
        for flags in ds.mask_flag_enums
    )


def _mask_nodata(arr: np.ndarray, nodatavals: tuple) -> None:
    for b, nodata in enumerate(nodatavals):
        if nodata is not None:
            arr[b][arr[b] == nodata] = np.nan


def calc_stats(
    raster_path: str,
    progress: Callable[[float], None] | None = None,
) -> list[models.BandStats]:
    with rasterio.Env(GDAL_CACHEMAX=GDAL_CACHEMAX_BYTES), \
            rasterio.open(raster_path) as ds:
        acc = _StatsAccumulator(ds.count)
        needs_mask = _needs_mask_read(ds)
        windows = [window for _, window in ds.block_windows(1)]
        for done, window in enumerate(windows, start=1):
            arr = ds.read(window=window).astype("float64")
            _mask_nodata(arr, ds.nodatavals)
            if needs_mask:
                arr[ds.read_masks(window=window) == 0] = np.nan
            acc.update(arr)
            if progress is not None:
                progress(done / len(windows))
        return acc.result()


def is_compatible_rasters(base_raster: str, test_raster: str) -> bool:
    """Проверить, что растры можно сравнить попиксельно.

    Для попиксельного diff-а массивы должны совпадать по форме, поэтому
    проверяется только то, без чего вычитание невозможно:
    - количество ячеек растра (столбцов и строк);
    - количество каналов.

    Различия в геопривязке (transform) и системе координат (crs) не мешают
    вычитанию массивов и репортятся отдельно, поэтому здесь не учитываются.
    """
    with rasterio.open(base_raster) as base_ds, rasterio.open(test_raster) as test_ds:
        return base_ds.shape == test_ds.shape and base_ds.count == test_ds.count


def calc_diff(
    base_raster: str,
    test_raster: str,
    *,
    rtol=0,
    atol=0,
    equal_nan=True,
    diff_raster_path: str | None = None,
    collect_stats: bool = True,
    progress: Callable[[float], None] | None = None,
) -> tuple[list[models.PixelDiffStats], list[models.BandStats], list[models.BandStats]]:
    """Вычитать первый растр из второго для получения diff-a и его последующего анализа
    Сколько пикселей отличается, насколько они отличаются и т.п.
    Опционально выводить график (картинку) и возможность сохранения diff-a на диск
    """
    with rasterio.Env(GDAL_CACHEMAX=GDAL_CACHEMAX_BYTES), \
            rasterio.open(base_raster) as base_ds, \
            rasterio.open(test_raster) as test_ds:
        count = base_ds.count
        total_pixels = base_ds.width * base_ds.height

        nd_base = base_ds.nodatavals
        nd_test = test_ds.nodatavals

        diff_count = np.zeros(count, dtype=np.int64)
        valid_count = np.zeros(count, dtype=np.int64)
        max_diff = np.zeros(count, dtype=np.float64)
        sum_squared_diff = np.zeros(count, dtype=np.float64)
        mask_diff_count = np.zeros(count, dtype=np.int64)

        compare_masks = any(
            MaskFlags.per_dataset in flags
            for flags in (*base_ds.mask_flag_enums, *test_ds.mask_flag_enums)
        )
        base_acc = _StatsAccumulator(count) if collect_stats else None
        test_acc = _StatsAccumulator(count) if collect_stats else None
        base_needs_mask = collect_stats and _needs_mask_read(base_ds)
        test_needs_mask = collect_stats and _needs_mask_read(test_ds)

        diff_ds = None
        if diff_raster_path is not None:
            diff_profile = base_ds.profile
            diff_profile.update({
                "dtype": "float32",
                "nodata": float("nan"),
                "compress": "deflate",
                "predictor": 3,
                "zlevel": 6,
            })
            Path(diff_raster_path).parent.mkdir(parents=True, exist_ok=True)
            diff_ds = rasterio.open(diff_raster_path, "w", **diff_profile)

        try:
            # Обрабатываем растр окно за окном (по всем каналам сразу), чтобы не
            # держать весь diff в памяти и читать каждый блок только один раз.
            windows = [window for _, window in base_ds.block_windows(1)]
            for done, window in enumerate(windows, start=1):
                arr_base = base_ds.read(window=window).astype("float64")
                arr_test = test_ds.read(window=window).astype("float64")

                _mask_nodata(arr_base, nd_base)
                _mask_nodata(arr_test, nd_test)

                arr_diff = arr_base - arr_test
                finite_mask = np.isfinite(arr_diff)
                valid_count += np.count_nonzero(finite_mask, axis=(1, 2))

                if diff_ds is not None:
                    diff_ds.write(arr_diff.astype("float32"), window=window)

                base_masks = test_masks = None
                if compare_masks or base_needs_mask:
                    base_masks = base_ds.read_masks(window=window)
                if compare_masks or test_needs_mask:
                    test_masks = test_ds.read_masks(window=window)
                if compare_masks:
                    mask_diff_count += np.count_nonzero(base_masks != test_masks, axis=(1, 2))

                close_mask = np.isclose(arr_base, arr_test, rtol=rtol, atol=atol, equal_nan=equal_nan)
                diff_count += np.count_nonzero(~close_mask, axis=(1, 2))

                abs_diff = np.abs(arr_diff)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)  # окно целиком из NaN
                    band_max = np.nanmax(abs_diff, axis=(1, 2))
                band_max = np.nan_to_num(band_max, nan=0.0)
                max_diff = np.maximum(max_diff, band_max)

                sum_squared_diff += np.nansum(arr_diff ** 2, axis=(1, 2))

                if collect_stats:
                    if base_needs_mask:
                        arr_base[base_masks == 0] = np.nan
                    if test_needs_mask:
                        arr_test[test_masks == 0] = np.nan
                    base_acc.update(arr_base)
                    test_acc.update(arr_test)

                if progress is not None:
                    progress(done / len(windows))
        finally:
            if diff_ds is not None:
                diff_ds.close()

        pixel_stats = [
            models.PixelDiffStats(
                diff_count=int(diff_count[b]),
                total_count=total_pixels,
                diff_percent=float((diff_count[b] / total_pixels) * 100),
                max_diff=float(max_diff[b]),
                rmse=float(np.sqrt(sum_squared_diff[b] / valid_count[b])) if valid_count[b] else 0.0,
                mask_diff_count=int(mask_diff_count[b]),
            )
            for b in range(count)
        ]
        base_stats = base_acc.result() if collect_stats else []
        test_stats = test_acc.result() if collect_stats else []
        return pixel_stats, base_stats, test_stats


def _phase(
    progress: Callable[[float, str], None] | None, message: str,
) -> Callable[[float], None] | None:
    if progress is None:
        return None
    return lambda complete: progress(complete, message)


def compare_rasters(
    base_raster: str,
    test_raster: str,
    *,
    diff_raster_path: str | None = None,
    ignore_pixel_values: bool = False,
    ignore_stats: bool = False,
    progress: Callable[[float, str], None] | None = None,
) -> models.RasterDiff | None:
    base_md5 = utils.calc_hash(base_raster, progress=_phase(progress, "Hashing base raster"))
    test_md5 = utils.calc_hash(test_raster, progress=_phase(progress, "Hashing test raster"))

    if base_md5 == test_md5:
        return None

    # Отключаем GDAL PAM, чтобы чтение и запись растров не создавали
    # сайдкар-файлы <растр>.aux.xml рядом с входными данными.
    with rasterio.Env(GDAL_PAM_ENABLED="NO"):
        base_props = read_raster_props(base_raster)
        test_props = read_raster_props(test_raster)

        pixel_values = None
        base_stats: list[models.BandStats] = []
        test_stats: list[models.BandStats] = []
        need_pixel_diff = not ignore_pixel_values or diff_raster_path is not None
        if need_pixel_diff and is_compatible_rasters(base_raster, test_raster):
            pixel_values, base_stats, test_stats = calc_diff(
                base_raster,
                test_raster,
                diff_raster_path=diff_raster_path,
                collect_stats=not ignore_stats,
                progress=_phase(progress, "Comparing pixels"),
            )
        elif not ignore_stats:
            base_stats = calc_stats(base_raster, progress=_phase(progress, "Computing base statistics"))
            test_stats = calc_stats(test_raster, progress=_phase(progress, "Computing test statistics"))

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
        nodata=models.DiffTuple(
            equal=_nodata_equal(base_props.nodata, test_props.nodata),
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
        gcps=models.DiffDict(
            equal=base_props.gcps == test_props.gcps,
            base=base_props.gcps,
            test=test_props.gcps,
        ),
        rpcs=models.DiffOptionalDict(
            equal=base_props.rpcs == test_props.rpcs,
            base=base_props.rpcs,
            test=test_props.rpcs,
        ),
        scales=models.DiffTuple(
            equal=base_props.scales == test_props.scales,
            base=base_props.scales,
            test=test_props.scales,
        ),
        offsets=models.DiffTuple(
            equal=base_props.offsets == test_props.offsets,
            base=base_props.offsets,
            test=test_props.offsets,
        ),
        units=models.DiffTuple(
            equal=base_props.units == test_props.units,
            base=base_props.units,
            test=test_props.units,
        ),
        colorinterp=models.DiffTuple(
            equal=base_props.colorinterp == test_props.colorinterp,
            base=base_props.colorinterp,
            test=test_props.colorinterp,
        ),
        descriptions=models.DiffTuple(
            equal=base_props.descriptions == test_props.descriptions,
            base=base_props.descriptions,
            test=test_props.descriptions,
        ),
        colormap=models.DiffList(
            equal=base_props.colormap == test_props.colormap,
            base=base_props.colormap,
            test=test_props.colormap,
        ),
        mask_flags=models.DiffList(
            equal=base_props.mask_flags == test_props.mask_flags,
            base=base_props.mask_flags,
            test=test_props.mask_flags,
        ),
        overviews=models.DiffList(
            equal=base_props.overviews == test_props.overviews,
            base=base_props.overviews,
            test=test_props.overviews,
        ),
        image_structure=models.DiffDict(
            equal=base_props.image_structure == test_props.image_structure,
            base=base_props.image_structure,
            test=test_props.image_structure,
        ),
        metadata=models.DiffDict(
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
            equal=base_stats == test_stats,
            base=base_stats,
            test=test_stats,
        ),
        pixel_values=pixel_values,
    )
