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
    nodata: float | None
    bbox: BoundingBox
    crs: CRS
    transform: Affine
    metadata: list[dict[str, Any]]
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
class DiffOptionalFloat:
    equal: bool
    base: float | None
    test: float | None


@dataclass
class DiffList:
    equal: bool
    base: list
    test: list


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
class RasterDiff:
    checksum: DiffStr
    bands: DiffInt
    width: DiffInt
    height: DiffInt
    dtype: DiffStr
    nodata: DiffOptionalFloat
    bbox: DiffBbox
    crs: DiffCRS
    transform: DiffTransform
    metadata: DiffList
    bands_metadata: DiffList
    stats: DiffList
    pixel_values: bool
