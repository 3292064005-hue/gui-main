from pathlib import Path
from .time_utils import now_text


def append_log(file_path: Path, level: str, message: str):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as f:
        f.write(f"[{now_text()}] [{level}] {message}\n")
