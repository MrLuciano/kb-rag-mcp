import logging
from datetime import datetime, timedelta
from typing import Optional

from croniter import croniter

log = logging.getLogger("kb-ingest.cron")


def _cron_field_matches(pattern: str, value: int) -> bool:
    if pattern == "*":
        return True
    if pattern.startswith("*/"):
        step = int(pattern[2:])
        return step > 0 and value % step == 0
    if "-" in pattern:
        parts = pattern.split("-")
        return int(parts[0]) <= value <= int(parts[1])
    if "," in pattern:
        return any(
            _cron_field_matches(p.strip(), value) for p in pattern.split(",")
        )
    return int(pattern) == value


def cron_matches(dt: datetime, expression: str) -> bool:
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression: '{expression}' — "
            f"expected 5 fields, got {len(parts)}"
        )
    fields = [dt.minute, dt.hour, dt.day, dt.month, dt.isoweekday() % 7]
    for i, (part, val) in enumerate(zip(parts, fields)):
        if not _cron_field_matches(part, val):
            return False
    return True


def validate_cron(expression: str) -> None:
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Expected 5 fields, got {len(parts)}: '{expression}'"
        )
    for part in parts:
        if not part.strip():
            raise ValueError(f"Empty field in cron expression: '{expression}'")
        if part == "*":
            continue
        if part.startswith("*/"):
            step = part[2:]
            if not step.isdigit() or int(step) <= 0:
                raise ValueError(
                    f"Invalid step value in '{part}': must be positive integer"
                )
            continue
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2:
                raise ValueError(
                    f"Invalid range '{part}': expected N-M"
                )
            for b in bounds:
                if not b.strip().isdigit():
                    raise ValueError(
                        f"Invalid range value '{b}' in '{part}'"
                    )
            continue
        if "," in part:
            for sub in part.split(","):
                validate_cron_field(sub)
            continue
        validate_cron_field(part)


def validate_cron_field(part: str) -> None:
    part = part.strip()
    if not part.isdigit():
        raise ValueError(f"Invalid cron field value: '{part}'")
    val = int(part)
    if val < 0 or val > 59:
        raise ValueError(
            f"Value {val} out of range (0-59) in '{part}'"
        )


def next_cron_time(
    after: datetime, expression: str
) -> Optional[datetime]:
    validate_cron(expression)
    try:
        cron = croniter(expression, after)
        return cron.get_next(datetime)
    except (ValueError, KeyError) as e:
        log.warning(
            "No future cron match found for '%s' (after %s): %s",
            expression,
            after,
            e,
        )
        return None
