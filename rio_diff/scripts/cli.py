import click

from rio_diff import __version__ as plugin_version, render
from rio_diff.compare import compare_rasters


@click.command("diff", short_help="Compare rasters")
@click.argument("base_raster", type=click.Path(exists=True))
@click.argument("test_raster", type=click.Path(exists=True))
@click.option(
    "--ignore-bands",
    default=False,
    is_flag=True,
    help="The number of bands will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-shape",
    default=False,
    is_flag=True,
    help="Width and height will be ignored.",
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
    "--ignore-bbox",
    default=False,
    is_flag=True,
    help="Bounding box will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-gcps",
    default=False,
    is_flag=True,
    help="Ground control points and RPCs will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-scales",
    default=False,
    is_flag=True,
    help="Band scales, offsets and units will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-colorinterp",
    default=False,
    is_flag=True,
    help="Color interpretation will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-colormap",
    default=False,
    is_flag=True,
    help="Color palettes will be ignored.",
    show_default=True,
)
@click.option(
    "--ignore-image-structure",
    default=False,
    is_flag=True,
    help="Image structure (driver, compression, interleave, blocks, overviews, mask flags) will be ignored.",
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
    "--ignore-pixels",
    "ignore_pixel_values",
    default=False,
    is_flag=True,
    help="Pixel values will be ignored.",
    show_default=True,
)
@click.option(
    "--checksum",
    "check_checksum",
    default=False,
    is_flag=True,
    help="Also compare the whole-file checksum (strict byte-level equality).",
    show_default=True,
)
@click.option(
    "--save-diff",
    "save_diff",
    type=click.Path(),
    default=None,
    help="Save the per-pixel difference raster (base - test) to the given path.",
)
@click.version_option(version=plugin_version, message="%(version)s")
@click.pass_context
def diff(
    ctx,
    base_raster,
    test_raster,
    ignore_bands,
    ignore_shape,
    ignore_dtype,
    ignore_nodata,
    ignore_crs,
    ignore_transform,
    ignore_bbox,
    ignore_gcps,
    ignore_scales,
    ignore_colorinterp,
    ignore_colormap,
    ignore_image_structure,
    ignore_metadata,
    ignore_stats,
    ignore_pixel_values,
    check_checksum,
    save_diff,
):
    """Rasterio diff plugin.
    """
    report = compare_rasters(
        base_raster,
        test_raster,
        diff_raster_path=save_diff,
        ignore_pixel_values=ignore_pixel_values,
        ignore_stats=ignore_stats,
    )

    if report is None:
        ctx.exit(0)

    checks: list[tuple[str, bool, object, object]] = []

    def add(ignore: bool, diff, label: str) -> None:
        if not ignore:
            checks.append((label, diff.equal, diff.base, diff.test))

    add(not check_checksum, report.checksum, "Checksum")
    add(ignore_bands, report.bands, "Bands")
    add(ignore_shape, report.width, "Width")
    add(ignore_shape, report.height, "Height")
    add(ignore_dtype, report.dtype, "Data type")
    add(ignore_nodata, report.nodata, "NoData")
    add(ignore_crs, report.crs, "CRS")
    add(ignore_transform, report.transform, "Transform")
    add(ignore_bbox, report.bbox, "BBox")
    add(ignore_gcps, report.gcps, "GCPs")
    add(ignore_gcps, report.rpcs, "RPCs")
    add(ignore_scales, report.scales, "Scales")
    add(ignore_scales, report.offsets, "Offsets")
    add(ignore_scales, report.units, "Units")
    add(ignore_colorinterp, report.colorinterp, "Color interpretation")
    add(ignore_colormap, report.colormap, "Colormap")
    add(ignore_image_structure, report.mask_flags, "Mask flags")
    add(ignore_image_structure, report.overviews, "Overviews")
    add(ignore_image_structure, report.image_structure, "Image structure")
    add(ignore_metadata, report.descriptions, "Band descriptions")
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
