from datetime import datetime, timedelta, timezone

from app.core.config import settings

# Build a fixed-offset timezone from the TIME_ZONE setting (UTC offset in hours).
# This replaces pytz.FixedOffset to eliminate the untyped dependency.
_tz_offset = timezone(timedelta(hours=settings.TIME_ZONE))


def get_current_time() -> datetime:
    """Return the current local time as a naive datetime (no tzinfo)."""
    return datetime.now(_tz_offset).replace(tzinfo=None)
