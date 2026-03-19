"""
SuperLocalMemory V3 — LangChain Integration
============================================

MIGRATION NOTICE: This adapter has been replaced by a standalone
LangChain partner package: ``langchain-superlocalmemory``

    pip install langchain-superlocalmemory

The partner package uses the direct Python API (no subprocess calls)
and follows LangChain's recommended integration pattern.

See: https://github.com/qualixar/langchain-superlocalmemory

This file is kept for backward compatibility but will be removed
in a future version. New projects should use the partner package.

Part of Qualixar | Author: Varun Pratap Bhardwaj (qualixar.com)
Paper: https://arxiv.org/abs/2603.14588
"""

from __future__ import annotations

import json
import subprocess
import warnings
from typing import Any, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

_DEPRECATION_MSG = (
    "superlocalmemory.integrations.langchain_memory is deprecated. "
    "Install the partner package instead: pip install langchain-superlocalmemory"
)


def _run_slm(args: list[str]) -> dict[str, Any]:
    """Run a slm CLI command and return parsed JSON output."""
    result = subprocess.run(
        ["slm"] + args + ["--json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


class SuperLocalMemoryChatHistory(BaseChatMessageHistory):
    """LangChain chat message history backed by SuperLocalMemory V3.

    .. deprecated::
        Use ``langchain-superlocalmemory`` partner package instead.
    """

    def __init__(
        self,
        session_id: str = "default",
        agent_id: str = "langchain",
        max_messages: int = 50,
    ) -> None:
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        self.session_id = session_id
        self.agent_id = agent_id
        self.max_messages = max_messages

    @property
    def messages(self) -> list[BaseMessage]:
        result = _run_slm([
            "recall",
            f"conversation session:{self.session_id}",
            "--limit", str(self.max_messages),
        ])
        facts = result.get("results", [])
        messages: list[BaseMessage] = []
        for fact in facts:
            content = fact.get("content", "")
            if content.startswith("[human] "):
                messages.append(HumanMessage(content=content[8:]))
            elif content.startswith("[ai] "):
                messages.append(AIMessage(content=content[5:]))
            elif content.startswith("[system] "):
                messages.append(SystemMessage(content=content[9:]))
        return messages

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        for msg in messages:
            prefix = {
                "human": "[human]",
                "ai": "[ai]",
                "system": "[system]",
            }.get(msg.type, f"[{msg.type}]")
            content = f"{prefix} {msg.content} [session:{self.session_id}]"
            subprocess.run(
                ["slm", "remember", content],
                capture_output=True,
                timeout=10,
            )

    def clear(self) -> None:
        result = _run_slm([
            "recall",
            f"session:{self.session_id}",
            "--limit", "200",
        ])
        for fact in result.get("results", []):
            fact_id = fact.get("fact_id")
            if fact_id:
                subprocess.run(
                    ["slm", "delete", fact_id, "--yes"],
                    capture_output=True,
                    timeout=10,
                )


class SuperLocalMemoryRetriever:
    """Retriever-style interface for querying SuperLocalMemory V3.

    .. deprecated::
        Use ``langchain-superlocalmemory`` partner package instead.
    """

    def __init__(self, limit: int = 5, agent_id: str = "langchain") -> None:
        warnings.warn(_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
        self.limit = limit
        self.agent_id = agent_id

    def get_relevant_memories(self, query: str) -> list[str]:
        result = _run_slm(["recall", query, "--limit", str(self.limit)])
        return [
            fact.get("content", "")
            for fact in result.get("results", [])
            if fact.get("content")
        ]

    def as_context_string(self, query: str) -> str:
        memories = self.get_relevant_memories(query)
        if not memories:
            return ""
        lines = ["[Relevant memories from SuperLocalMemory:]"]
        lines.extend(f"- {m}" for m in memories)
        return "\n".join(lines)
