import click

from rio_diff import __version__ as plugin_version
from rio_diff.compare import compare_rasters


@click.command("diff", short_help="Compare rasters")
@click.argument("base_raster", type=click.Path(exists=True))
@click.argument("test_raster", type=click.Path(exists=True))
@click.option(
    "--ignore-height",
    default=False,
    is_flag=True,
    help="The number of height will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-width",
    default=False,
    is_flag=True,
    help="The number of width will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-bands",
    default=False,
    is_flag=True,
    help="The number of bands will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-dtype",
    default=False,
    is_flag=True,
    help="Data type will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-nodata",
    default=False,
    is_flag=True,
    help="No data values will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-bbox",
    default=False,
    is_flag=True,
    help="Bounding box will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-crs",
    default=False,
    is_flag=True,
    help="Coordinate reference system will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-transform",
    default=False,
    is_flag=True,
    help="Affine transform will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-metadata",
    default=False,
    is_flag=True,
    help="Metadata will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-stats",
    default=False,
    is_flag=True,
    help="Statistics will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-pixel-values",
    default=False,
    is_flag=True,
    help="Pixel values will be ignored.",
    show_default=True,
)
@click.version_option(version=plugin_version, message="%(version)s")
@click.pass_context
def diff(
    ctx,
    base_raster,
    test_raster,
    ignore_height,
    ignore_width,
    ignore_bands,
    ignore_dtype,
    ignore_nodata,
    ignore_bbox,
    ignore_crs,
    ignore_transform,
    ignore_metadata,
    ignore_stats,
    ignore_pixel_values,
):
    """Rasterio diff plugin.
    """
    compare_rasters(
        base_raster=base_raster,
        test_raster=test_raster,
        ignore_height=ignore_height,
        ignore_width=ignore_width,
        ignore_bands=ignore_bands,
        ignore_dtype=ignore_dtype,
        ignore_nodata=ignore_nodata,
        ignore_bbox=ignore_bbox,
        ignore_crs=ignore_crs,
        ignore_transform=ignore_transform,
        ignore_metadata=ignore_metadata,
        ignore_stats=ignore_stats,
        ignore_pixel_values=ignore_pixel_values,
    )
