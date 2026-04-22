# Copyright (c) 2026 Varun Pratap Bhardwaj / Qualixar
# Licensed under AGPL-3.0-or-later - see LICENSE file
# Part of SuperLocalMemory V3 | https://qualixar.com | https://varunpratap.com

"""Reader-writer lock used by the shared worker engine.

Part of Qualixar | Author: Varun Pratap Bhardwaj
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator


class EngineRWLock:
    """Writer-priority reader-writer lock.

    Usage:
        lock = EngineRWLock()
        with lock.read():
            ...
        with lock.write():
            ...

    Not reentrant.
    """

    __slots__ = ("_cond", "_readers", "_writers_waiting", "_writer_active")

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers: int = 0
        self._writers_waiting: int = 0
        self._writer_active: bool = False

    @contextmanager
    def read(self) -> Iterator[None]:
        with self._cond:
            while self._writer_active or self._writers_waiting > 0:
                self._cond.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                if self._readers == 0:
                    self._cond.notify_all()

    @contextmanager
    def write(self) -> Iterator[None]:
        with self._cond:
            self._writers_waiting += 1
            try:
                while self._readers > 0 or self._writer_active:
                    self._cond.wait()
                self._writer_active = True
            finally:
                self._writers_waiting -= 1
        try:
            yield
        finally:
            with self._cond:
                self._writer_active = False
                self._cond.notify_all()

    def stats(self) -> dict[str, int | bool]:
        with self._cond:
            return {
                "readers": self._readers,
                "writers_waiting": self._writers_waiting,
                "writer_active": self._writer_active,
            }
