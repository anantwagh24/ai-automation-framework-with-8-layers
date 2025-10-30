from __future__ import annotations
from pathlib import Path
import json
from datetime import datetime

def timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")

def write_json(path: str | Path, payload) -> None:
    p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")

