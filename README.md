# rio-diff

A rasterio plugin for comparing two raster files and showing differences between them.

## Overview

`rio-diff` is a command-line tool that extends the functionality of [Rasterio](https://github.com/rasterio/rasterio) by providing a way to compare two raster files and highlight their differences. Inspired by the classic Unix `diff` command, this plugin enables users to identify differences in raster properties and pixel values.

## Features

- Compare various raster properties including dimensions, data types, coordinate reference systems, and metadata
- Calculate pixel-by-pixel differences between compatible rasters
- Optionally save the per-pixel difference raster (`base - test`) to disk
- Show statistics on differences including count, percentage, maximum difference, and RMSE
- Support for ignoring specific properties during comparison
- Integration with Rasterio's command-line interface

## Installation

Install the package using pip:

```bash
pip install rio-diff
```

After installation, the plugin will be available as a subcommand of `rio`.

## Usage

Basic usage to compare two raster files:

```bash
rio diff base_raster.tif test_raster.tif
```

### Options

- `--ignore-height`: Ignore the height property during comparison
- `--ignore-width`: Ignore the width property during comparison
- `--ignore-bands`: Ignore the number of bands during comparison
- `--ignore-dtype`: Ignore data type during comparison
- `--ignore-nodata`: Ignore NoData values during comparison
- `--ignore-bbox`: Ignore bounding box during comparison
- `--ignore-crs`: Ignore coordinate reference system during comparison
- `--ignore-transform`: Ignore affine transform during comparison
- `--ignore-metadata`: Ignore metadata during comparison
- `--ignore-stats`: Ignore statistics during comparison
- `--ignore-pixel-values`: Ignore pixel values during comparison
- `--checksum`: Also compare the whole-file checksum (strict byte-level equality; optional, off by default)
- `--save-diff PATH`: Save the per-pixel difference raster (`base - test`) to the given path. When the rasters are byte-identical, the tool exits early and no diff raster is written.
- `--version`: Show version information

### Examples

Compare two raster files with default settings:

```bash
rio diff raster1.tif raster2.tif
```

Ignore metadata differences when comparing:

```bash
rio diff raster1.tif raster2.tif --ignore-metadata
```

Compare rasters but ignore differences in pixel values:

```bash
rio diff raster1.tif raster2.tif --ignore-pixel-values
```

Require strict byte-level equality via the whole-file checksum:

```bash
rio diff raster1.tif raster2.tif --checksum
```

Save the per-pixel difference raster to disk:

```bash
rio diff raster1.tif raster2.tif --save-diff diff.tif
```

If the rasters are byte-identical, the tool exits early and the diff raster is not written.

## Comparison Details

The tool compares the following raster properties:

- **Checksum**: MD5 hash of the file content (only when `--checksum` is passed).
- **Dimensions**: Width and height in pixels
- **Bands**: Number of channels/layers
- **Data Type**: Bit depth and signed/unsigned nature
- **NoData Value**: Value representing missing or invalid data
- **Bounding Box**: Spatial extent in coordinate units
- **CRS**: Coordinate Reference System
- **Transform**: Affine transformation matrix
- **Metadata**: Tags and attributes associated with the raster
- **Statistics**: Basic statistical information about pixel values
- **Pixel Values**: Actual pixel-by-pixel comparison (when rasters are compatible)

For compatible rasters, the tool calculates detailed statistics about pixel differences including:
- Count of different pixels
- Percentage of different pixels
- Maximum difference value
- Root Mean Square Error (RMSE)

## Exit Codes

The command sets its exit code so it can be used in scripts and CI:

- `0`: No differences were found across the compared properties (also returned early when the files are byte-identical).
- `1`: At least one difference was found.
- `2`: Usage error (invalid arguments or missing input files).

Ignored properties (`--ignore-*`) do not affect the exit code. The whole-file checksum only affects it when `--checksum` is passed.

## Inspiration

- [Linux diff command](https://man7.org/linux/man-pages/man1/diff.1.html) - Classic Unix utility for comparing files
- [ArcGIS Raster Compare](https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/raster-compare.htm) - Tool for comparing raster datasets

## License

This project is licensed under the MIT License - see the LICENSE file for details.