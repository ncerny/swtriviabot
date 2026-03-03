"""Business logic for weekly winners summary subscriptions."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord

from src.models.archived_session import ArchivedSession
from src.models.weekly_summary_subscription import WeeklySummarySubscription
from src.services import storage_service

logger = logging.getLogger(__name__)

DAY_TO_WEEKDAY = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

WEEKDAY_TO_LABEL = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}

_NO_WINNERS_VALUES = {"no winners", "no winner", "none", "n/a", "na"}
DAY_ALIASES = {
    "mon": "monday",
    "monday": "monday",
    "tue": "tuesday",
    "tues": "tuesday",
    "tuesday": "tuesday",
    "wed": "wednesday",
    "wednesday": "wednesday",
    "thu": "thursday",
    "thur": "thursday",
    "thurs": "thursday",
    "thursday": "thursday",
    "fri": "friday",
    "friday": "friday",
    "sat": "saturday",
    "saturday": "saturday",
    "sun": "sunday",
    "sunday": "sunday",
}
TIMEZONE_ABBREVIATIONS = {
    "PT": "America/Los_Angeles",
    "MT": "America/Denver",
    "CT": "America/Chicago",
    "ET": "America/New_York",
    "AKT": "America/Anchorage",
    "HST": "Pacific/Honolulu",
    "UTC": "UTC",
    "GMT": "UTC",
    "Z": "UTC",
}


@dataclass
class ParsedSchedule:
    """Parsed schedule components from slash command input."""

    day: str
    time_local: str
    timezone_name: str


def parse_winners_text(raw_text: str) -> list[str]:
    """Parse winner names from a free-text admin input."""
    text = raw_text.strip()
    if not text:
        return []

    if text.casefold() in _NO_WINNERS_VALUES:
        return []

    normalized = text.replace("\n", ",")
    normalized = re.sub(r"\s+(?:and|&)\s+", ",", normalized, flags=re.IGNORECASE)

    winners: list[str] = []
    seen: set[str] = set()
    for token in normalized.split(","):
        winner = token.strip(" \t.;:-")
        if not winner:
            continue

        winner_key = winner.casefold()
        if winner_key in seen:
            continue

        seen.add(winner_key)
        winners.append(winner)

    return winners


def _normalize_day(day_token: str) -> str:
    day = DAY_ALIASES.get(day_token.strip().lower())
    if not day:
        raise ValueError(
            "day must be one of monday, tuesday, wednesday, thursday, friday, saturday, sunday"
        )
    return day


def _normalize_timezone_name(timezone_token: str) -> str:
    token = timezone_token.strip()
    mapped = TIMEZONE_ABBREVIATIONS.get(token.upper())
    timezone_name = mapped if mapped else token
    parse_timezone_name(timezone_name)
    return timezone_name


def parse_local_time(time_local: str) -> tuple[int, int]:
    """Parse HH:MM 24-hour local time input."""
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", time_local.strip())
    if not match:
        raise ValueError("time_local must use HH:MM 24-hour format")

    hour = int(match.group(1))
    minute = int(match.group(2))
    return hour, minute


def parse_timezone_name(timezone_name: str) -> ZoneInfo:
    """Parse and validate an IANA timezone string."""
    try:
        return ZoneInfo(timezone_name.strip())
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise ValueError(
            "timezone_name must be a valid IANA timezone (e.g. America/Chicago)"
        ) from e


def parse_schedule_string(schedule: str) -> ParsedSchedule:
    """Parse a schedule string like 'Sunday 18:00 CT'."""
    match = re.fullmatch(
        r"\s*([A-Za-z]+)\s+([01]\d|2[0-3]):([0-5]\d)\s+([A-Za-z/_+\-]+)\s*", schedule
    )
    if not match:
        raise ValueError("schedule must be in the format '<Day> <HH:MM> <Timezone>'")

    day_token = match.group(1)
    hour = int(match.group(2))
    minute = int(match.group(3))
    timezone_token = match.group(4)

    day = _normalize_day(day_token)
    timezone_name = _normalize_timezone_name(timezone_token)
    time_local = f"{hour:02d}:{minute:02d}"
    return ParsedSchedule(day=day, time_local=time_local, timezone_name=timezone_name)


def calculate_next_send_at(weekday: int, hour: int, minute: int, now: datetime) -> datetime:
    """Calculate the next scheduled send time in UTC."""
    days_ahead = (weekday - now.weekday()) % 7
    candidate = (now + timedelta(days=days_ahead)).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def calculate_next_send_at_local(
    local_weekday: int,
    local_hour: int,
    local_minute: int,
    timezone_name: str,
    now: datetime,
) -> datetime:
    """Calculate next send time from local weekday/time and return UTC."""
    local_tz = parse_timezone_name(timezone_name)
    now_local = now.astimezone(local_tz)

    days_ahead = (local_weekday - now_local.weekday()) % 7
    candidate_local = (now_local + timedelta(days=days_ahead)).replace(
        hour=local_hour,
        minute=local_minute,
        second=0,
        microsecond=0,
    )
    if candidate_local <= now_local:
        candidate_local += timedelta(days=7)

    return candidate_local.astimezone(timezone.utc)


def create_or_update_subscription(
    guild_id: str,
    user_id: str,
    day: str,
    time_local: str,
    timezone_name: str,
    now: datetime | None = None,
) -> WeeklySummarySubscription:
    """Create or update a weekly summary subscription."""
    weekday = DAY_TO_WEEKDAY.get(day.strip().lower())
    if weekday is None:
        raise ValueError(
            "day must be one of: monday, tuesday, wednesday, thursday, friday, saturday, sunday"
        )

    local_hour, local_minute = parse_local_time(time_local)
    timezone_name = timezone_name.strip()
    parse_timezone_name(timezone_name)
    current_time = now or datetime.now(timezone.utc)
    next_send_at = calculate_next_send_at_local(
        local_weekday=weekday,
        local_hour=local_hour,
        local_minute=local_minute,
        timezone_name=timezone_name,
        now=current_time,
    )

    subscription = WeeklySummarySubscription(
        guild_id=guild_id,
        user_id=user_id,
        weekday=next_send_at.weekday(),
        hour=next_send_at.hour,
        minute=next_send_at.minute,
        next_send_at=next_send_at,
        created_at=current_time,
        updated_at=current_time,
        timezone_name=timezone_name,
        local_weekday=weekday,
        local_hour=local_hour,
        local_minute=local_minute,
    )

    storage_service.save_weekly_summary_subscription(subscription)
    return subscription


def create_or_update_subscription_from_schedule(
    guild_id: str,
    user_id: str,
    schedule: str,
    now: datetime | None = None,
) -> WeeklySummarySubscription:
    """Create or update subscription from a schedule string."""
    parsed = parse_schedule_string(schedule)
    return create_or_update_subscription(
        guild_id=guild_id,
        user_id=user_id,
        day=parsed.day,
        time_local=parsed.time_local,
        timezone_name=parsed.timezone_name,
        now=now,
    )


def summarize_winners_from_archives(archives: list[ArchivedSession]) -> list[tuple[str, int]]:
    """Aggregate weekly winner totals, counting each winner once per round."""
    totals: dict[str, int] = {}
    display_names: dict[str, str] = {}

    for archive in archives:
        seen_in_round: set[str] = set()
        for winner in archive.winners:
            normalized = winner.strip()
            if not normalized:
                continue

            key = normalized.casefold()
            if key in seen_in_round:
                continue

            seen_in_round.add(key)
            display_names.setdefault(key, normalized)
            totals[key] = totals.get(key, 0) + 1

    sorted_keys = sorted(
        totals.keys(), key=lambda key: (-totals[key], display_names[key].casefold())
    )
    return [(display_names[key], totals[key]) for key in sorted_keys]


def format_weekly_summary_message(
    window_start: datetime,
    window_end: datetime,
    winner_summary: list[tuple[str, int]],
) -> str:
    """Format a weekly summary DM message."""
    start_label = window_start.strftime("%Y-%b-%d").upper()
    end_label = (window_end - timedelta(days=1)).strftime("%Y-%b-%d").upper()

    lines = [f"Winners for date range {start_label} to {end_label}:", ""]
    if not winner_summary:
        lines.append("No winners were recorded this week.")
    else:
        for winner, count in winner_summary:
            lines.append(f"{winner} - {count}")

    return "\n".join(lines)


def weekday_label(weekday: int) -> str:
    """Get display label for a weekday integer."""
    return WEEKDAY_TO_LABEL.get(weekday, str(weekday))


def _calculate_next_send_for_subscription(
    subscription: WeeklySummarySubscription,
    now: datetime,
) -> datetime:
    """Calculate next send time for an existing subscription."""
    return calculate_next_send_at_local(
        local_weekday=subscription.local_weekday,
        local_hour=subscription.local_hour,
        local_minute=subscription.local_minute,
        timezone_name=subscription.timezone_name,
        now=now,
    )


async def process_due_subscriptions(
    client: discord.Client,
    now: datetime | None = None,
) -> None:
    """Send summary DMs for any due weekly subscriptions."""
    current_time = now or datetime.now(timezone.utc)
    due_subscriptions = storage_service.load_due_weekly_summary_subscriptions(
        now=current_time,
        limit=50,
    )

    for subscription in due_subscriptions:
        scheduled_time = subscription.next_send_at
        window_start = scheduled_time - timedelta(days=7)
        window_end = scheduled_time

        archives = storage_service.load_archived_sessions(subscription.guild_id, limit=8)
        weekly_archives = [
            archive for archive in archives if window_start <= archive.archived_at < window_end
        ]
        winner_summary = summarize_winners_from_archives(weekly_archives)
        message = format_weekly_summary_message(
            window_start=window_start,
            window_end=window_end,
            winner_summary=winner_summary,
        )

        try:
            user = await client.fetch_user(int(subscription.user_id))
            await user.send(message)
        except Exception as e:
            logger.warning(
                "Failed to send weekly summary DM to user %s in guild %s: %s",
                subscription.user_id,
                subscription.guild_id,
                e,
            )

        next_send_at = _calculate_next_send_for_subscription(subscription, now=current_time)
        subscription.next_send_at = next_send_at
        subscription.weekday = next_send_at.weekday()
        subscription.hour = next_send_at.hour
        subscription.minute = next_send_at.minute
        subscription.updated_at = current_time
        storage_service.save_weekly_summary_subscription(subscription)
