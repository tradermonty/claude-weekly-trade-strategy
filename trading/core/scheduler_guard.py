"""OS-level file lock to prevent concurrent scheduler execution."""

from __future__ import annotations

import fcntl
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SchedulerGuard:
    """Exclusive file lock using fcntl.flock().

    On process crash the OS automatically releases the lock,
    so there is no stale-lock problem.

    Usage::

        guard = SchedulerGuard(config.lock_file)
        with guard:
            # Only one process runs this block at a time
            run_scheduler()

    Or manually::

        guard = SchedulerGuard(config.lock_file)
        if guard.acquire():
            try:
                run_scheduler()
            finally:
                guard.release()
    """

    def __init__(self, lock_path: Path) -> None:
        self._lock_path = lock_path
        self._fd: Optional[int] = None

    def acquire(self) -> bool:
        """Try to acquire an exclusive non-blocking lock.

        Returns True if the lock was acquired, False if another
        process already holds it.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(self._lock_path), os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False

        self._fd = fd

        # Write PID and timestamp for diagnostics
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        info = f"pid={os.getpid()}\ntimestamp={datetime.now(timezone.utc).isoformat()}\n"
        os.write(fd, info.encode())

        return True

    def release(self) -> None:
        """Release the lock and close the file descriptor."""
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            finally:
                os.close(self._fd)
                self._fd = None

    # --- Context manager ---

    def __enter__(self) -> SchedulerGuard:
        if not self.acquire():
            raise RuntimeError(
                f"Could not acquire scheduler lock: {self._lock_path} "
                "(another instance is running)"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        self.release()
