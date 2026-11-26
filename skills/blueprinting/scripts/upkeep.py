#!/usr/bin/env python3
"""Calculate a next-working-day response deadline from JSON stdin. No scheduling or writes."""

from datetime import date, datetime, timedelta, timezone
import json
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from engagement import Invalid, digest


def deadline(value):
    if not isinstance(value, dict) or set(value) != {"schema", "start", "calendar"} or value["schema"] != 1:
        raise Invalid("Deadline schema 1 needs start and calendar")
    calendar = value["calendar"]
    if not isinstance(calendar, dict) or set(calendar) != {"zone", "weekdays", "holidays"}:
        raise Invalid("Explicit IANA zone, weekdays and holidays required")
    zone = ZoneInfo(calendar["zone"])
    weekdays, holidays = calendar["weekdays"], calendar["holidays"]
    if (not isinstance(weekdays, list) or not weekdays
            or any(type(d) is not int or not 0 <= d <= 6 for d in weekdays)
            or len(set(weekdays)) != len(weekdays) or not isinstance(holidays, list)):
        raise Invalid("Weekdays must be distinct integers, Monday=0 to Sunday=6; holidays must be a list")
    holidays = {date.fromisoformat(day) for day in holidays}
    start = datetime.fromisoformat(value["start"])
    if start.tzinfo is None or start.utcoffset() is None:
        raise Invalid("Start must include an explicit UTC offset")
    local = start.astimezone(zone)
    day = local.date() + timedelta(days=1)
    while day.weekday() not in weekdays or day in holidays:
        day += timedelta(days=1)
    target = datetime.combine(day, local.time().replace(tzinfo=None))
    adjustment = "none"
    # Round-trip checks reject invented local instants during a clock change. UTC keys also
    # distinguish the two occurrences of a folded wall time, unlike local datetime equality.
    for _ in range(172801):
        valid = {}
        for fold in (0, 1):
            candidate = target.replace(tzinfo=zone, fold=fold)
            instant = candidate.astimezone(timezone.utc)
            if instant.astimezone(zone).replace(tzinfo=None) == target:
                valid[instant] = candidate
        if valid:
            if target.weekday() not in weekdays or target.date() in holidays:
                raise Invalid("Timezone adjustment reached a nonworking date; calendar requires review")
            if len(valid) > 1 and adjustment == "none":
                adjustment = "ambiguous-time-earlier"
            due = valid[min(valid)]
            return {"schema": 1, "start": value["start"], "local_start": local.isoformat(),
                    "due": due.isoformat(), "zone": calendar["zone"], "calendar_hash": digest(calendar),
                    "adjustment": adjustment,
                    "limitations": "Calculated deadline only. Retain it with the obligation; this does not assign an owner, send a reminder or resolve a decision."}
        target = target.replace(microsecond=0) + timedelta(seconds=1)
        adjustment = "nonexistent-time-advanced"
    raise Invalid("No valid local instant within two days; calendar requires review")


def main():
    try:
        print(json.dumps(deadline(json.load(sys.stdin)), indent=2))
    except (ValueError, TypeError, KeyError, OverflowError, ZoneInfoNotFoundError) as error:
        print(f"Deadline blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
