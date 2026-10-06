# app/utils/timezone.py

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("Africa/Lagos")


def now():
    """
    Return the current datetime in the FOCOST application timezone.

    FOCOST uses Africa/Lagos as its application/business timezone.
    """
    return datetime.now(APP_TIMEZONE)


def today():
    """
    Return the current calendar date in the FOCOST application timezone.
    """
    return now().date()


def utc_now():
    """
    Return the current timezone-aware UTC datetime.

    Use this for timestamps that represent an absolute point in time,
    especially security, authentication, audit, subscription, webhook,
    and database event timestamps.
    """
    return datetime.now(UTC)


def utc_today():
    """
    Return the current UTC calendar date.
    """
    return utc_now().date()


def as_utc(value):
    """
    Normalize a datetime to timezone-aware UTC.

    Existing FOCOST database records may contain naive UTC datetimes.
    Naive values are therefore interpreted as UTC rather than rejected.
    """
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)