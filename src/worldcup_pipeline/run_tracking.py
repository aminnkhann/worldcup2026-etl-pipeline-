"""File-based ETL run tracking."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class RunTracker:
    mode: str
    log_path: Path = PROJECT_ROOT / "logs" / "pipeline-runs.jsonl"
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def finish(self, status: str, counts: dict[str, int] | None = None, error: str | None = None) -> None:
        ended_at = datetime.now(UTC)
        record: dict[str, Any] = {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": status,
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_seconds": round((ended_at - self.started_at).total_seconds(), 3),
            "counts": counts or {},
        }
        if error:
            record["error"] = error

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        except OSError as exc:
            logger.warning("Could not write run tracking record: %s", exc)
