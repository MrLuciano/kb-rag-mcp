"""Tests for Phase 52: Cron expression matcher (ingest/core/cron.py)."""

import pytest
from datetime import datetime
from ingest.core.cron import (
    _cron_field_matches,
    cron_matches,
    next_cron_time,
    validate_cron,
    validate_cron_field,
)


# ── _cron_field_matches ──────────────────────────────────────────────────────


class TestCronFieldMatches:
    def test_star_matches_any(self):
        assert _cron_field_matches("*", 0)
        assert _cron_field_matches("*", 23)
        assert _cron_field_matches("*", 59)

    def test_exact_match(self):
        assert _cron_field_matches("5", 5)
        assert not _cron_field_matches("5", 6)

    def test_step_match(self):
        assert _cron_field_matches("*/15", 0)
        assert _cron_field_matches("*/15", 15)
        assert _cron_field_matches("*/15", 30)
        assert _cron_field_matches("*/15", 45)
        assert not _cron_field_matches("*/15", 7)
        assert not _cron_field_matches("*/15", 59)

    def test_range_match(self):
        assert _cron_field_matches("9-17", 9)
        assert _cron_field_matches("9-17", 12)
        assert _cron_field_matches("9-17", 17)
        assert not _cron_field_matches("9-17", 8)
        assert not _cron_field_matches("9-17", 18)

    def test_comma_list_match(self):
        assert _cron_field_matches("15,45", 15)
        assert _cron_field_matches("15,45", 45)
        assert not _cron_field_matches("15,45", 30)
        assert not _cron_field_matches("15,45", 0)


# ── cron_matches ─────────────────────────────────────────────────────────────


class TestCronMatches:
    def test_exact_time_match(self):
        dt = datetime(2024, 1, 1, 3, 0)
        assert cron_matches(dt, "0 3 * * *")

    def test_exact_time_no_match(self):
        dt = datetime(2024, 1, 1, 3, 5)
        assert not cron_matches(dt, "0 3 * * *")

    def test_step_minute_match(self):
        dt = datetime(2024, 1, 1, 0, 30)
        assert cron_matches(dt, "*/30 * * * *")

    def test_step_minute_no_match(self):
        dt = datetime(2024, 1, 1, 0, 7)
        assert not cron_matches(dt, "*/30 * * * *")

    def test_comma_list(self):
        dt = datetime(2024, 1, 1, 0, 15)
        assert cron_matches(dt, "15,45 * * * *")

    def test_range_hour(self):
        dt = datetime(2024, 1, 1, 9, 0)
        assert cron_matches(dt, "0 9-17 * * *")

    def test_range_hour_outside(self):
        dt = datetime(2024, 1, 1, 18, 0)
        assert not cron_matches(dt, "0 9-17 * * *")

    def test_specific_dow(self):
        dt = datetime(2024, 1, 1, 0, 0)
        assert cron_matches(dt, "0 0 * * 1")

    def test_specific_dow_no_match(self):
        dt = datetime(2024, 1, 7, 0, 0)
        assert not cron_matches(dt, "0 0 * * 1")

    def test_specific_month(self):
        dt = datetime(2024, 6, 1, 0, 0)
        assert cron_matches(dt, "0 0 * 6 *")

    def test_month_no_match(self):
        dt = datetime(2024, 7, 1, 0, 0)
        assert not cron_matches(dt, "0 0 * 6 *")

    def test_day_of_month(self):
        dt = datetime(2024, 1, 15, 0, 0)
        assert cron_matches(dt, "0 0 15 * *")

    def test_invalid_field_count(self):
        with pytest.raises(ValueError, match="expected 5 fields"):
            cron_matches(datetime(2024, 1, 1), "0 3 *")

    def test_whitespace_handling(self):
        dt = datetime(2024, 1, 1, 3, 0)
        assert cron_matches(dt, "  0 3 * * *  ")

    def test_mixed_pattern(self):
        dt = datetime(2024, 1, 15, 10, 30)
        assert cron_matches(dt, "30,0 9-17 15 1,6 1,3,5")


# ── validate_cron ────────────────────────────────────────────────────────────


class TestValidateCron:
    def test_valid_cron_passes(self):
        validate_cron("*/15 * * * *")
        validate_cron("0 3 * * 1")
        validate_cron("30 9-17 15 1,6 1,3,5")

    def test_wrong_field_count(self):
        with pytest.raises(ValueError, match="Expected 5 fields"):
            validate_cron("0 3 *")

    def test_empty_expression(self):
        with pytest.raises(ValueError, match="Expected 5 fields"):
            validate_cron("")

    def test_invalid_step_value(self):
        with pytest.raises(ValueError, match="Invalid step value"):
            validate_cron("*/0 * * * *")

    def test_negative_step(self):
        with pytest.raises(ValueError, match="Invalid step value"):
            validate_cron("*/-5 * * * *")

    def test_non_numeric_step(self):
        with pytest.raises(ValueError, match="Invalid step value"):
            validate_cron("*/abc * * * *")

    def test_invalid_range_format(self):
        with pytest.raises(ValueError, match="Invalid range"):
            validate_cron("9--5 * * * *")

    def test_range_non_numeric(self):
        with pytest.raises(ValueError, match="Invalid range value"):
            validate_cron("a-b * * * *")

    def test_range_half_non_numeric(self):
        with pytest.raises(ValueError, match="Invalid range value"):
            validate_cron("9-b * * * *")

    def test_invalid_comma_value(self):
        with pytest.raises(ValueError, match="Invalid cron field"):
            validate_cron("15,abc * * * *")

    def test_field_out_of_range(self):
        with pytest.raises(ValueError, match="out of range"):
            validate_cron("99 * * * *")

    def test_field_negative(self):
        with pytest.raises(ValueError, match="Invalid range value"):
            validate_cron("-5 * * * *")


# ── validate_cron_field ──────────────────────────────────────────────────────


class TestValidateCronField:
    def test_valid(self):
        validate_cron_field("5")
        validate_cron_field("0")
        validate_cron_field("59")

    def test_non_digit(self):
        with pytest.raises(ValueError, match="Invalid cron field"):
            validate_cron_field("abc")

    def test_negative(self):
        with pytest.raises(ValueError, match="Invalid cron field"):
            validate_cron_field("-1")

    def test_out_of_range_high(self):
        with pytest.raises(ValueError, match="out of range"):
            validate_cron_field("60")

    def test_out_of_range_negative(self):
        with pytest.raises(ValueError, match="Invalid cron field"):
            validate_cron_field("-5")

    def test_blank(self):
        with pytest.raises(ValueError, match="Invalid cron field"):
            validate_cron_field(" ")


# ── next_cron_time ───────────────────────────────────────────────────────────


class TestNextCronTime:
    def test_next_every_30_minutes(self):
        dt = datetime(2024, 1, 1, 0, 5)
        nxt = next_cron_time(dt, "*/30 * * * *")
        assert nxt == datetime(2024, 1, 1, 0, 30)

    def test_next_same_day(self):
        dt = datetime(2024, 1, 1, 9, 0)
        nxt = next_cron_time(dt, "0 17 * * *")
        assert nxt == datetime(2024, 1, 1, 17, 0)

    def test_next_rolls_to_next_hour(self):
        dt = datetime(2024, 1, 1, 10, 5)
        nxt = next_cron_time(dt, "0 * * * *")
        assert nxt == datetime(2024, 1, 1, 11, 0)

    def test_next_rolls_to_next_day(self):
        dt = datetime(2024, 1, 1, 23, 30)
        nxt = next_cron_time(dt, "0 3 * * *")
        assert nxt == datetime(2024, 1, 2, 3, 0)

    def test_next_weekly(self):
        dt = datetime(2024, 1, 1, 0, 0)
        nxt = next_cron_time(dt, "0 3 * * 1")
        assert nxt == datetime(2024, 1, 1, 3, 0)

    def test_next_weekly_rolls_to_next_week(self):
        dt = datetime(2024, 1, 2, 0, 0)
        nxt = next_cron_time(dt, "0 3 * * 1")
        assert nxt == datetime(2024, 1, 8, 3, 0)

    def test_next_just_past_match(self):
        dt = datetime(2024, 1, 1, 3, 1)
        nxt = next_cron_time(dt, "0 3 * * 1")
        assert nxt == datetime(2024, 1, 8, 3, 0)

    def test_star_minute(self):
        dt = datetime(2024, 1, 1, 10, 5)
        nxt = next_cron_time(dt, "* * * * *")
        assert nxt == datetime(2024, 1, 1, 10, 6)

    def test_no_future_match_returns_none(self):
        dt = datetime(2024, 1, 1, 0, 0)
        nxt = next_cron_time(dt, "0 0 30 2 *")
        assert nxt is None

    def test_invalid_cron_raises(self):
        with pytest.raises(ValueError):
            next_cron_time(datetime(2024, 1, 1), "not a cron")
