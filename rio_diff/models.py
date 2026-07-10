from dataclasses import dataclass
from typing import Any

from affine import Affine
from rasterio.coords import BoundingBox
from rasterio.crs import CRS


@dataclass
class RasterProps:
    width: int
    height: int
    bands: int
    dtype: str
    nodata: tuple
    bbox: BoundingBox
    crs: CRS
    transform: Affine
    gcps: dict
    rpcs: dict | None
    scales: tuple
    offsets: tuple
    units: tuple
    colorinterp: tuple
    descriptions: tuple
    colormap: list
    mask_flags: list
    overviews: list
    image_structure: dict
    metadata: dict[str, dict[str, Any]]
    bands_metadata: list
    stats: list


@dataclass
class DiffStr:
    equal: bool
    base: str
    test: str


@dataclass
class DiffInt:
    equal: bool
    base: int
    test: int


@dataclass
class DiffTuple:
    equal: bool
    base: tuple
    test: tuple


@dataclass
class DiffList:
    equal: bool
    base: list
    test: list


@dataclass
class DiffDict:
    equal: bool
    base: dict
    test: dict


@dataclass
class DiffOptionalDict:
    equal: bool
    base: dict | None
    test: dict | None


@dataclass
class DiffBbox:
    equal: bool
    base: BoundingBox
    test: BoundingBox


@dataclass
class DiffCRS:
    equal: bool
    base: CRS
    test: CRS


@dataclass
class DiffTransform:
    equal: bool
    base: Affine
    test: Affine


@dataclass
class PixelDiffStats:
    diff_count: int
    total_count: int
    diff_percent: float
    max_diff: float
    rmse: float
    mask_diff_count: int = 0


@dataclass
class RasterDiff:
    checksum: DiffStr
    bands: DiffInt
    width: DiffInt
    height: DiffInt
    dtype: DiffStr
    nodata: DiffTuple
    bbox: DiffBbox
    crs: DiffCRS
    transform: DiffTransform
    gcps: DiffDict
    rpcs: DiffOptionalDict
    scales: DiffTuple
    offsets: DiffTuple
    units: DiffTuple
    colorinterp: DiffTuple
    descriptions: DiffTuple
    colormap: DiffList
    mask_flags: DiffList
    overviews: DiffList
    image_structure: DiffDict
    metadata: DiffDict
    bands_metadata: DiffList
    stats: DiffList
    pixel_values: list[PixelDiffStats] | None
