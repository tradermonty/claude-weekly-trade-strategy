"""US market holiday calendar with dynamic calculation."""

from __future__ import annotations

from datetime import date, time, timedelta


class USMarketCalendar:
    """Calculate US stock market holidays and early close days dynamically."""

    def is_market_holiday(self, d: date) -> bool:
        """Return True if the given date is a market holiday (closed all day)."""
        return d in self._holidays(d.year)

    def is_early_close(self, d: date) -> bool:
        """Return True if the market closes early (13:00 ET) on this date."""
        return d in self._early_close_days(d.year)

    def next_trading_day(self, d: date) -> date:
        """Return the next day the market is open (skips weekends and holidays)."""
        candidate = d + timedelta(days=1)
        while candidate.weekday() >= 5 or self.is_market_holiday(candidate):
            candidate += timedelta(days=1)
        return candidate

    def get_market_close_time(self, d: date) -> time:
        """Return market close time: 13:00 for early close, 16:00 normally."""
        if self.is_early_close(d):
            return time(13, 0)
        return time(16, 0)

    # --- Private helpers ---

    def _holidays(self, year: int) -> set[date]:
        """Compute all market holidays for a given year."""
        holidays: set[date] = set()

        # New Year's Day: Jan 1 (observed)
        holidays.add(self._observed(date(year, 1, 1)))

        # MLK Day: January 3rd Monday
        holidays.add(self._nth_weekday(year, 1, 0, 3))  # Monday=0

        # Presidents' Day: February 3rd Monday
        holidays.add(self._nth_weekday(year, 2, 0, 3))

        # Good Friday
        holidays.add(self._good_friday(year))

        # Memorial Day: May last Monday
        holidays.add(self._last_weekday(year, 5, 0))

        # Juneteenth: June 19 (observed)
        holidays.add(self._observed(date(year, 6, 19)))

        # Independence Day: July 4 (observed)
        holidays.add(self._observed(date(year, 7, 4)))

        # Labor Day: September 1st Monday
        holidays.add(self._nth_weekday(year, 9, 0, 1))

        # Thanksgiving: November 4th Thursday
        holidays.add(self._nth_weekday(year, 11, 3, 4))  # Thursday=3

        # Christmas: December 25 (observed)
        holidays.add(self._observed(date(year, 12, 25)))

        return holidays

    def _early_close_days(self, year: int) -> set[date]:
        """Compute early close days (13:00 ET close)."""
        days: set[date] = set()

        # Day before Independence Day (July 3) if it's a weekday
        jul3 = date(year, 7, 3)
        if jul3.weekday() < 5:
            days.add(jul3)

        # Day after Thanksgiving (Black Friday)
        thanksgiving = self._nth_weekday(year, 11, 3, 4)
        days.add(thanksgiving + timedelta(days=1))

        # Christmas Eve (Dec 24) if it's a weekday
        dec24 = date(year, 12, 24)
        if dec24.weekday() < 5:
            days.add(dec24)

        return days

    @staticmethod
    def _observed(d: date) -> date:
        """If Saturday, observe on Friday; if Sunday, observe on Monday."""
        if d.weekday() == 5:  # Saturday
            return d - timedelta(days=1)
        if d.weekday() == 6:  # Sunday
            return d + timedelta(days=1)
        return d

    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
        """Return the n-th occurrence of weekday in the given month.

        weekday: 0=Monday .. 6=Sunday
        n: 1-based (1st, 2nd, 3rd, 4th, 5th)
        """
        first = date(year, month, 1)
        # Days until the first occurrence of the target weekday
        days_ahead = (weekday - first.weekday()) % 7
        first_occ = first + timedelta(days=days_ahead)
        return first_occ + timedelta(weeks=n - 1)

    @staticmethod
    def _last_weekday(year: int, month: int, weekday: int) -> date:
        """Return the last occurrence of weekday in the given month."""
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)
        days_back = (last_day.weekday() - weekday) % 7
        return last_day - timedelta(days=days_back)

    @staticmethod
    def _good_friday(year: int) -> date:
        """Compute Good Friday using the Anonymous Gregorian algorithm for Easter."""
        # Computus (Anonymous Gregorian algorithm)
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        l = (32 + 2 * e + 2 * i - h - k) % 7  # noqa: E741
        m = (a + 11 * h + 22 * l) // 451
        month, day = divmod(h + l - 7 * m + 114, 31)
        easter = date(year, month, day + 1)
        return easter - timedelta(days=2)
