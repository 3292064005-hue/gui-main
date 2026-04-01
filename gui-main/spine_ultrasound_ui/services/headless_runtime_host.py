from __future__ import annotations

from typing import Any


class HeadlessRuntimeHost:
    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    def status(self) -> dict[str, Any]: return self._adapter.runtime_introspection.status()
    def health(self) -> dict[str, Any]: return self._adapter.runtime_introspection.health()
    def schema(self) -> dict[str, Any]: return self._adapter.runtime_introspection.schema()
    def topic_catalog(self) -> dict[str, Any]: return self._adapter.runtime_introspection.topic_catalog()
    def role_catalog(self) -> dict[str, Any]: return self._adapter.runtime_introspection.role_catalog()
    def command_policy_catalog(self) -> dict[str, Any]: return self._adapter.runtime_introspection.command_policy_catalog()
    def control_authority_status(self) -> dict[str, Any]: return self._adapter.runtime_introspection.control_authority_status()
    def recent_commands(self) -> dict[str, Any]: return self._adapter.command_service.recent_commands()
    def command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]: return self._adapter.command_service.command(command, payload)
    def snapshot(self) -> dict[str, Any]: return self._adapter.surface.snapshot()
    def control_plane_status(self) -> dict[str, Any]: return self._adapter.surface.control_plane_status()
