import json
from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig


class ConfigService:
    def save(self, path: Path, config: RuntimeConfig) -> None:
        path.write_text(json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def load(self, path: Path) -> RuntimeConfig:
        return RuntimeConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
