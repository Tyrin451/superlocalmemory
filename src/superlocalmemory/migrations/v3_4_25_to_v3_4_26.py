# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Idempotent migration from v3.4.25 to v3.4.26 data layout.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _daemon_running() -> bool:
    """Return True if an SLM daemon is holding the data dir.

    Defined as a module-level indirection so tests can monkey-patch it
    without reaching into ``cli.daemon``.
    """
    from superlocalmemory.cli.daemon import is_daemon_running
    return bool(is_daemon_running())


def migrate_if_safe(data_dir: Path) -> dict[str, object]:
    """Run :func:`migrate` only when it's safe to touch the data dir.

    If a live daemon is detected (v3.4.25 still running during ``pip
    install -U``), the migration is deferred and the next daemon start
    will apply it. If the daemon probe fails we err on the safe side
    and also defer — we never crash the user's upgrade.

    Returns a dict with a ``status`` in ``{applied, already_applied,
    deferred}``.
    """
    data_dir = Path(data_dir)

    if is_ready(data_dir):
        return {"status": "already_applied", "data_dir": str(data_dir)}

    try:
        daemon_up = _daemon_running()
    except Exception as exc:
        # Probe failure — we default to "daemon is up" (safer: defers
        # the migration) but we must not hide it from operators.
        logger.warning(
            "daemon probe failed, deferring migrate_if_safe: %s", exc,
        )
        daemon_up = True

    if daemon_up:
        return {
            "status": "deferred",
            "data_dir": str(data_dir),
            "reason": "daemon is running — migration will apply on next daemon start",
        }

    result = migrate(data_dir)
    result["status"] = "applied"
    return result


def migrate(data_dir: Path) -> dict[str, object]:
    """Prepare v3.4.26 data directory. Safe to run any number of times.

    memory.db is untouched; the migration only provisions the new
    recall_queue.db and marks readiness with a sentinel file.
    """
    result: dict[str, object] = {
        "data_dir": str(data_dir),
        "created": [],
        "already_present": [],
    }
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    from superlocalmemory.core.recall_queue import RecallQueue

    queue_path = data_dir / "recall_queue.db"
    if queue_path.exists():
        result["already_present"].append(str(queue_path))
    else:
        result["created"].append(str(queue_path))
    q = RecallQueue(db_path=queue_path)
    q.close()

    marker = data_dir / ".slm-v3.4.26-ready"
    if marker.exists():
        result["already_present"].append(str(marker))
    else:
        marker.write_text("3.4.26\n", encoding="utf-8")
        result["created"].append(str(marker))
    return result


def is_ready(data_dir: Path) -> bool:
    return (Path(data_dir) / ".slm-v3.4.26-ready").exists()
