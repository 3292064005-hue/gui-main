from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from spine_ultrasound_ui.utils import now_ns


@dataclass
class ForceSample:
    ts_ns: int
    wrench_n: list[float]
    status: str
    source: str


class ForceSensorProvider(ABC):
    provider_id: str = "force_sensor_provider"

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    @abstractmethod
    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        raise NotImplementedError


class MockForceSensorProvider(ForceSensorProvider):
    provider_id = "mock_force_sensor"

    def __init__(self) -> None:
        self._phase = 0.0

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        self._phase += 0.13
        if not contact_active:
            z_force = 0.0
        else:
            z_force = desired_force_n + 0.25 * math.sin(self._phase) + 0.05 * math.cos(self._phase * 0.5)
        return ForceSample(
            ts_ns=now_ns(),
            wrench_n=[0.03, 0.02, round(z_force, 3), 0.0, 0.0, 0.0],
            status="ok",
            source=self.provider_id,
        )


class UnavailableForceSensorProvider(ForceSensorProvider):
    provider_id = "unavailable_force_sensor"

    def read_sample(self, *, contact_active: bool, desired_force_n: float) -> ForceSample:
        del contact_active, desired_force_n
        return ForceSample(
            ts_ns=0,
            wrench_n=[0.0] * 6,
            status="unavailable",
            source=self.provider_id,
        )


def create_force_sensor_provider(provider_id: str) -> ForceSensorProvider:
    if provider_id == MockForceSensorProvider.provider_id:
        return MockForceSensorProvider()
    if provider_id == UnavailableForceSensorProvider.provider_id:
        return UnavailableForceSensorProvider()
    return UnavailableForceSensorProvider()
