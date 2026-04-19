# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — LLD-11 §Firing

"""Tests for opt-in firing of ``SkillEvolver.run_post_session`` + Stop hook.

Covers MASTER-PLAN D3: evolution is OFF by default, so the Stop hook is a
no-op on fresh installs. Only after ``evolution.enabled=True`` is set does
the Stop hook trigger ``run_post_session``.

Author: Varun Pratap Bhardwaj / Qualixar
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from superlocalmemory.core.config import EvolutionConfig, SLMConfig
from superlocalmemory.evolution.skill_evolver import SkillEvolver


# ---------------------------------------------------------------------------
# test_evolution_disabled_by_default
# ---------------------------------------------------------------------------


def test_evolution_disabled_by_default() -> None:
    """A fresh ``SLMConfig`` must have ``evolution.enabled=False``."""
    config = SLMConfig.default()
    assert isinstance(config.evolution, EvolutionConfig)
    assert config.evolution.enabled is False

    # And ``run_post_session`` must short-circuit when config.enabled is False.
    evolver = SkillEvolver(db_path=":memory:", config=config)
    result = evolver.run_post_session(session_id="s1", profile_id="default")
    assert result.get("enabled") is False


# ---------------------------------------------------------------------------
# Stop-hook integration
# ---------------------------------------------------------------------------


@pytest.fixture()
def stop_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Configure the Stop hook to run in an isolated tempdir.

    Swaps ``_daemon_post`` so no real daemon call happens, and sets
    CLAUDE_PROJECT_DIR + CLAUDE_SESSION_ID so the hook has identifiers.
    """
    from superlocalmemory.hooks import hook_handlers as hh

    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-test-abc")

    # Isolate tmp markers so Stop doesn't touch real /tmp entries.
    tmp_area = tmp_path / "tmp"
    tmp_area.mkdir()
    monkeypatch.setattr(hh, "_TMP", str(tmp_area))
    monkeypatch.setattr(
        hh, "_MARKER", str(tmp_area / "slm-session-initialized"),
    )
    monkeypatch.setattr(
        hh, "_START_TIME", str(tmp_area / "slm-session-start-time"),
    )
    monkeypatch.setattr(
        hh, "_ACTIVITY_LOG", str(tmp_area / "slm-session-activity"),
    )
    monkeypatch.setattr(
        hh, "_LAST_CONSOLIDATION", str(tmp_area / ".last-consolidation"),
    )

    # Stub daemon_post — returns success, records calls.
    daemon_calls: list[tuple[str, dict]] = []

    def _fake_daemon_post(
        path: str, body: dict, timeout: float = 3.0,
    ) -> bool:
        daemon_calls.append((path, body))
        return True

    monkeypatch.setattr(hh, "_daemon_post", _fake_daemon_post)

    # Record SkillEvolver.run_post_session calls.
    evolver_calls: list[dict[str, Any]] = []

    def _record(**kwargs: Any) -> dict[str, Any]:
        evolver_calls.append(kwargs)
        return {"enabled": True, "candidates": 0, "evolved": 0, "rejected": 0}

    # Patch the module-level launcher we will introduce.
    monkeypatch.setattr(
        hh, "_launch_post_session_evolution", _record, raising=False,
    )

    return {
        "tmp_path": tmp_path,
        "daemon_calls": daemon_calls,
        "evolver_calls": evolver_calls,
        "hh": hh,
    }


def test_stop_hook_calls_run_post_session_when_enabled(
    stop_env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``evolution.enabled=True``, Stop hook must trigger evolution."""
    hh = stop_env["hh"]

    # Signal enabled state via env var — the hook reads it at call time
    # so we don't need to touch config files.
    monkeypatch.setenv("SLM_EVOLUTION_ENABLED", "1")

    # Invoke the Stop handler. It calls sys.exit(0); catch it.
    with pytest.raises(SystemExit) as exc:
        hh._hook_stop()
    assert exc.value.code == 0

    assert len(stop_env["evolver_calls"]) == 1
    call = stop_env["evolver_calls"][0]
    assert call.get("session_id") == "sess-test-abc"


def test_stop_hook_noop_when_disabled(
    stop_env: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``evolution.enabled`` is false/unset, Stop hook is a no-op."""
    hh = stop_env["hh"]
    monkeypatch.delenv("SLM_EVOLUTION_ENABLED", raising=False)

    with pytest.raises(SystemExit) as exc:
        hh._hook_stop()
    assert exc.value.code == 0

    assert stop_env["evolver_calls"] == []
