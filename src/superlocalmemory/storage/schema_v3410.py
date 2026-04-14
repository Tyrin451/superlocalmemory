# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""SuperLocalMemory V3.4.10 "Fortress" — Schema Extensions.

New tables for cloud backup + entity quality:
  - backup_destinations: Cloud backup targets (Google Drive, GitHub, local)
  - entity_blacklist: Stop words and known garbage entity names

Design rules (inherited):
  - CREATE IF NOT EXISTS for idempotency
  - profile_id where applicable
  - Never ALTER existing column types

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL — Backup Destinations
# ---------------------------------------------------------------------------

_BACKUP_DESTINATIONS_DDL = """
CREATE TABLE IF NOT EXISTS backup_destinations (
    id TEXT PRIMARY KEY,
    profile_id TEXT DEFAULT 'default',
    destination_type TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    credentials_ref TEXT DEFAULT '',
    config TEXT DEFAULT '{}',
    last_sync_at TEXT,
    last_sync_status TEXT DEFAULT 'never',
    last_sync_error TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_backup_dest_type
    ON backup_destinations(destination_type);
CREATE INDEX IF NOT EXISTS idx_backup_dest_profile
    ON backup_destinations(profile_id);
"""

# ---------------------------------------------------------------------------
# DDL — Entity Blacklist
# ---------------------------------------------------------------------------

_ENTITY_BLACKLIST_DDL = """
CREATE TABLE IF NOT EXISTS entity_blacklist (
    term TEXT PRIMARY KEY,
    reason TEXT DEFAULT 'stop_word',
    added_at TEXT NOT NULL
);
"""

# ---------------------------------------------------------------------------
# Default blacklist entries (seeded on first migration)
# ---------------------------------------------------------------------------

_DEFAULT_BLACKLIST = [
    # English stop words that frequently become garbage entities
    "a", "an", "the", "all", "not", "no", "yes", "and", "or", "but",
    "if", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "shall", "should", "can", "could", "just", "also", "only",
    "very", "too", "so", "then", "than", "that", "this",
    "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "any", "many", "much", "own", "same",
    "new", "old", "first", "last", "next", "now",
    # Months (biggest historical source of garbage)
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    # Technical terms commonly misclassified
    "test", "fix", "build", "check", "run", "start", "stop",
    "error", "status", "version", "query", "data", "file",
    "ready", "done", "complete", "pending", "active", "failed",
    "total", "count", "key", "value", "true", "false",
    # Abstract nouns misclassified as people
    "completeness", "correctness", "limitations", "requirements",
    "performance", "security", "quality", "coverage", "progress",
    "analysis", "research", "implementation", "verification",
]


# ---------------------------------------------------------------------------
# Migration runner
# ---------------------------------------------------------------------------

def apply_v3410_schema(db_path: str | sqlite3.Connection) -> dict:
    """Apply all v3.4.10 schema changes. Idempotent."""
    result = {"applied": [], "errors": []}

    if isinstance(db_path, sqlite3.Connection):
        conn = db_path
        own_connection = False
    else:
        conn = sqlite3.connect(str(db_path))
        own_connection = True

    try:
        # Backup destinations table
        try:
            conn.executescript(_BACKUP_DESTINATIONS_DDL)
            result["applied"].append("backup_destinations table + indexes")
        except sqlite3.OperationalError as e:
            result["errors"].append(f"backup_destinations: {e}")

        # Entity blacklist table
        try:
            conn.executescript(_ENTITY_BLACKLIST_DDL)
            result["applied"].append("entity_blacklist table")
        except sqlite3.OperationalError as e:
            result["errors"].append(f"entity_blacklist: {e}")

        # Seed default blacklist (only inserts missing entries)
        now = __import__("datetime").datetime.now().isoformat()
        seeded = 0
        for term in _DEFAULT_BLACKLIST:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO entity_blacklist (term, reason, added_at) "
                    "VALUES (?, 'stop_word', ?)",
                    (term, now),
                )
                seeded += 1
            except sqlite3.OperationalError:
                pass
        if seeded:
            result["applied"].append(f"entity_blacklist seeded ({len(_DEFAULT_BLACKLIST)} terms)")

        # Mark version
        try:
            conn.execute(
                "INSERT OR IGNORE INTO schema_version (version, applied_at) VALUES (?, ?)",
                ("3.4.10", now),
            )
        except sqlite3.OperationalError:
            pass

        conn.commit()

        if result["applied"]:
            logger.info("Schema v3.4.10 applied: %s", ", ".join(result["applied"]))

    except Exception as e:
        result["errors"].append(f"fatal: {e}")
        logger.error("Schema v3.4.10 migration failed: %s", e)
    finally:
        if own_connection:
            conn.close()

    return result
