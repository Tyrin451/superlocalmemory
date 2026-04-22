# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Post-upgrade version banner.

Writes ``$SLM_DATA_DIR/.version`` (default ``~/.superlocalmemory/.version``)
and prints a short factual banner the first time the CLI or daemon is
invoked after a ``pip install -U`` / ``npm install -g`` that changes the
installed version. Every subsequent invocation is a no-op.

The banner is best-effort and must never raise — a disk error or a
corrupt marker makes the banner silent, not the CLI broken.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _data_dir() -> Path:
    return Path(os.environ.get("SLM_DATA_DIR") or Path.home() / ".superlocalmemory")


def _marker_path() -> Path:
    return _data_dir() / ".version"


def read_marker_version() -> str | None:
    """Return the marker string or None if missing / unreadable."""
    try:
        raw = _marker_path().read_bytes()
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError):
        return None
    # Marker is a single-line ASCII version — anything outside that is treated
    # as unknown so we never act on garbage.
    try:
        text = raw.decode("ascii").strip()
    except UnicodeDecodeError:
        return None
    if not text or any(ord(c) < 0x20 for c in text):
        return None
    return text


def write_marker_version(version: str) -> bool:
    """Persist the current version to the marker. Returns True on success."""
    target = _marker_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".version.tmp")
        tmp.write_text(version + "\n", encoding="ascii")
        os.replace(tmp, target)
        return True
    except OSError:
        return False


def _has_existing_db() -> bool:
    """True if a memory.db already exists — signals a pre-v3.4.26 user
    upgrading in-place (the marker only began shipping in v3.4.26)."""
    return (_data_dir() / "memory.db").exists()


def _banner(prior: str | None, current: str) -> str:
    header = (f"SuperLocalMemory upgraded from {prior} to {current}"
              if prior else
              f"SuperLocalMemory upgraded to {current} (from an earlier version)")
    return "\n".join([
        header,
        "  - Multi-IDE MCP processes now share a worker — large RAM drop",
        "  - Feedback and learning signals flow from every IDE to the daemon",
        "  - Silent data migration complete; no manual steps required",
        "Run `slm doctor` to verify your setup.",
        "",
    ])


def check_and_emit_upgrade_banner(current: str) -> bool:
    """Print the banner once per upgrade boundary. Idempotent.

    Returns True if the banner was emitted on this call, else False.
    Never raises — swallows I/O errors so a broken data directory cannot
    take down the CLI.
    """
    try:
        prior = read_marker_version()

        if prior == current:
            return False

        # Fresh install: no marker, no DB. Stay quiet — the setup wizard
        # handles the welcome. Still write the marker so subsequent
        # invocations are no-ops.
        if prior is None and not _has_existing_db():
            write_marker_version(current)
            return False

        sys.stdout.write(_banner(prior, current))
        sys.stdout.flush()
        write_marker_version(current)
        return True
    except Exception:
        # Banner is advisory. A failure here must never propagate.
        return False
