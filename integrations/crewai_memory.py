"""
SuperLocalMemory V3 — CrewAI Integration
=========================================

MIGRATION NOTICE: This adapter has been replaced by a standalone
package: ``crewai-superlocalmemory``

    pip install crewai-superlocalmemory

The new package implements CrewAI's StorageBackend Protocol (2026)
and uses the direct Python API. CrewAI has deprecated ExternalMemory
in favor of the unified Memory class with pluggable storage backends.

See: https://github.com/qualixar/crewai-superlocalmemory

This file is kept for backward compatibility but will be removed
in a future version. New projects should use the partner package.

Part of Qualixar | Author: Varun Pratap Bhardwaj (qualixar.com)
Paper: https://arxiv.org/abs/2603.14588
"""

from __future__ import annotations

import json
import subprocess
import warnings
from typing import Any

_DEPRECATION_MSG = (
    "superlocalmemory.integrations.crewai_memory is deprecated. "
    "CrewAI now uses a unified Memory class with StorageBackend protocol. "
    "Install the partner package instead: pip install crewai-superlocalmemory"
)


def _slm(args: list[str], capture: bool = True) -> dict[str, Any]:
    cmd = ["slm"] + args
    if capture:
        cmd += ["--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0 or not capture:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


class SuperLocalMemoryStorage:
    """Legacy CrewAI storage adapter (subprocess-based).

    .. deprecated::
        Use ``crewai-superlocalmemory`` partner package instead.
        CrewAI now uses StorageBackend protocol, not ExternalMemory.
    """

    def __init__(
        self, agent_id: str = "crewai", limit: int = 10,
    ) -> None:
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        self.agent_id = agent_id
        self.limit = limit

    def save(self, value: str, metadata: dict[str, Any] | None = None) -> None:
        content = f"[crew:{self.agent_id}] {value}"
        subprocess.run(
            ["slm", "remember", content],
            capture_output=True, timeout=15,
        )

    def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        n = limit or self.limit
        result = _slm(["recall", query, "--limit", str(n)])
        return [
            {
                "id": fact.get("fact_id", ""),
                "memory": fact.get("content", ""),
                "score": fact.get("score", 0.0),
            }
            for fact in result.get("results", [])
        ]

    def reset(self) -> None:
        result = _slm(["recall", f"crew:{self.agent_id}", "--limit", "500"])
        for fact in result.get("results", []):
            fact_id = fact.get("fact_id")
            if fact_id:
                subprocess.run(
                    ["slm", "delete", fact_id, "--yes"],
                    capture_output=True, timeout=10,
                )
