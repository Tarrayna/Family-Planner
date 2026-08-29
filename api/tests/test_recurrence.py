import asyncio
import datetime as dt

from app.recurrence import expand_occurrences
from app.tasks import materialize_series


def next_weekday(start: dt.date, weekday: int) -> dt.date:
    """The next date on/after start falling on the given weekday (Mon=0)."""
    return start + dt.timedelta(days=(weekday - start.weekday()) % 7)


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> dt.date:
    d = dt.date(year, month, 1)
    count = 0
    while True:
        if d.weekday() == weekday:
            count += 1
            if count == n:
                return d
        d += dt.timedelta(days=1)


def test_every_3_weeks_on_wednesday():
    dtstart = next_weekday(dt.date(2026, 1, 1), 2)  # Wednesday
    window_end = dtstart + dt.timedelta(weeks=12)

    result = expand_occurrences("FREQ=WEEKLY;INTERVAL=3;BYDAY=WE", dtstart, dtstart, window_end)

    expected = [dtstart + dt.timedelta(weeks=3 * i) for i in range(5)]
    assert result == expected
    assert all(d.weekday() == 2 for d in result)


def test_2nd_wednesday_of_month():
    first = nth_weekday_of_month(2026, 1, 2, 2)  # 2nd Wednesday of Jan 2026
    window_end = dt.date(2026, 4, 30)

    result = expand_occurrences("FREQ=MONTHLY;BYDAY=2WE", first, first, window_end)

    expected = [nth_weekday_of_month(2026, m, 2, 2) for m in (1, 2, 3, 4)]
    assert result == expected


def test_every_3_days():
    dtstart = dt.date(2026, 3, 1)
    window_end = dtstart + dt.timedelta(days=20)

    result = expand_occurrences("FREQ=DAILY;INTERVAL=3", dtstart, dtstart, window_end)

    expected = [dtstart + dt.timedelta(days=3 * i) for i in range(7)]  # 0..18 days
    assert result == expected


def test_until_bound_stops_generation():
    dtstart = dt.date(2026, 1, 1)
    until = dt.date(2026, 1, 10)
    window_end = dt.date(2026, 2, 1)  # window extends well past UNTIL

    result = expand_occurrences(
        f"FREQ=DAILY;UNTIL={until.strftime('%Y%m%d')}T000000Z", dtstart, dtstart, window_end
    )

    assert result[-1] == until
    assert all(d <= until for d in result)


def test_count_bound_limits_occurrences():
    dtstart = next_weekday(dt.date(2026, 1, 1), 0)  # Monday
    window_end = dtstart + dt.timedelta(weeks=52)  # window far larger than COUNT allows

    result = expand_occurrences("FREQ=WEEKLY;BYDAY=MO;COUNT=3", dtstart, dtstart, window_end)

    assert result == [dtstart + dt.timedelta(weeks=i) for i in range(3)]


def test_window_bounds_are_inclusive():
    dtstart = dt.date(2026, 5, 1)
    window_start = dtstart + dt.timedelta(days=3)  # exactly an occurrence date
    window_end = dtstart + dt.timedelta(days=9)  # exactly an occurrence date

    result = expand_occurrences("FREQ=DAILY;INTERVAL=3", dtstart, window_start, window_end)

    assert result[0] == window_start  # left edge included, not just the day after
    assert result[-1] == window_end  # right edge included, not just the day before


class FakeDB:
    """Minimal stand-in for the asyncpg pool: fetch() returns preset rows,
    execute() records what would have been inserted."""

    def __init__(self, existing_dates):
        self._existing_dates = existing_dates
        self.inserted_dates = []

    async def fetch(self, query, *args):
        return [{"due_date": d} for d in self._existing_dates]

    async def execute(self, query, *args):
        self.inserted_dates.append(args[2])  # due_date is the 3rd bound param


def test_materialize_series_inserts_only_missing_dates():
    master = {
        "id": "master-id",
        "title": "Take out trash",
        "assignee_id": None,
        "due_date": dt.date(2026, 1, 1),
        "due_time_hint": "none",
        "rrule": "FREQ=DAILY;INTERVAL=3",
    }
    today = dt.date(2026, 1, 1)
    window_start = today - dt.timedelta(days=30)
    window_end = today + dt.timedelta(days=90)
    all_occurrences = expand_occurrences(master["rrule"], master["due_date"], window_start, window_end)

    db = FakeDB(existing_dates={master["due_date"]})  # only the master row exists so far
    asyncio.run(materialize_series(db, master, today))

    expected_new = [d for d in all_occurrences if d != master["due_date"]]
    assert sorted(db.inserted_dates) == sorted(expected_new)


def test_materialize_series_is_idempotent_once_all_dates_exist():
    master = {
        "id": "master-id",
        "title": "Take out trash",
        "assignee_id": None,
        "due_date": dt.date(2026, 1, 1),
        "due_time_hint": "none",
        "rrule": "FREQ=DAILY;INTERVAL=3",
    }
    today = dt.date(2026, 1, 1)
    window_start = today - dt.timedelta(days=30)
    window_end = today + dt.timedelta(days=90)
    all_occurrences = expand_occurrences(master["rrule"], master["due_date"], window_start, window_end)

    db = FakeDB(existing_dates=set(all_occurrences))
    asyncio.run(materialize_series(db, master, today))

    assert db.inserted_dates == []
