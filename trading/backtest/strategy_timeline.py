"""Blog validation and strategy period mapping for backtesting."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from trading.core.holidays import USMarketCalendar
from trading.data.models import StrategySpec
from trading.layer2.tools.strategy_parser import parse_blog

logger = logging.getLogger(__name__)

_calendar = USMarketCalendar()

# Pattern: YYYY-MM-DD-weekly-strategy.md (exact match)
_BLOG_FILENAME = re.compile(r"^\d{4}-\d{2}-\d{2}-weekly-strategy\.md$")

# Patterns to exclude
_EXCLUDED_SUFFIXES = ("_bk.md", "-en.md", " copy.md")


@dataclass
class BlogEntry:
    """A validated blog entry with its strategy and transition day."""

    blog_date: date
    transition_day: date  # first trading day on or after blog_date
    strategy: StrategySpec
    file_path: Path


@dataclass
class SkippedBlog:
    """A blog that failed validation."""

    blog_date: str
    file_path: Path
    reason: str


class StrategyTimeline:
    """Map dates to active strategies, handling blog transitions."""

    def __init__(self) -> None:
        self._entries: list[BlogEntry] = []
        self._skipped: list[SkippedBlog] = []
        self._effective_start: Optional[date] = None

    @property
    def entries(self) -> list[BlogEntry]:
        return list(self._entries)

    @property
    def skipped(self) -> list[SkippedBlog]:
        return list(self._skipped)

    @property
    def effective_start(self) -> Optional[date]:
        """Earliest valid date for backtesting (first transition day)."""
        return self._effective_start

    def build(self, blogs_dir: Path) -> None:
        """Scan blogs directory, parse and validate all blogs.

        Builds the timeline of valid strategies and records skipped blogs.
        """
        blogs_dir = Path(blogs_dir)
        if not blogs_dir.is_dir():
            raise FileNotFoundError(f"Blogs directory not found: {blogs_dir}")

        # Find all matching blog files
        candidates = sorted(
            f for f in blogs_dir.iterdir()
            if f.is_file()
            and _BLOG_FILENAME.match(f.name)
            and not any(f.name.endswith(s) for s in _EXCLUDED_SUFFIXES)
            and f.parent.name != "backup"
        )

        self._entries = []
        self._skipped = []

        for blog_path in candidates:
            blog_date_str = blog_path.name[:10]  # YYYY-MM-DD
            try:
                spec = parse_blog(blog_path)
                reason = _validate_strategy(spec)
                if reason:
                    self._skipped.append(SkippedBlog(blog_date_str, blog_path, reason))
                    logger.warning("Skipping %s: %s", blog_path.name, reason)
                    continue

                blog_d = date.fromisoformat(blog_date_str)
                transition = _first_trading_day_on_or_after(blog_d)

                self._entries.append(BlogEntry(
                    blog_date=blog_d,
                    transition_day=transition,
                    strategy=spec,
                    file_path=blog_path,
                ))
            except Exception as e:
                self._skipped.append(SkippedBlog(blog_date_str, blog_path, str(e)))
                logger.warning("Error parsing %s: %s", blog_path.name, e)

        if self._entries:
            self._effective_start = self._entries[0].transition_day

    def get_strategy(self, d: date) -> Optional[StrategySpec]:
        """Get the active strategy for a given date.

        Returns the most recent blog strategy whose transition_day <= d.
        """
        active: Optional[StrategySpec] = None
        for entry in self._entries:
            if entry.transition_day <= d:
                active = entry.strategy
            else:
                break
        return active

    def is_transition_day(self, d: date) -> bool:
        """Check if d is a transition day (first trading day of a new blog week)."""
        return any(entry.transition_day == d for entry in self._entries)

    def get_transition_entry(self, d: date) -> Optional[BlogEntry]:
        """Get the blog entry if d is a transition day."""
        for entry in self._entries:
            if entry.transition_day == d:
                return entry
        return None

    def get_all_transition_days(self) -> list[date]:
        """Return all transition days in order."""
        return [e.transition_day for e in self._entries]


def _validate_strategy(spec: StrategySpec) -> Optional[str]:
    """Validate a parsed strategy. Returns error reason or None if valid."""
    # Check current_allocation is not empty
    if not spec.current_allocation:
        return "current_allocation empty"

    # Check allocation sum is in 90-110% range
    total = sum(spec.current_allocation.values())
    if not (90 <= total <= 110):
        return f"current_allocation sum {total:.1f}% outside 90-110% range"

    # Check at least one scenario exists
    if not spec.scenarios:
        return "scenarios empty"

    return None


def _first_trading_day_on_or_after(d: date) -> date:
    """Return d if it's a trading day, otherwise the next trading day."""
    while d.weekday() >= 5 or _calendar.is_market_holiday(d):
        from datetime import timedelta
        d = d + timedelta(days=1)
    return d
