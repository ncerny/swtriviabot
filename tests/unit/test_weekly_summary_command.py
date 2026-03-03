"""Unit tests for /weekly-summary-subscribe command."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from discord import app_commands

from src.commands.weekly_summary import (
    weekly_summary_subscribe_command,
    weekly_summary_subscribe_error,
)
from src.models.weekly_summary_subscription import WeeklySummarySubscription


async def _invoke(interaction, schedule: str) -> None:
    await weekly_summary_subscribe_command.callback(  # type: ignore[arg-type]
        interaction,
        schedule=schedule,
    )


@pytest.mark.asyncio
async def test_weekly_summary_subscribe_rejects_dm(mock_interaction) -> None:
    mock_interaction.guild_id = None
    mock_interaction.response.send_message = AsyncMock()

    await _invoke(mock_interaction, schedule="Monday 09:30 CT")

    mock_interaction.response.send_message.assert_awaited_once()
    sent = mock_interaction.response.send_message.call_args[0][0]
    assert "only be used in a server" in sent


@pytest.mark.asyncio
async def test_weekly_summary_subscribe_invalid_time_shows_error(
    mock_interaction, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise(**_kwargs):
        raise ValueError("schedule must be in the format")

    monkeypatch.setattr(
        "src.commands.weekly_summary.weekly_summary_service.create_or_update_subscription_from_schedule",
        _raise,
    )

    mock_interaction.response.send_message = AsyncMock()

    await _invoke(mock_interaction, schedule="monday-99:99-CT")

    mock_interaction.response.send_message.assert_awaited_once()
    sent = mock_interaction.response.send_message.call_args[0][0]
    assert "format" in sent


@pytest.mark.asyncio
async def test_weekly_summary_subscribe_success(
    mock_interaction, monkeypatch: pytest.MonkeyPatch
) -> None:
    next_send = datetime(2026, 3, 9, 9, 30, tzinfo=timezone.utc)
    subscription = WeeklySummarySubscription(
        guild_id=str(mock_interaction.guild_id),
        user_id=str(mock_interaction.user.id),
        weekday=0,
        hour=15,
        minute=30,
        next_send_at=next_send,
        created_at=next_send,
        updated_at=next_send,
        timezone_name="America/Chicago",
        local_weekday=0,
        local_hour=9,
        local_minute=30,
    )

    monkeypatch.setattr(
        "src.commands.weekly_summary.weekly_summary_service.create_or_update_subscription_from_schedule",
        lambda **_kwargs: subscription,
    )

    mock_interaction.response.send_message = AsyncMock()

    await _invoke(mock_interaction, schedule="Monday 09:30 CT")

    mock_interaction.response.send_message.assert_awaited_once()
    sent = mock_interaction.response.send_message.call_args[0][0]
    assert "Weekly summary subscription saved" in sent
    assert "Monday" in sent
    assert "09:30 America/Chicago" in sent
    assert "15:30 UTC" in sent


@pytest.mark.asyncio
async def test_weekly_summary_subscribe_permission_error_handler(mock_interaction) -> None:
    mock_interaction.response.is_done = Mock(return_value=False)
    mock_interaction.response.send_message = AsyncMock()

    await weekly_summary_subscribe_error(
        mock_interaction,
        app_commands.MissingPermissions(["administrator"]),
    )

    mock_interaction.response.send_message.assert_awaited_once()
    sent = mock_interaction.response.send_message.call_args[0][0]
    assert "Administrator required" in sent
