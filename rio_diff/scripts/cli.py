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
    
    if report.checksum.equal is True:
        return

    if not ignore_checksum and not report.checksum.equal:
        click.secho(f'< Checksum: {report.checksum.base}', fg="red")
        click.secho(f'> Checksum: {report.checksum.test}', fg="green")
        click.echo("")

    if not ignore_width and not report.width.equal:
        click.secho(f'< Width: {report.width.base}', fg="red")
        click.secho(f'> Width: {report.width.test}', fg="green")
        click.echo("")

    if not ignore_height and not report.height.equal:
        click.secho(f'< Height: {report.height.base}', fg="red")
        click.secho(f'> Height: {report.height.test}', fg="green")
        click.echo("")

    if not ignore_bands and not report.bands.equal:
        click.secho(f'< Bands: {report.bands.base}', fg="red")
        click.secho(f'> Bands: {report.bands.test}', fg="green")
        click.echo("")

    if not ignore_dtype and not report.dtype.equal:
        click.secho(f'< Data Type: {report.dtype.base}', fg="red")
        click.secho(f'> Data Type: {report.dtype.test}', fg="green")
        click.echo("")

    if not ignore_nodata and not report.nodata.equal:
        click.secho(f'< NoData: {report.nodata.base}', fg="red")
        click.secho(f'> NoData: {report.nodata.test}', fg="green")
        click.echo("")

    if not ignore_bbox and not report.bbox.equal:
        click.secho(f'< BBox: {report.bbox.base}', fg="red")
        click.secho(f'> BBox: {report.bbox.test}', fg="green")
        click.echo("")

    if not ignore_crs and not report.crs.equal:
        click.secho(f'< CRS: {report.crs.base}', fg="red")
        click.secho(f'> CRS: {report.crs.test}', fg="green")
        click.echo("")

    if not ignore_transform and not report.transform.equal:
        click.secho(f'< Transform: {report.transform.base}', fg="red")
        click.secho(f'> Transform: {report.transform.test}', fg="green")
        click.echo("")

    if not ignore_metadata:
        if not report.metadata.equal:
            click.secho(f'< Metadata: {report.metadata.base}', fg="red")
            click.secho(f'> Metadata: {report.metadata.test}', fg="green")
            click.echo("")
        # TODO: выводить конкретно в чем разница и для какого канала
        if not report.bands_metadata.equal:
            click.secho(f'< Bands Metadata: {report.bands_metadata.base}', fg="red")
            click.secho(f'> Bands Metadata: {report.bands_metadata.test}', fg="green")
            click.echo("")

    if not ignore_stats and not report.stats.equal:
        # TODO: выводить детально в каких каналах и в чем различия
        click.secho(f'< Statistics: {report.stats.base}', fg="red")
        click.secho(f'> Statistics: {report.stats.test}', fg="green")
        click.echo("")

    if not ignore_pixel_values:
        if report.pixel_values is None:
            click.secho("Pixel Values: Rasters are incompatible", fg="red")
        else:
            for bidx, stat in enumerate(report.pixel_values, start=1):
                if stat.diff_count > 0:
                    click.secho(f"Pixel Values (Band {bidx}): ", fg="red")
                    click.secho(f"\tDifferent pixels: {stat.diff_count} ({stat.diff_percent:.2f}%)", fg="red")
                    click.secho(f"\tMax diff: {stat.max_diff}", fg="red")
                    click.secho(f"\tRMSE: {stat.rmse}", fg="red")
