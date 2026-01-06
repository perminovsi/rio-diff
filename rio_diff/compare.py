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


def compare_rasters(base_raster: str, test_raster: str) -> models.RasterDiff:
    base_md5 = utils.calc_hash(base_raster)
    test_md5 = utils.calc_hash(test_raster)

    base_props = read_raster_props(base_raster)
    test_props = read_raster_props(test_raster)

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
        pixel_values=calc_diff(base_raster, test_raster),
    )
