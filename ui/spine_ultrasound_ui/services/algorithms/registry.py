from __future__ import annotations

from typing import Dict, Iterable

from .plugin_plane import AlgorithmPlugin


class PluginRegistry:
    def __init__(self, plugins: Iterable[AlgorithmPlugin] = ()):  # noqa: B008
        self._plugins: Dict[str, AlgorithmPlugin] = {}
        for plugin in plugins:
            self.register(plugin)

    def register(self, plugin: AlgorithmPlugin) -> None:
        self._plugins[plugin.stage] = plugin

    def get(self, stage: str) -> AlgorithmPlugin:
        return self._plugins[stage]

    def all(self) -> list[AlgorithmPlugin]:
        return list(self._plugins.values())
