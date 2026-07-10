"""Вывод отчёта сравнения растров в консоль в стиле pytest-diff.

Показываются только различия. Каждое поле выводится единым способом — как
pytest показывает `assert base == test`: unified-diff по ``pprint``-представлению,
где строки ``-`` относятся к base (красный), ``+`` — к test (зелёный), а
неизменившиеся строки служат контекстом.
"""

import difflib
import pprint

import click
from affine import Affine

from rio_diff import models

_STAT_ATTRS = ("min", "max", "mean", "std")
_TRANSFORM_ATTRS = (
    ("a", "pixel width"),
    ("b", "row rotation"),
    ("c", "upper-left x"),
    ("d", "column rotation"),
    ("e", "pixel height"),
    ("f", "upper-left y"),
)
_CONTEXT_LINES = 2


def _has_attrs(value, attrs) -> bool:
    return all(hasattr(value, attr) for attr in attrs)


def _prepare(value):
    """Разложить объекты по полям, чтобы ``pprint`` печатал их построчно.

    Statistics/BBox/Transform и подобные объекты в repr-е выглядят одной
    строкой, поэтому diff краснит их целиком. Превращаем их в dict по полям
    (рекурсивно), тогда каждое поле оказывается на своей строке и в diff-е
    подсвечивается только изменившееся. Ключи внешних dict сортируем, чтобы
    base и test были выровнены.
    """
    if isinstance(value, dict):
        return {key: _prepare(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, Affine):
        return {f"{name.upper()} ({desc})": getattr(value, name) for name, desc in _TRANSFORM_ATTRS}
    if _has_attrs(value, _STAT_ATTRS):
        return {name: getattr(value, name) for name in _STAT_ATTRS}
    if hasattr(value, "_fields"):  # namedtuple, напр. BoundingBox
        return {name: _prepare(getattr(value, name)) for name in value._fields}
    if isinstance(value, (list, tuple)):
        return [_prepare(item) for item in value]
    return value


def _lines(value) -> list[str]:
    """Разбить значение на строки для diff-а.

    Контейнеры раскладываем через ``pprint`` с узкой шириной, чтобы элементы
    ложились по одному на строку. Скаляры берём через ``str`` — так у объектов
    с коротким представлением (например, CRS → ``EPSG:32637``) не всплывает
    громоздкий repr.
    """
    prepared = _prepare(value)
    if isinstance(prepared, (dict, list, tuple)):
        text = pprint.pformat(prepared, width=1, sort_dicts=False)
    else:
        text = str(prepared)
    return text.splitlines() or [text]


def _print_value_diff(base, test) -> None:
    lines = [
        line
        for line in difflib.ndiff(_lines(base), _lines(test))
        if line[:2] != "? "  # подсказки ndiff с ^~+ — пропускаем как шум
    ]

    keep = [False] * len(lines)
    for i, line in enumerate(lines):
        if line[:2] in ("- ", "+ "):
            lo = max(0, i - _CONTEXT_LINES)
            hi = min(len(lines), i + _CONTEXT_LINES + 1)
            keep[lo:hi] = [True] * (hi - lo)

    skipping = False
    for line, kept in zip(lines, keep):
        if not kept:
            if not skipping:
                click.secho("  ...", dim=True)
                skipping = True
            continue
        skipping = False
        tag = line[:2]
        if tag == "- ":
            click.secho(f"  {line}", fg="red")
        elif tag == "+ ":
            click.secho(f"  {line}", fg="green")
        else:  # "  " — общий контекст
            click.echo(f"  {line}")


def _print_mismatch(label: str, base, test) -> None:
    click.secho(label, bold=True)
    _print_value_diff(base, test)


def print_report(
    checks: list[tuple[str, bool, object, object]],
    pixel_values: list[models.PixelDiffStats] | None,
    show_pixel_values: bool,
) -> bool:
    """Вывести различия. Возвращает True, если найдено хотя бы одно."""
    printed = 0

    def separate() -> None:
        nonlocal printed
        if printed:
            click.echo()
        printed += 1

    for label, equal, base, test in checks:
        if not equal:
            separate()
            _print_mismatch(label, base, test)

    if show_pixel_values:
        if pixel_values is None:
            separate()
            click.secho(
                "Pixel values not compared (incompatible shape or band count)",
                fg="yellow",
            )
        else:
            diffs = [
                (bidx, stat)
                for bidx, stat in enumerate(pixel_values, start=1)
                if stat.diff_count > 0 or stat.mask_diff_count > 0
            ]
            if diffs:
                separate()
                click.secho("Pixel values", bold=True)
                rows = [
                    {
                        "band": bidx,
                        "diff_count": stat.diff_count,
                        "diff_percent": round(stat.diff_percent, 2),
                        "max_diff": stat.max_diff,
                        "rmse": stat.rmse,
                        "mask_diff_count": stat.mask_diff_count,
                    }
                    for bidx, stat in diffs
                ]
                for line in _lines(rows):
                    click.secho(f"  {line}", fg="red")

    return printed > 0
