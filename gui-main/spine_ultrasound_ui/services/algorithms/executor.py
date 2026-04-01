from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import ProcessingStepRecord

from .cache import PluginCache
from .plugin_plane import AlgorithmPlugin


class PluginExecutor:
    def __init__(self, cache: PluginCache | None = None):
        self.cache = cache or PluginCache()

    def run(self, plugin: AlgorithmPlugin, session_dir: Path, inputs: dict[str, Any]) -> ProcessingStepRecord:
        plugin.validate_inputs(inputs)
        cache_key = plugin.cache_key(session_dir, inputs)
        cached = self.cache.load(session_dir, plugin.stage, cache_key)
        if cached is not None:
            return ProcessingStepRecord(**cached)
        step = plugin.run(session_dir, inputs)
        self.cache.save(session_dir, plugin.stage, cache_key, step.to_dict())
        return step
