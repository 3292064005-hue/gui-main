from pathlib import Path


class ReplayService:
    def list_experiments(self, root: Path) -> list[Path]:
        return sorted([p for p in root.iterdir() if p.is_dir()]) if root.exists() else []
