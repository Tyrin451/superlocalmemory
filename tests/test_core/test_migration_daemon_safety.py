"""Migration v3.4.25 -> v3.4.26 must not race a live v3.4.25 daemon.

Contract:
- ``migrate_if_safe(data_dir)`` checks whether an SLM daemon is running.
  If yes, the migration is deferred — on-disk state is not touched and
  the status flag says so.
- If no daemon is running, the migration applies as usual.
- The daemon's own ``start_server`` runs the migration unconditionally
  (it IS the process holding the DB once it's up).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from superlocalmemory.migrations.v3_4_25_to_v3_4_26 import (
    is_ready,
    migrate,
    migrate_if_safe,
)


class TestMigrateIfSafe:
    def test_applies_when_no_daemon(self, tmp_path, monkeypatch):
        # Patch the daemon probe to False — "nobody is holding the DB".
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            lambda: False,
        )
        result = migrate_if_safe(tmp_path)
        assert result["status"] == "applied"
        assert is_ready(tmp_path)

    def test_defers_when_daemon_running(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            lambda: True,
        )
        result = migrate_if_safe(tmp_path)
        assert result["status"] == "deferred"
        # Nothing on disk yet — the marker is the gate.
        assert not is_ready(tmp_path)

    def test_deferred_then_applied_on_daemon_stop(self, tmp_path, monkeypatch):
        # First call: daemon up, deferred.
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            lambda: True,
        )
        assert migrate_if_safe(tmp_path)["status"] == "deferred"

        # Daemon stops; second call applies it.
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            lambda: False,
        )
        assert migrate_if_safe(tmp_path)["status"] == "applied"
        assert is_ready(tmp_path)

    def test_second_apply_is_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            lambda: False,
        )
        first = migrate_if_safe(tmp_path)
        second = migrate_if_safe(tmp_path)
        assert first["status"] == "applied"
        assert second["status"] == "already_applied"
        assert is_ready(tmp_path)

    def test_never_raises_on_daemon_probe_failure(self, tmp_path, monkeypatch):
        def _boom():
            raise RuntimeError("psutil exploded")
        monkeypatch.setattr(
            "superlocalmemory.migrations.v3_4_25_to_v3_4_26._daemon_running",
            _boom,
        )
        # On an indeterminate probe we must err on the safe side and
        # defer, not crash the user's upgrade.
        result = migrate_if_safe(tmp_path)
        assert result["status"] == "deferred"
