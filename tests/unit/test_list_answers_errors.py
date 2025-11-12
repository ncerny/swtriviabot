"""Additional coverage for list-answers command error handling."""

from unittest.mock import AsyncMock, Mock

import pytest
import discord
from discord import app_commands

import src.commands.list_answers as list_answers_module
from src.commands.list_answers import list_answers_command, list_answers_error
from src.services import answer_service


def _not_found() -> discord.errors.NotFound:
    return discord.errors.NotFound(Mock(), "expired interaction")


async def _invoke(interaction: discord.Interaction) -> None:
    await list_answers_command.callback(interaction)  # type: ignore[arg-type]


async def _invoke_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    await list_answers_error(interaction, error)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_list_answers_defer_already_responded(mock_interaction):
    mock_interaction.response.defer.side_effect = discord.errors.InteractionResponded(Mock())

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_defer_failure_returns_early(mock_interaction):
    mock_interaction.response.defer.side_effect = RuntimeError("boom")

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 0


@pytest.mark.asyncio
async def test_list_answers_dm_not_found(mock_interaction):
    mock_interaction.guild_id = None
    mock_interaction.followup.send.side_effect = _not_found()

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_dm_generic_error(mock_interaction):
    mock_interaction.guild_id = None
    mock_interaction.followup.send.side_effect = RuntimeError("send failure")

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_no_answers_not_found(mock_interaction):
    mock_interaction.followup.send.side_effect = _not_found()

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_no_answers_generic_error(mock_interaction):
    mock_interaction.followup.send.side_effect = RuntimeError("send failure")

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_answers_not_found(mock_interaction):
    guild_id = str(mock_interaction.guild_id)
    answer_service.submit_answer(guild_id, "user", "Name", "Answer")
    mock_interaction.followup.send = AsyncMock(side_effect=_not_found())

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_unexpected_error_followup_not_found(mock_interaction, monkeypatch):
    def _raise(_guild_id):
        raise RuntimeError("failure")

    monkeypatch.setattr(list_answers_module.answer_service, "get_session", _raise)
    mock_interaction.followup.send.side_effect = _not_found()

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_unexpected_error_followup_generic(mock_interaction, monkeypatch):
    def _raise(_guild_id):
        raise RuntimeError("failure")

    monkeypatch.setattr(list_answers_module.answer_service, "get_session", _raise)
    mock_interaction.followup.send.side_effect = RuntimeError("send failure")

    await _invoke(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_error_handler_not_found_before_response(mock_interaction):
    mock_interaction.response.is_done.return_value = False
    mock_interaction.response.send_message.side_effect = _not_found()

    mock_interaction.response.is_done = Mock(return_value=False)
    mock_interaction.response.send_message = AsyncMock(side_effect=_not_found())

    await _invoke_error(mock_interaction, app_commands.AppCommandError("oops"))

    assert mock_interaction.response.send_message.await_count == 1


@pytest.mark.asyncio
async def test_list_answers_error_handler_not_found_after_response(mock_interaction):
    mock_interaction.response.is_done = Mock(return_value=True)
    mock_interaction.followup.send.side_effect = _not_found()

    await _invoke_error(mock_interaction, app_commands.AppCommandError("oops"))

    assert mock_interaction.followup.send.await_count == 1