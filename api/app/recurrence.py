import datetime as dt

from dateutil.rrule import rrulestr


def expand_occurrences(
    rrule: str, dtstart: dt.date, window_start: dt.date, window_end: dt.date
) -> list[dt.date]:
    """Occurrence dates for an RFC 5545 RRULE (UNTIL/COUNT may be embedded in
    it) anchored at dtstart, within [window_start, window_end] inclusive."""
    # UNTIL is UTC per RFC 5545 (and how repeat.html emits it, "...T000000Z"),
    # which dateutil requires DTSTART to also be timezone-aware for.
    rule = rrulestr(f"RRULE:{rrule}", dtstart=dt.datetime.combine(dtstart, dt.time(), dt.timezone.utc))
    start = dt.datetime.combine(window_start, dt.time(), dt.timezone.utc)
    end = dt.datetime.combine(window_end, dt.time(23, 59, 59), dt.timezone.utc)
    return [occurrence.date() for occurrence in rule.between(start, end, inc=True)]
