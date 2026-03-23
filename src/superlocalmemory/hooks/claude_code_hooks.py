# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under the MIT License - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Claude Code Hook Integration — invisible memory injection.

Installs hooks into Claude Code's settings.json that auto-inject
SLM context on session start and auto-capture on tool use.

Usage:
    slm hooks install    Install hooks into Claude Code settings
    slm hooks status     Check if hooks are installed
    slm hooks remove     Remove SLM hooks from settings

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
HOOKS_DIR = Path.home() / ".superlocalmemory" / "hooks"

# The hook scripts that Claude Code will execute
HOOK_SCRIPTS = {
    "slm-session-start.sh": """\
#!/bin/bash
# SLM Active Memory — Session Start Hook
# Auto-recalls relevant context at session start
slm session-context 2>/dev/null || true
""",
    "slm-auto-capture.sh": """\
#!/bin/bash
# SLM Active Memory — Auto-Capture Hook
# Evaluates tool output for decisions/bugs/preferences
# Input comes via stdin from Claude Code PostToolUse event
INPUT=$(cat)
if [ -n "$INPUT" ]; then
    echo "$INPUT" | slm observe 2>/dev/null || true
fi
""",
}

# Hook definitions for Claude Code settings.json
HOOK_DEFINITIONS = {
    "hooks": {
        "SessionStart": [
            {
                "type": "command",
                "command": str(HOOKS_DIR / "slm-session-start.sh"),
                "timeout": 10000,
            }
        ],
    }
}


def install_hooks() -> dict:
    """Install SLM hooks into Claude Code settings."""
    results = {"scripts": False, "settings": False, "errors": []}

    # 1. Create hook scripts
    try:
        HOOKS_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in HOOK_SCRIPTS.items():
            path = HOOKS_DIR / name
            path.write_text(content)
            path.chmod(0o755)
        results["scripts"] = True
    except Exception as exc:
        results["errors"].append(f"Script creation failed: {exc}")

    # 2. Update Claude Code settings.json
    try:
        if not CLAUDE_SETTINGS.parent.exists():
            CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)

        settings = {}
        if CLAUDE_SETTINGS.exists():
            settings = json.loads(CLAUDE_SETTINGS.read_text())

        # Merge hooks without overwriting existing ones
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Add SessionStart hook if not present
        session_hooks = settings["hooks"].get("SessionStart", [])
        slm_hook_cmd = str(HOOKS_DIR / "slm-session-start.sh")
        already_installed = any(
            h.get("command", "") == slm_hook_cmd
            for h in session_hooks if isinstance(h, dict)
        )

        if not already_installed:
            session_hooks.append({
                "type": "command",
                "command": slm_hook_cmd,
                "timeout": 10000,
            })
            settings["hooks"]["SessionStart"] = session_hooks

        CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2))
        results["settings"] = True
    except Exception as exc:
        results["errors"].append(f"Settings update failed: {exc}")

    return results


def remove_hooks() -> dict:
    """Remove SLM hooks from Claude Code settings."""
    results = {"scripts": False, "settings": False, "errors": []}

    # 1. Remove hook scripts
    try:
        if HOOKS_DIR.exists():
            shutil.rmtree(HOOKS_DIR)
        results["scripts"] = True
    except Exception as exc:
        results["errors"].append(f"Script removal failed: {exc}")

    # 2. Remove from Claude Code settings
    try:
        if CLAUDE_SETTINGS.exists():
            settings = json.loads(CLAUDE_SETTINGS.read_text())
            if "hooks" in settings and "SessionStart" in settings["hooks"]:
                slm_hook_cmd = str(HOOKS_DIR / "slm-session-start.sh")
                settings["hooks"]["SessionStart"] = [
                    h for h in settings["hooks"]["SessionStart"]
                    if not (isinstance(h, dict) and h.get("command", "") == slm_hook_cmd)
                ]
                if not settings["hooks"]["SessionStart"]:
                    del settings["hooks"]["SessionStart"]
                if not settings["hooks"]:
                    del settings["hooks"]
                CLAUDE_SETTINGS.write_text(json.dumps(settings, indent=2))
            results["settings"] = True
    except Exception as exc:
        results["errors"].append(f"Settings cleanup failed: {exc}")

    return results


def check_status() -> dict:
    """Check if SLM hooks are installed."""
    scripts_ok = all(
        (HOOKS_DIR / name).exists()
        for name in HOOK_SCRIPTS
    )

    settings_ok = False
    try:
        if CLAUDE_SETTINGS.exists():
            settings = json.loads(CLAUDE_SETTINGS.read_text())
            session_hooks = settings.get("hooks", {}).get("SessionStart", [])
            slm_hook_cmd = str(HOOKS_DIR / "slm-session-start.sh")
            settings_ok = any(
                h.get("command", "") == slm_hook_cmd
                for h in session_hooks if isinstance(h, dict)
            )
    except Exception:
        pass

    return {
        "installed": scripts_ok and settings_ok,
        "scripts": scripts_ok,
        "settings": settings_ok,
        "hooks_dir": str(HOOKS_DIR),
    }
