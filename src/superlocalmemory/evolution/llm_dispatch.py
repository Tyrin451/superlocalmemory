# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory v3.4.21 — LLD-11 §Dispatch

"""Central LLM dispatch for the skill-evolution subsystem.

Enforces MASTER-PLAN D2 (no top-tier "O-family" Claude models, no
``gpt-4-turbo``) and LLD-00 §5 (every LLM-bound prompt passes through
``redact_secrets(aggression='high')`` FIRST).

Every evolution LLM call funnels through :func:`_dispatch_llm`. Writes an
audit row to ``evolution_llm_cost_log`` after the dispatch succeeds — the
row stores only the *redacted* prompt length and the model, never the
raw prompt, so no canary can leak via the cost log.

Author: Varun Pratap Bhardwaj / Qualixar
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from superlocalmemory.core.security_primitives import redact_secrets

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Allow-list and deny-list
# ---------------------------------------------------------------------------
#
# Allow-list explicitly names every model evolution may invoke. Deny-list
# catches substrings that must NEVER appear in an evolution-issued model
# id — notably the O-tier Claude family (MASTER-PLAN D2) and OpenAI's
# ``gpt-4-turbo`` (cost + behaviour regressions observed in prod).
#
# NOTE on the deny-list strings: the Stage-5b CI gate scans ``src/`` for
# the full banned model-family literal. That literal must NEVER appear in
# this file or any other source file. We check for the shorter substring
# ``opus`` instead; that catches every Claude O-family id variant without
# putting the banned literal anywhere in source.

ALLOWED_LLM_MODELS: frozenset[str] = frozenset({
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "ollama:llama3",
    "ollama:qwen2.5",
})

FORBIDDEN_MODEL_SUBSTRINGS: tuple[str, ...] = ("opus", "gpt-4-turbo")

MAX_TOKENS_CAP: int = 500


# ---------------------------------------------------------------------------
# Real backend (overridable in tests)
# ---------------------------------------------------------------------------


def _actual_llm_call(prompt: str, *, model: str, max_tokens: int) -> str:
    """Invoke the concrete backend for ``model`` and return the response.

    The production wiring lives in ``skill_evolver._call_claude_cli`` /
    ``_call_ollama`` / ``_call_api``. This stub exists so tests can swap
    a deterministic backend via ``monkeypatch.setattr``. At runtime,
    SkillEvolver injects the real backend before calling ``_dispatch_llm``.
    """
    raise NotImplementedError(
        "evolution._actual_llm_call not wired. SkillEvolver must inject "
        "a concrete backend before dispatching."
    )


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


def _validate_model(model: str) -> None:
    """Raise ``ValueError`` if the model is forbidden or not allow-listed."""
    if not isinstance(model, str) or not model:
        raise ValueError(f"model must be a non-empty str, got {model!r}")
    lowered = model.lower()
    for forbidden in FORBIDDEN_MODEL_SUBSTRINGS:
        if forbidden in lowered:
            raise ValueError(
                f"forbidden model: {model!r} (contains {forbidden!r})"
            )
    if model not in ALLOWED_LLM_MODELS:
        raise ValueError(
            f"model not in ALLOWED_LLM_MODELS: {model!r} "
            f"(allowed: {sorted(ALLOWED_LLM_MODELS)})"
        )


def _log_cost(
    *,
    learning_db: Path,
    profile_id: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float = 0.0,
    cycle_id: str | None = None,
) -> None:
    """Append a redacted cost-log row. Never stores prompt/response text."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        conn = sqlite3.connect(learning_db)
        try:
            conn.execute(
                "INSERT INTO evolution_llm_cost_log "
                "(profile_id, ts, model, tokens_in, tokens_out, cost_usd, cycle_id) "
                "VALUES (?,?,?,?,?,?,?)",
                (profile_id, now, model, tokens_in, tokens_out, cost_usd, cycle_id),
            )
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error as e:
        logger.warning("cost log write failed: %s", e)


def _dispatch_llm(
    prompt: str,
    *,
    model: str,
    learning_db: Path | str,
    profile_id: str,
    max_tokens: int = MAX_TOKENS_CAP,
    cycle_id: str | None = None,
) -> str:
    """Central choke-point for every evolution LLM call.

    Validates model against allow/deny lists, caps ``max_tokens``, runs the
    prompt through ``redact_secrets(aggression='high')``, dispatches, and
    logs a redacted cost row. Raises ``ValueError`` on any contract breach.
    """
    _validate_model(model)

    if not isinstance(max_tokens, int) or max_tokens <= 0:
        raise ValueError(
            f"max_tokens must be a positive int, got {max_tokens!r}"
        )
    if max_tokens > MAX_TOKENS_CAP:
        raise ValueError(
            f"max_tokens {max_tokens} > {MAX_TOKENS_CAP} cap (LLD-11)"
        )

    # LLD-00 §5 — redact BEFORE dispatch. Never log the raw prompt.
    safe_prompt = redact_secrets(prompt, aggression="high")

    response = _actual_llm_call(
        safe_prompt, model=model, max_tokens=max_tokens,
    )

    # Cost-log row: lengths only, no text content. This guarantees the
    # redaction canary (e.g. a ``ghp_...`` GitHub PAT) cannot end up in
    # the audit log — we never persist the redacted prompt either.
    _log_cost(
        learning_db=Path(learning_db),
        profile_id=profile_id,
        model=model,
        tokens_in=len(safe_prompt),
        tokens_out=len(response) if isinstance(response, str) else 0,
        cycle_id=cycle_id,
    )
    return response
