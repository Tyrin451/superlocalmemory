# SuperLocalMemory 3.2 -- Windows Compatibility Audit

**Date:** 2026-03-30
**Auditor:** Claude (Partner)
**Scope:** All Python source files in `src/superlocalmemory/`
**Result:** 4 issues found, 3 fixed, 1 verified-already-safe

---

## Summary

| Category | Files Scanned | Issues Found | Fixed | Already Safe |
|----------|--------------|-------------|-------|-------------|
| Path handling | 60+ | 0 | 0 | 0 |
| File permissions (chmod) | 1 | 1 | 1 | 0 |
| Signal handling | 0 | 0 | 0 | 0 |
| Symlinks | 1 | 1 | 1 | 0 |
| Pipe I/O (selectors) | 1 | 1 | 1 | 0 |
| sqlite-vec extension | 1 | 0 | 0 | 1 |
| Unused import (select) | 1 | 1 | 1 | 0 |
| Home directory | 20+ | 0 | 0 | 0 |
| Temp files | 1 | 0 | 0 | 0 |
| Process management | 0 | 0 | 0 | 0 |
| SQLite WAL mode | 0 | 0 | 0 | 0 |
| Subprocess | 5+ | 0 | 0 | 0 |

---

## Issue 1: `os.chmod(key_path, 0o600)` in signer.py -- FIXED

**File:** `src/superlocalmemory/attribution/signer.py` line 38
**Problem:** `os.chmod()` on Windows only supports the read-only flag (`stat.S_IWRITE`). Setting Unix-style permissions (0o600) has no effect on Windows NTFS ACLs and may confuse users.
**Fix:** Wrapped in `sys.platform != "win32"` guard. On Windows, the file is created in the user's home directory which is already ACL-protected.

## Issue 2: `symlink_to()` in v2_migrator.py -- FIXED

**File:** `src/superlocalmemory/storage/v2_migrator.py` line 393
**Problem:** `Path.symlink_to()` requires either admin privileges or Developer Mode on Windows. Without these, migration fails with `OSError`.
**Fix:** On Windows, uses `mklink /J` (directory junction) which works without elevation. Falls back gracefully with a warning if that also fails. The migration data copy still succeeds -- only the backward-compat link is affected.

## Issue 3: `selectors` for pipe I/O in worker_pool.py -- FIXED

**File:** `src/superlocalmemory/core/worker_pool.py` lines 159-163
**Problem:** `selectors.DefaultSelector()` on Windows uses `select.select()` under the hood, which only works with **sockets**, not pipe file descriptors. This would cause `OSError: [WinError 10038]` when trying to read from the subprocess stdout pipe.
**Fix:** Replaced with thread-based `_readline_with_timeout()` (same pattern already used successfully in `EmbeddingService._readline_with_timeout()`). This is fully cross-platform.

## Issue 4: Unused `import select` in embeddings.py -- FIXED

**File:** `src/superlocalmemory/core/embeddings.py` line 21
**Problem:** The `select` module was imported but never used (the file already uses the thread-based timeout approach). While harmless, it signals potential past usage of the Unix-only `select.select()` pattern.
**Fix:** Removed the unused import.

---

## Verified Safe (No Fix Needed)

### Path Handling -- SAFE

All path operations use `pathlib.Path` throughout the codebase:
- `Path.home() / ".superlocalmemory"` -- works on Windows (resolves to `C:\Users\username`)
- `Path("/")` division operator -- pathlib handles OS separators automatically
- No string concatenation with `/` for filesystem paths found
- 50+ files use `from pathlib import Path` consistently

### sqlite-vec Extension Loading -- SAFE

**File:** `src/superlocalmemory/retrieval/vector_store.py`
The `_try_load_extension()` method already has comprehensive try/except handling:
- `ImportError` -- sqlite-vec not installed
- `AttributeError` -- `enable_load_extension` not available (macOS system Python)
- Generic `Exception` -- any other failure
All caught, logged, and gracefully degraded to `available = False`. The ANNIndex fallback is used when sqlite-vec is unavailable.

### Home Directory (`Path.home()`) -- SAFE

Used in 20+ files. `Path.home()` is cross-platform and resolves correctly:
- macOS/Linux: `/Users/username` or `/home/username`
- Windows: `C:\Users\username`

### Temp Files -- SAFE

**File:** `src/superlocalmemory/core/profiles.py` line 118
Uses `tempfile.mkstemp()` with explicit `dir=` parameter, which is cross-platform.

### Subprocess Management -- SAFE

**Files:** `worker_pool.py`, `embeddings.py`
Uses `subprocess.Popen` with `sys.executable` (correct Python binary), text mode, and pipe-based I/O. No `os.fork()`, `os.getppid()`, or other Unix-only process APIs.

### SQLite WAL Mode -- SAFE

Not explicitly set in the codebase. SQLite defaults are used, which work identically on Windows. The `PRAGMA busy_timeout = 10000` in vector_store.py is cross-platform.

### Signal Handling -- SAFE

No usage of `signal.SIGALRM`, `signal.SIGKILL`, `signal.SIGUSR1/2`, or any other Unix-only signals found anywhere in the source.

---

## CI Matrix Update

**File:** `.github/workflows/test.yml`

Updated test matrix from:
```yaml
runs-on: ubuntu-latest
python-version: ["3.11", "3.12"]
```

To:
```yaml
runs-on: [ubuntu-latest, macos-latest, windows-latest]
python-version: ["3.11", "3.12", "3.13"]
fail-fast: false
```

This gives 9 test configurations (3 OS x 3 Python versions).

---

## npm Package (package.json) -- VERIFIED

- **Version:** 3.2.1 (matches pyproject.toml)
- **OS field:** Declares `["darwin", "linux", "win32"]`
- **bin/slm-npm:** Already has Windows Python detection (`py -3`, `LOCALAPPDATA` paths)
- **scripts/postinstall.js:** Already handles Windows Python detection and PEP 668
- **scripts/prepack.js:** Cross-platform `__pycache__` cleanup using Node.js `fs`
- **PYTHONPATH separator:** Uses `path.delimiter` (`;` on Windows, `:` on Unix) -- correct

---

## Windows PowerShell Scripts -- EXIST

The repo already ships Windows-specific scripts:
- `scripts/install.ps1` -- Full Windows installer with MCP auto-configuration
- `scripts/verify-install.ps1` -- Installation verification
- `scripts/start-dashboard.ps1` -- Dashboard launcher
- `scripts/test-npm-package.ps1` -- npm package tester
- `scripts/sync-wiki.ps1` -- Wiki sync
- `scripts/install-skills.ps1` -- Skill installer

---

## Test Verification

After all fixes, the full test suite passes:

```
618 passed in 9.53s
```

No regressions introduced.
