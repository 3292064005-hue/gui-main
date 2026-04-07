from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

_MIN_PYSIDE6 = (6, 7)
_MIN_PROTOBUF = (3, 20, 3)
_MAX_PROTOBUF_EXCLUSIVE = (8,)
_MIN_CMAKE = (3, 24)
_UBUNTU_BASELINE = (22, 4)


@dataclass(frozen=True)
class VersionCheck:
    ok: bool
    detail: str
    version: str = ""


def _normalize(parts: Iterable[int], length: int) -> tuple[int, ...]:
    seq = tuple(int(part) for part in parts)
    if len(seq) >= length:
        return seq[:length]
    return seq + (0,) * (length - len(seq))


def parse_numeric_version(raw: str | None) -> tuple[int, ...] | None:
    if not raw:
        return None
    tokens = re.findall(r"\d+", str(raw))
    if not tokens:
        return None
    return tuple(int(token) for token in tokens)


def version_in_range(raw: str | None, *, minimum: tuple[int, ...], maximum_exclusive: tuple[int, ...] | None = None) -> VersionCheck:
    version = parse_numeric_version(raw)
    if version is None:
        return VersionCheck(False, f"无法解析版本号: {raw or 'unknown'}", raw or "")
    min_cmp = _normalize(version, len(minimum)) >= minimum
    max_cmp = True
    if maximum_exclusive is not None:
        max_cmp = _normalize(version, len(maximum_exclusive)) < maximum_exclusive
    ok = min_cmp and max_cmp
    range_label = f">={'.'.join(map(str, minimum))}"
    if maximum_exclusive is not None:
        range_label += f", <{'.'.join(map(str, maximum_exclusive))}"
    detail = f"{raw} (要求 {range_label})"
    return VersionCheck(ok, detail, raw or "")


def check_pyside6_version(raw: str | None) -> VersionCheck:
    return version_in_range(raw, minimum=_MIN_PYSIDE6)


def check_protobuf_runtime_version(raw: str | None) -> VersionCheck:
    return version_in_range(raw, minimum=_MIN_PROTOBUF, maximum_exclusive=_MAX_PROTOBUF_EXCLUSIVE)


def check_cmake_version(raw: str | None) -> VersionCheck:
    return version_in_range(raw, minimum=_MIN_CMAKE)


def read_os_release(path: Path | str = "/etc/os-release") -> dict[str, str]:
    release_path = Path(path)
    data: dict[str, str] = {}
    if not release_path.exists():
        return data
    for line in release_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def check_ubuntu_2204(path: Path | str = "/etc/os-release") -> VersionCheck:
    info = read_os_release(path)
    distro_id = info.get("ID", "").lower()
    version_id = info.get("VERSION_ID", "")
    version = parse_numeric_version(version_id)
    if distro_id != "ubuntu" or version is None:
        pretty = info.get("PRETTY_NAME") or f"{distro_id or 'unknown'} {version_id or 'unknown'}"
        return VersionCheck(False, pretty)
    ok = _normalize(version, len(_UBUNTU_BASELINE)) == _UBUNTU_BASELINE
    pretty = info.get("PRETTY_NAME") or f"ubuntu {version_id}"
    return VersionCheck(ok, pretty, version_id)


__all__ = [
    "VersionCheck",
    "check_cmake_version",
    "check_protobuf_runtime_version",
    "check_pyside6_version",
    "check_ubuntu_2204",
    "parse_numeric_version",
    "read_os_release",
]
