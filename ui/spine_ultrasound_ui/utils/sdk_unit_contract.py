from __future__ import annotations

from typing import Any, Sequence

from .runtime_fingerprint import payload_hash

_TRANSLATION_INDICES = (3, 7, 11)


def mm_to_m(value_mm: float) -> float:
    return float(value_mm) / 1000.0


def m_to_mm(value_m: float) -> float:
    return float(value_m) * 1000.0


def _looks_like_mm_translation(value: float) -> bool:
    return abs(float(value)) > 2.0


def normalize_frame_matrix_ui_mm_to_sdk_m(matrix: Sequence[float] | None) -> list[float]:
    values = [float(item) for item in (matrix or [])[:16]]
    if len(values) < 16:
        values.extend([0.0] * (16 - len(values)))
        values[0] = values[5] = values[10] = values[15] = 1.0
    normalized = list(values)
    for idx in _TRANSLATION_INDICES:
        if _looks_like_mm_translation(normalized[idx]):
            normalized[idx] = mm_to_m(normalized[idx])
    return normalized


def normalize_vector_mm_to_m(values: Sequence[float] | None, expected_length: int) -> list[float]:
    payload = [mm_to_m(float(item)) for item in (values or [])[:expected_length]]
    if len(payload) < expected_length:
        payload.extend([0.0] * (expected_length - len(payload)))
    return payload


def extract_frame_translation_mm(matrix: Sequence[float] | None) -> list[float]:
    values = [float(item) for item in (matrix or [])[:16]]
    if len(values) < 16:
        values.extend([0.0] * (16 - len(values)))
    out: list[float] = []
    for idx in _TRANSLATION_INDICES:
        value = values[idx]
        out.append(float(value) if _looks_like_mm_translation(value) else m_to_mm(value))
    return out


def build_sdk_boundary_contract(*, fc_frame_matrix: Sequence[float], tcp_frame_matrix: Sequence[float], load_com_mm: Sequence[float]) -> dict[str, Any]:
    fc_matrix_m = normalize_frame_matrix_ui_mm_to_sdk_m(fc_frame_matrix)
    tcp_matrix_m = normalize_frame_matrix_ui_mm_to_sdk_m(tcp_frame_matrix)
    load_com_m = normalize_vector_mm_to_m(load_com_mm, 3)
    contract = {
        "ui_length_unit": "mm",
        "sdk_length_unit": "m",
        "ui_angle_unit": "rad",
        "sdk_angle_unit": "rad",
        "translation_indices_row_major": list(_TRANSLATION_INDICES),
        "normalization_policy": "ui_mm_to_sdk_m_at_boundary_only",
        "fc_frame_matrix_m": fc_matrix_m,
        "tcp_frame_matrix_m": tcp_matrix_m,
        "load_com_m": load_com_m,
        "tcp_translation_mm": extract_frame_translation_mm(tcp_frame_matrix),
    }
    contract["contract_hash"] = payload_hash(contract)
    return contract


def with_sdk_boundary_fields(payload: dict[str, Any], *, fc_frame_matrix: Sequence[float], tcp_frame_matrix: Sequence[float], load_com_mm: Sequence[float]) -> dict[str, Any]:
    contract = build_sdk_boundary_contract(
        fc_frame_matrix=fc_frame_matrix,
        tcp_frame_matrix=tcp_frame_matrix,
        load_com_mm=load_com_mm,
    )
    enriched = dict(payload)
    enriched["sdk_boundary_units"] = contract
    enriched.setdefault("fc_frame_matrix_m", list(contract["fc_frame_matrix_m"]))
    enriched.setdefault("tcp_frame_matrix_m", list(contract["tcp_frame_matrix_m"]))
    enriched.setdefault("load_com_m", list(contract["load_com_m"]))
    return enriched
