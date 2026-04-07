from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Callable

from spine_ultrasound_ui.utils import now_ns


@dataclass(frozen=True)
class ForceSample:
    ts_ns: int
    wrench_n: list[float]
    status: str
    source: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ForceSensorProvider(ABC):
    provider_id: str = "force_sensor_provider"

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    @abstractmethod
    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        ...


class MockForceSensorProvider(ForceSensorProvider):
    provider_id = "mock_force_sensor"

    def __init__(self) -> None:
        self._phase = 0.0

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        self._phase += 0.13
        base_force = desired_force_n if contact_active else 0.0
        ripple = 0.25 * math.sin(self._phase) + 0.05 * math.cos(self._phase * 0.5)
        z_force = round(base_force + (ripple if contact_active else 0.0), 3)
        return ForceSample(
            ts_ns=now_ns(),
            wrench_n=[0.03, 0.02, z_force, 0.0, 0.0, 0.0],
            status="ok",
            source=self.provider_id,
        )


class UnavailableForceSensorProvider(ForceSensorProvider):
    provider_id = "unavailable_force_sensor"

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        del contact_active, desired_force_n
        return ForceSample(
            ts_ns=now_ns(),
            wrench_n=[0.0] * 6,
            status="unavailable",
            source=self.provider_id,
        )


_PROVIDER_FACTORIES: dict[str, Callable[[], ForceSensorProvider]] = {
    MockForceSensorProvider.provider_id: MockForceSensorProvider,
    UnavailableForceSensorProvider.provider_id: UnavailableForceSensorProvider,
}


def register_force_sensor_provider_factory(provider_id: str, factory: Callable[[], ForceSensorProvider]) -> None:
    provider_id = str(provider_id).strip()
    if not provider_id:
        raise ValueError("provider_id must not be empty")
    _PROVIDER_FACTORIES[provider_id] = factory


def available_force_sensor_providers() -> list[str]:
    return sorted(_PROVIDER_FACTORIES)


def create_force_sensor_provider(provider_id: str) -> ForceSensorProvider:
    factory = _PROVIDER_FACTORIES.get(provider_id, UnavailableForceSensorProvider)
    provider = factory()
    if not isinstance(provider, ForceSensorProvider):
        raise TypeError(f"factory for {provider_id!r} returned {type(provider).__name__}, expected ForceSensorProvider")
    return provider
