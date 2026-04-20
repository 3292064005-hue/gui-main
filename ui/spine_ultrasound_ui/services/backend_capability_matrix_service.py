from __future__ import annotations

from typing import Any


class BackendCapabilityMatrixService:
    """Build explicit UI capability contracts."""

    @staticmethod
    def build(entries: dict[str, str]) -> dict[str, dict[str, Any]]:
        matrix: dict[str, dict[str, Any]] = {}
        for name, mode in entries.items():
            normalized = str(mode or "hidden").strip().lower()
            if normalized not in {"executable", "monitor_only", "hidden"}:
                normalized = "hidden"
            matrix[name] = {
                "mode": normalized,
                "executable": normalized == "executable",
                "monitor_only": normalized == "monitor_only",
                "visible": normalized != "hidden",
            }
        return matrix

    @staticmethod
    def to_media_capabilities(matrix: dict[str, dict[str, Any]]) -> dict[str, bool]:
        """Return the legacy boolean capability surface.

        Historical callers interpret these booleans as "does this backend expose
        a usable stream/surface for the feature" rather than raw UI visibility.
        For media streams, monitor-only remains a usable capability; for
        write-centric surfaces such as recording, only executable mode counts as
        enabled.
        """
        out: dict[str, bool] = {}
        for name, item in matrix.items():
            mode = str(item.get("mode", "hidden"))
            if name in {"camera", "ultrasound", "reconstruction"}:
                out[name] = mode in {"executable", "monitor_only"}
            else:
                out[name] = mode == "executable"
        return out


    @staticmethod
    def page_contract(matrix: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        def mode_for(*names: str) -> str:
            modes = [str(dict(matrix.get(name, {})).get("mode", "hidden")) for name in names]
            if any(mode == "executable" for mode in modes):
                return "executable"
            if any(mode == "monitor_only" for mode in modes):
                return "monitor_only"
            return "hidden"

        def entry(mode: str) -> dict[str, Any]:
            return {
                "mode": mode,
                "visible": mode != "hidden",
                "monitor_only": mode == "monitor_only",
                "executable": mode == "executable",
            }

        return {
            "vision": entry(mode_for("camera")),
            "reconstruction": entry(mode_for("ultrasound", "reconstruction")),
            "replay": entry(mode_for("recording", "reconstruction")),
        }
