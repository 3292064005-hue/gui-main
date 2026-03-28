from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from spine_ultrasound_ui.utils import ensure_dir, now_ns


class JsonlRecorder:
    def __init__(self, path: Path, session_id: str):
        self.path = path
        self.session_id = session_id
        self.seq = 0
        ensure_dir(path.parent)

    def append(self, payload: Dict[str, Any], source_ts_ns: Optional[int] = None) -> None:
        self.seq += 1
        envelope = {
            "monotonic_ns": now_ns(),
            "source_ts_ns": source_ts_ns or 0,
            "seq": self.seq,
            "session_id": self.session_id,
            "data": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope, ensure_ascii=False) + "\n")

    def append_event(self, payload: Dict[str, Any]) -> None:
        self.append(payload, source_ts_ns=int(payload.get("ts_ns", 0) or 0))


class FrameRecorder:
    def __init__(self, frame_root: Path, index_path: Path, session_id: str):
        self.frame_root = ensure_dir(frame_root)
        self.index = JsonlRecorder(index_path, session_id)

    def append_pixmap(self, pixmap: Any, prefix: str, source_ts_ns: Optional[int] = None) -> Optional[Path]:
        if pixmap is None or getattr(pixmap, "isNull", lambda: True)():
            return None
        frame_name = f"{prefix}_{self.index.seq + 1:06d}.png"
        target = self.frame_root / frame_name
        if not pixmap.save(str(target)):
            return None
        self.index.append({"frame_path": str(target), "kind": prefix}, source_ts_ns=source_ts_ns)
        return target
