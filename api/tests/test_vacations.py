import datetime as dt

from app.vacations import date_in_any_window, days_late


def test_days_late_no_vacation():
    today = dt.date(2026, 6, 10)
    due = dt.date(2026, 6, 5)
    assert days_late(due, today) == 5


def test_days_late_due_today_or_future_is_zero():
    today = dt.date(2026, 6, 10)
    assert days_late(today, today) == 0
    assert days_late(today + dt.timedelta(days=1), today) == 0


def test_days_late_none_due_date_is_zero():
    assert days_late(None, dt.date(2026, 6, 10)) == 0


def test_days_late_fully_paused_by_vacation():
    today = dt.date(2026, 6, 10)
    due = dt.date(2026, 6, 5)  # 5 days late, unpaused
    windows = [(dt.date(2026, 6, 5), dt.date(2026, 6, 12))]  # spans the whole gap
    assert days_late(due, today, windows) == 0


def test_days_late_partially_paused_by_vacation():
    today = dt.date(2026, 6, 10)
    due = dt.date(2026, 6, 1)  # 9 days late, unpaused
    windows = [(dt.date(2026, 6, 5), dt.date(2026, 6, 7))]  # 3 days inside the gap
    assert days_late(due, today, windows) == 9 - 3


def test_days_late_vacation_outside_gap_has_no_effect():
    today = dt.date(2026, 6, 10)
    due = dt.date(2026, 6, 5)  # 5 days late
    windows = [(dt.date(2026, 1, 1), dt.date(2026, 1, 31))]  # unrelated month
    assert days_late(due, today, windows) == 5


def test_days_late_multiple_nonoverlapping_windows_sum():
    today = dt.date(2026, 6, 20)
    due = dt.date(2026, 6, 1)  # 19 days late, unpaused
    windows = [
        (dt.date(2026, 6, 5), dt.date(2026, 6, 6)),  # 2 days
        (dt.date(2026, 6, 10), dt.date(2026, 6, 12)),  # 3 days
    ]
    assert days_late(due, today, windows) == 19 - 5


def test_date_in_any_window():
    windows = [(dt.date(2026, 6, 5), dt.date(2026, 6, 10))]
    assert date_in_any_window(dt.date(2026, 6, 5), windows) is True  # left edge
    assert date_in_any_window(dt.date(2026, 6, 10), windows) is True  # right edge
    assert date_in_any_window(dt.date(2026, 6, 11), windows) is False
    assert date_in_any_window(dt.date(2026, 6, 4), windows) is False


def test_date_in_any_window_empty():
    assert date_in_any_window(dt.date(2026, 6, 5), []) is False
