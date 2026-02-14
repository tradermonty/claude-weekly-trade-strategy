"""Tests for the SchedulerGuard class."""

from __future__ import annotations

from pathlib import Path

import pytest

from trading.core.scheduler_guard import SchedulerGuard


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSchedulerGuard:
    """SchedulerGuard exclusive file-lock behaviour."""

    def test_acquire_and_release(self, tmp_path: Path):
        """Can acquire, then release the lock successfully."""
        lock_file = tmp_path / "test.lock"
        guard = SchedulerGuard(lock_file)

        assert guard.acquire() is True
        # Lock file should exist
        assert lock_file.exists()

        guard.release()
        # After release, another acquire should succeed
        guard2 = SchedulerGuard(lock_file)
        assert guard2.acquire() is True
        guard2.release()

    def test_double_acquire_fails(self, tmp_path: Path):
        """Second acquire returns False while first holds the lock."""
        lock_file = tmp_path / "test.lock"
        guard1 = SchedulerGuard(lock_file)
        guard2 = SchedulerGuard(lock_file)

        assert guard1.acquire() is True
        try:
            # Same lock file, different SchedulerGuard instance — should fail
            assert guard2.acquire() is False
        finally:
            guard1.release()

    def test_context_manager(self, tmp_path: Path):
        """Works as a context manager — lock is held inside, released after."""
        lock_file = tmp_path / "test.lock"
        guard = SchedulerGuard(lock_file)

        with guard:
            # Inside the context, the lock should be held
            assert guard._fd is not None

            # Another guard should NOT be able to acquire
            other = SchedulerGuard(lock_file)
            assert other.acquire() is False

        # After exiting context, fd should be None (released)
        assert guard._fd is None

        # Now another guard should be able to acquire
        guard3 = SchedulerGuard(lock_file)
        assert guard3.acquire() is True
        guard3.release()

    def test_context_manager_raises_on_locked(self, tmp_path: Path):
        """Raises RuntimeError when entering context while lock is held."""
        lock_file = tmp_path / "test.lock"

        holder = SchedulerGuard(lock_file)
        assert holder.acquire() is True

        try:
            blocked = SchedulerGuard(lock_file)
            with pytest.raises(RuntimeError, match="Could not acquire scheduler lock"):
                with blocked:
                    pass  # Should never reach here
        finally:
            holder.release()
