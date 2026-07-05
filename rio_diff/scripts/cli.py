import click

from rio_diff import __version__ as plugin_version, render
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
    help="NoData values will be ignored.",
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
@click.option(
    "--ignore-checksum",
    default=False,
    is_flag=True,
    help="Checksum will be ignored.",
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
    ignore_checksum,
):
    """Rasterio diff plugin.
    """
    report = compare_rasters(base_raster, test_raster)

    checks: list[tuple[str, bool, object, object]] = []

    def add(ignore: bool, diff, label: str) -> None:
        if not ignore:
            checks.append((label, diff.equal, diff.base, diff.test))

    add(ignore_checksum, report.checksum, "Checksum")
    add(ignore_width, report.width, "Width")
    add(ignore_height, report.height, "Height")
    add(ignore_bands, report.bands, "Bands")
    add(ignore_dtype, report.dtype, "Data type")
    add(ignore_nodata, report.nodata, "NoData")
    add(ignore_bbox, report.bbox, "BBox")
    add(ignore_crs, report.crs, "CRS")
    add(ignore_transform, report.transform, "Transform")
    add(ignore_metadata, report.metadata, "Metadata")
    # TODO: выводить конкретно в чем разница и для какого канала
    add(ignore_metadata, report.bands_metadata, "Bands metadata")
    # TODO: выводить детально в каких каналах и в чем различия
    add(ignore_stats, report.stats, "Statistics")

    has_diff = render.print_report(
        checks,
        report.pixel_values,
        show_pixel_values=not ignore_pixel_values,
    )
    ctx.exit(1 if has_diff else 0)
