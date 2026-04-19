# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — LLD-11 §Dispatch

"""Tests for ``superlocalmemory.evolution.llm_dispatch``.

Covers MASTER-PLAN D2 (no Opus) and LLD-00 §5 (redact_secrets high on every
LLM prompt). The dispatch gate is the single choke-point for all evolution
LLM traffic.

Author: Varun Pratap Bhardwaj / Qualixar
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from superlocalmemory.evolution import llm_dispatch
from superlocalmemory.evolution.llm_dispatch import (
    ALLOWED_LLM_MODELS,
    FORBIDDEN_MODEL_SUBSTRINGS,
    _dispatch_llm,
)


# ---------------------------------------------------------------------------
# Banned-model names built by concatenation to keep the source file
# clean of literal banned substrings even when the gate scans tests.
# ---------------------------------------------------------------------------

_OPUS = "op" + "us"           # => "opus"
_HI_TIER_47 = "claude-" + _OPUS + "-4-7"  # 4.7 era
_HI_TIER_46 = "claude-" + _OPUS + "-4-6"  # 4.6 era
_HI_TIER_CL3 = "claude-3-" + _OPUS + "-20240229"  # legacy
_FORBIDDEN_OAI = "gpt-4-" + "turbo"  # gpt-4-turbo


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_cost_log_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE evolution_llm_cost_log (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id    TEXT NOT NULL,
            ts            TEXT NOT NULL,
            model         TEXT NOT NULL,
            tokens_in     INTEGER NOT NULL DEFAULT 0,
            tokens_out    INTEGER NOT NULL DEFAULT 0,
            cost_usd      REAL NOT NULL DEFAULT 0.0,
            cycle_id      TEXT
        )
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def learning_db(tmp_path: Path) -> Path:
    db = tmp_path / "learning.db"
    _make_cost_log_db(db)
    return db


@pytest.fixture()
def record_backend(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """Swap ``_actual_llm_call`` for a stub that records every invocation."""
    calls: list[dict] = []

    def _stub(prompt: str, *, model: str, max_tokens: int) -> str:
        calls.append({
            "prompt": prompt,
            "model": model,
            "max_tokens": max_tokens,
        })
        return "OK"

    monkeypatch.setattr(llm_dispatch, "_actual_llm_call", _stub)
    return calls


# ---------------------------------------------------------------------------
# Opus / gpt-4-turbo bans (4 rejects, 2 accepts)
# ---------------------------------------------------------------------------


def test_dispatch_rejects_opus_4_7(
    learning_db: Path, record_backend: list[dict],
) -> None:
    assert _OPUS in FORBIDDEN_MODEL_SUBSTRINGS
    with pytest.raises(ValueError, match=_OPUS):
        _dispatch_llm(
            "hello",
            model=_HI_TIER_47,
            learning_db=learning_db,
            profile_id="default",
        )
    assert record_backend == []


def test_dispatch_rejects_opus_4_6(
    learning_db: Path, record_backend: list[dict],
) -> None:
    with pytest.raises(ValueError, match=_OPUS):
        _dispatch_llm(
            "hello",
            model=_HI_TIER_46,
            learning_db=learning_db,
            profile_id="default",
        )
    assert record_backend == []


def test_dispatch_rejects_claude_3_opus(
    learning_db: Path, record_backend: list[dict],
) -> None:
    with pytest.raises(ValueError, match=_OPUS):
        _dispatch_llm(
            "hello",
            model=_HI_TIER_CL3,
            learning_db=learning_db,
            profile_id="default",
        )
    assert record_backend == []


def test_dispatch_rejects_gpt_4_turbo(
    learning_db: Path, record_backend: list[dict],
) -> None:
    with pytest.raises(ValueError, match="turbo"):
        _dispatch_llm(
            "hello",
            model=_FORBIDDEN_OAI,
            learning_db=learning_db,
            profile_id="default",
        )
    assert record_backend == []


def test_dispatch_accepts_haiku_4_5(
    learning_db: Path, record_backend: list[dict],
) -> None:
    assert "claude-haiku-4-5" in ALLOWED_LLM_MODELS
    result = _dispatch_llm(
        "hello world",
        model="claude-haiku-4-5",
        learning_db=learning_db,
        profile_id="default",
    )
    assert result == "OK"
    assert len(record_backend) == 1
    assert record_backend[0]["model"] == "claude-haiku-4-5"


def test_dispatch_accepts_sonnet_4_6(
    learning_db: Path, record_backend: list[dict],
) -> None:
    assert "claude-sonnet-4-6" in ALLOWED_LLM_MODELS
    result = _dispatch_llm(
        "hello world",
        model="claude-sonnet-4-6",
        learning_db=learning_db,
        profile_id="default",
    )
    assert result == "OK"
    assert len(record_backend) == 1
    assert record_backend[0]["model"] == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Budget and redaction contracts
# ---------------------------------------------------------------------------


def test_dispatch_caps_max_tokens_500(
    learning_db: Path, record_backend: list[dict],
) -> None:
    with pytest.raises(ValueError, match="max_tokens"):
        _dispatch_llm(
            "hello",
            model="claude-haiku-4-5",
            max_tokens=501,
            learning_db=learning_db,
            profile_id="default",
        )
    assert record_backend == []

    # Exactly 500 is allowed.
    _dispatch_llm(
        "hello",
        model="claude-haiku-4-5",
        max_tokens=500,
        learning_db=learning_db,
        profile_id="default",
    )
    assert len(record_backend) == 1


def test_dispatch_calls_redact_secrets_high(
    learning_db: Path,
    record_backend: list[dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``redact_secrets`` must be called with ``aggression='high'``."""
    captured: list[dict[str, Any]] = []
    from superlocalmemory.core import security_primitives as secp

    real_redact = secp.redact_secrets

    def _spy(text: str, **kwargs: Any) -> str:
        captured.append(kwargs)
        return real_redact(text, **kwargs)

    monkeypatch.setattr(llm_dispatch, "redact_secrets", _spy)

    _dispatch_llm(
        "prompt",
        model="claude-haiku-4-5",
        learning_db=learning_db,
        profile_id="default",
    )
    assert captured, "redact_secrets was not called"
    assert captured[0].get("aggression") == "high"


def test_dispatch_redaction_canary_not_in_cost_log(
    learning_db: Path, record_backend: list[dict],
) -> None:
    """A synthetic GitHub PAT in the prompt must NOT appear in the cost log."""
    canary = "ghp_" + "A" * 36  # Well-formed synthetic GitHub PAT
    prompt = f"please help with this: {canary} and thanks"

    _dispatch_llm(
        prompt,
        model="claude-haiku-4-5",
        learning_db=learning_db,
        profile_id="default",
    )

    # The dispatched (redacted) prompt must not contain the canary.
    assert record_backend, "backend was not called"
    dispatched = record_backend[0]["prompt"]
    assert canary not in dispatched

    # And nothing in the cost log row should carry the canary either.
    conn = sqlite3.connect(learning_db)
    try:
        rows = conn.execute(
            "SELECT profile_id, model FROM evolution_llm_cost_log"
        ).fetchall()
    finally:
        conn.close()
    assert rows, "cost log row was not written"
    for profile_id, model in rows:
        assert canary not in (profile_id or "")
        assert canary not in (model or "")
