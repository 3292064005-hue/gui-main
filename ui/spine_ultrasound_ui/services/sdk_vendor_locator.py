from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SdkVendorLayout:
    source: str = "missing"
    sdk_root: Path | None = None
    include_dir: Path | None = None
    external_dir: Path | None = None
    lib_dir: Path | None = None
    static_lib: Path | None = None
    shared_lib: Path | None = None
    nomodel_shared_lib: Path | None = None
    xmate_model_lib: Path | None = None

    @property
    def found(self) -> bool:
        return bool(self.sdk_root and self.include_dir and self.external_dir and self.lib_dir and self.static_lib)

    @property
    def xmate_model_available(self) -> bool:
        return bool(self.xmate_model_lib and self.xmate_model_lib.exists())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "found": self.found,
            "sdk_root": str(self.sdk_root) if self.sdk_root else "",
            "include_dir": str(self.include_dir) if self.include_dir else "",
            "external_dir": str(self.external_dir) if self.external_dir else "",
            "lib_dir": str(self.lib_dir) if self.lib_dir else "",
            "static_lib": str(self.static_lib) if self.static_lib else "",
            "shared_lib": str(self.shared_lib) if self.shared_lib else "",
            "nomodel_shared_lib": str(self.nomodel_shared_lib) if self.nomodel_shared_lib else "",
            "xmate_model_lib": str(self.xmate_model_lib) if self.xmate_model_lib else "",
            "xmate_model_available": self.xmate_model_available,
        }


class SdkVendorLocator:
    """Locate the vendored or overridden xCore SDK layout.

    Resolution order is explicit-override first: environment variables win when
    set to a valid SDK root, and the vendored repository copy is the fallback.
    This keeps local/mainline defaults stable while allowing prod/HIL hosts to
    point at an externally mounted official SDK.
    """

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = Path(root_dir or Path(__file__).resolve().parents[2])

    def locate(self) -> SdkVendorLayout:
        candidates: list[tuple[str, Path]] = []
        for key in ("XCORE_SDK_ROOT", "ROKAE_SDK_ROOT"):
            value = os.environ.get(key, "").strip()
            if value:
                candidates.append((f"env:{key}", Path(value)))
        vendored = self.root_dir / "third_party" / "rokae_xcore_sdk" / "robot"
        candidates.append(("vendored", vendored))

        for source, sdk_root in candidates:
            layout = self._inspect(source, sdk_root)
            if layout.found:
                return layout
        return SdkVendorLayout()

    def _inspect(self, source: str, sdk_root: Path) -> SdkVendorLayout:
        include_dir = sdk_root / "include"
        external_dir = sdk_root / "external"
        lib_dir = sdk_root / "lib" / "Linux" / "cpp" / "x86_64"
        static_lib = lib_dir / "libxCoreSDK.a"
        shared_lib = lib_dir / "libxCoreSDK.so.0.3.4"
        nomodel_shared_lib = lib_dir / "NoModel" / "libxCoreSDK.so.0.3.4"
        xmate_model_lib = lib_dir / "libxMateModel.a"
        return SdkVendorLayout(
            source=source,
            sdk_root=sdk_root if sdk_root.exists() else None,
            include_dir=include_dir if include_dir.exists() else None,
            external_dir=external_dir if external_dir.exists() else None,
            lib_dir=lib_dir if lib_dir.exists() else None,
            static_lib=static_lib if static_lib.exists() else None,
            shared_lib=shared_lib if shared_lib.exists() else None,
            nomodel_shared_lib=nomodel_shared_lib if nomodel_shared_lib.exists() else None,
            xmate_model_lib=xmate_model_lib if xmate_model_lib.exists() else None,
        )
