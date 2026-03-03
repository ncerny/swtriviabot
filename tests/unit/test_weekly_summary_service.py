"""Unit tests for weekly summary subscription and aggregation logic."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from src.models.answer import Answer
from src.models.archived_session import ArchivedSession
from src.models.weekly_summary_subscription import WeeklySummarySubscription
from src.services import weekly_summary_service


def _archive(
    archived_at: datetime,
    winners: list[str],
    guild_id: str = "guild-1",
) -> ArchivedSession:
    return ArchivedSession(
        guild_id=guild_id,
        question_text="Q?",
        answers={
            "u1": Answer(
                user_id="u1",
                username="Alice",
                text="A",
                timestamp=archived_at,
            )
        },
        winners=winners,
        created_at=archived_at - timedelta(hours=1),
        archived_at=archived_at,
    )


def test_parse_winners_text_handles_common_formats() -> None:
    assert weekly_summary_service.parse_winners_text("Curly, Larry, and Moe") == [
        "Curly",
        "Larry",
        "Moe",
    ]
    assert weekly_summary_service.parse_winners_text("Alice & Bob") == ["Alice", "Bob"]


def test_parse_winners_text_handles_no_winner_inputs() -> None:
    assert weekly_summary_service.parse_winners_text("") == []
    assert weekly_summary_service.parse_winners_text("No Winners") == []
    assert weekly_summary_service.parse_winners_text("none") == []


def test_parse_schedule_string_with_ct_abbreviation() -> None:
    parsed = weekly_summary_service.parse_schedule_string("Sunday 18:00 CT")
    assert parsed.day == "sunday"
    assert parsed.time_local == "18:00"
    assert parsed.timezone_name == "America/Chicago"


def test_parse_schedule_string_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match="schedule must be in the format"):
        weekly_summary_service.parse_schedule_string("sunday-18:00-CT")


def test_calculate_next_send_at_rolls_to_next_week_when_time_passed() -> None:
    now = datetime(2026, 3, 3, 10, 30, tzinfo=timezone.utc)  # Tuesday

    next_send = weekly_summary_service.calculate_next_send_at(weekday=1, hour=10, minute=0, now=now)

    assert next_send == datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)


def test_calculate_next_send_at_uses_upcoming_weekday() -> None:
    now = datetime(2026, 3, 3, 10, 30, tzinfo=timezone.utc)  # Tuesday

    next_send = weekly_summary_service.calculate_next_send_at(weekday=4, hour=9, minute=0, now=now)

    assert next_send == datetime(2026, 3, 6, 9, 0, tzinfo=timezone.utc)


def test_create_or_update_subscription_converts_local_time_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)  # Tuesday
    saved: list[WeeklySummarySubscription] = []

    monkeypatch.setattr(
        weekly_summary_service.storage_service,
        "save_weekly_summary_subscription",
        lambda sub: saved.append(sub),
    )

    subscription = weekly_summary_service.create_or_update_subscription(
        guild_id="guild-1",
        user_id="123456789",
        day="wednesday",
        time_local="09:30",
        timezone_name="America/Chicago",
        now=now,
    )

    assert subscription.local_weekday == 2
    assert subscription.local_hour == 9
    assert subscription.local_minute == 30
    assert subscription.timezone_name == "America/Chicago"
    assert subscription.next_send_at == datetime(2026, 3, 4, 15, 30, tzinfo=timezone.utc)
    assert subscription.weekday == 2
    assert subscription.hour == 15
    assert subscription.minute == 30
    assert len(saved) == 1


def test_create_or_update_subscription_rejects_invalid_timezone() -> None:
    now = datetime(2026, 3, 3, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="timezone_name must be a valid IANA timezone"):
        weekly_summary_service.create_or_update_subscription(
            guild_id="guild-1",
            user_id="123456789",
            day="monday",
            time_local="09:30",
            timezone_name="Not/AZone",
            now=now,
        )


def test_summarize_winners_counts_each_round_once() -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    archives = [
        _archive(now - timedelta(days=1), ["Alice", "Bob", "alice"]),
        _archive(now - timedelta(days=2), ["Alice"]),
        _archive(now - timedelta(days=3), ["bob"]),
    ]

    summary = weekly_summary_service.summarize_winners_from_archives(archives)

    assert summary == [("Alice", 2), ("Bob", 2)]


def test_format_weekly_summary_message() -> None:
    start = datetime(2026, 3, 3, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 3, 10, 0, 0, tzinfo=timezone.utc)

    message = weekly_summary_service.format_weekly_summary_message(
        window_start=start,
        window_end=end,
        winner_summary=[("Fylis", 4), ("Qire", 2), ("Kilaire", 1)],
    )

    assert "Winners for date range 2026-MAR-03 to 2026-MAR-09" in message
    assert "Fylis - 4" in message
    assert "Qire - 2" in message
    assert "Kilaire - 1" in message


@pytest.mark.asyncio
async def test_process_due_subscriptions_sends_dm_and_advances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    subscription = WeeklySummarySubscription(
        guild_id="guild-1",
        user_id="123456789",
        weekday=1,
        hour=12,
        minute=0,
        next_send_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2),
    )

    archives = [
        _archive(now - timedelta(days=1), ["Alice"]),
        _archive(now - timedelta(days=2), ["Alice", "Bob"]),
    ]

    saved: list[WeeklySummarySubscription] = []

    monkeypatch.setattr(
        weekly_summary_service.storage_service,
        "load_due_weekly_summary_subscriptions",
        lambda now, limit=50: [subscription],
    )
    monkeypatch.setattr(
        weekly_summary_service.storage_service,
        "load_archived_sessions",
        lambda guild_id, limit=7: archives,
    )
    monkeypatch.setattr(
        weekly_summary_service.storage_service,
        "save_weekly_summary_subscription",
        lambda sub: saved.append(sub),
    )

    user = AsyncMock()
    user.send = AsyncMock()

    client = AsyncMock()
    client.fetch_user = AsyncMock(return_value=user)

    await weekly_summary_service.process_due_subscriptions(client, now=now)

    user.send.assert_awaited_once()
    sent_message = user.send.call_args[0][0]
    assert "Winners for date range 2026-MAR-03 to 2026-MAR-09" in sent_message
    assert "Alice - 2" in sent_message
    assert "Bob - 1" in sent_message

    assert len(saved) == 1
    assert saved[0].next_send_at > now
