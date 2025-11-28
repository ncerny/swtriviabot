"""Focused unit tests for post-question helper flows."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import discord

from src.commands.post_question import (
    PostQuestionModal,
    AnswerModal,
    AnswerButton,
    post_question_command,
)
from src.services import answer_service


class DummyChannel:
    """Minimal asynchronous channel stub."""

    def __init__(self) -> None:
        self.sent: list[dict[str, object]] = []
        self._permissions = SimpleNamespace(send_messages=True, embed_links=True)

    async def send(self, content: str, **kwargs: object) -> None:
        self.sent.append({"content": content, **kwargs})

    def permissions_for(self, member: object) -> object:
        return self._permissions


class DummyMessage:
    """Message stub supporting delete/edit hooks."""

    def __init__(self) -> None:
        self.edits: list[dict[str, object]] = []
        self.deleted = False
        self.channel: object | None = None
        self.author: object | None = None
        self.embeds: list[object] = []
        self.attachments: list[object] = []
        self.content: str = ""

    async def edit(self, **kwargs: object) -> None:
        self.edits.append(kwargs)

    async def delete(self) -> None:
        self.deleted = True


class FakeClient:
    """Client stub returning a prepared message."""

    def __init__(self, message) -> None:
        self._message = message

    async def wait_for(self, event: str, timeout: float, check) -> object:  # noqa: D401 - follows Discord signature
        assert event == "message"
        assert check(self._message)
        return self._message


def _build_message(
    *,
    channel: DummyChannel,
    author: object,
    embeds: list[object] | None = None,
    attachments: list[object] | None = None,
    content: str = "",
) -> DummyMessage:
    message = DummyMessage()
    message.channel = channel
    message.author = author
    message.embeds = embeds or []
    message.attachments = attachments or []
    message.content = content
    return message


@pytest.mark.asyncio
async def test_watch_for_image_and_edit_updates_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """Background watcher edits the question message when an image arrives."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=123, channel=cast(discord.TextChannel, channel))
    expected_embed = discord.Embed(title="Image")

    modal._wait_for_image_attachment = AsyncMock(return_value=expected_embed)
    message = DummyMessage()

    await modal._watch_for_image_and_edit(cast(discord.Message, message), timeout=1.0)

    modal._wait_for_image_attachment.assert_awaited_once_with(timeout=1.0)
    assert message.edits == [{"embed": expected_embed}]


@pytest.mark.asyncio
async def test_wait_for_image_attachment_handles_tenor_embed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Embedded Tenor links are resolved to GIF embeds."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=123, channel=cast(discord.TextChannel, channel))
    user = object()

    resolved_embed = discord.Embed(title="Resolved")
    modal._resolve_tenor_url = AsyncMock(return_value=resolved_embed)

    embed_stub = SimpleNamespace(
        type="gifv",
        url="https://tenor.com/view/test-12345",
        image=None,
        video=None,
        title=None,
        description=None,
        thumbnail=None,
        footer=None,
    )

    message = _build_message(channel=channel, author=user, embeds=[embed_stub])
    modal.interaction = cast(discord.Interaction, SimpleNamespace(client=FakeClient(message), user=user))

    result = await modal._wait_for_image_attachment(timeout=5.0)

    assert result is resolved_embed
    assert message.deleted


@pytest.mark.asyncio
async def test_wait_for_image_attachment_copies_embed_metadata() -> None:
    """Non-Tenor embeds are copied with metadata preserved."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=222, channel=cast(discord.TextChannel, channel))
    user = object()

    embed_stub = SimpleNamespace(
        type="image",
        url=None,
        image=SimpleNamespace(url="https://example.com/pic.png"),
        video=None,
        title="Picture",
        description="Description",
        thumbnail=SimpleNamespace(url="https://example.com/thumb.png"),
        footer=SimpleNamespace(text="Footer", icon_url="https://example.com/icon.png"),
    )

    message = _build_message(channel=channel, author=user, embeds=[embed_stub])
    modal.interaction = cast(discord.Interaction, SimpleNamespace(client=FakeClient(message), user=user))

    result = await modal._wait_for_image_attachment(timeout=2.0)

    assert isinstance(result, discord.Embed)
    assert result.title == "Picture"
    assert result.description == "Description"
    assert result.image.url == "https://example.com/pic.png"
    assert result.thumbnail.url == "https://example.com/thumb.png"
    assert result.footer.text == "Footer"
    assert result.footer.icon_url == "https://example.com/icon.png"
    assert message.deleted


@pytest.mark.asyncio
async def test_wait_for_image_attachment_handles_attachment() -> None:
    """Image attachments are converted to embeds."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=321, channel=cast(discord.TextChannel, channel))
    user = object()

    attachment = SimpleNamespace(content_type="image/png", url="https://example.com/image.png")
    message = _build_message(channel=channel, author=user, attachments=[attachment])
    modal.interaction = cast(discord.Interaction, SimpleNamespace(client=FakeClient(message), user=user))

    embed = await modal._wait_for_image_attachment(timeout=2.0)

    assert isinstance(embed, discord.Embed)
    assert embed.image.url == "https://example.com/image.png"
    assert message.deleted


@pytest.mark.asyncio
async def test_wait_for_image_attachment_validates_direct_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct URLs are validated via image_service helper."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=456, channel=cast(discord.TextChannel, channel))
    user = object()

    returned_embed = discord.Embed(title="Validated")
    validate_mock = AsyncMock(return_value=(True, returned_embed))
    monkeypatch.setattr("src.services.image_service.validate_image_url", validate_mock)

    message = _build_message(
        channel=channel,
        author=user,
        content="Check this out https://example.com/image.png",
    )
    modal.interaction = cast(discord.Interaction, SimpleNamespace(client=FakeClient(message), user=user))

    result = await modal._wait_for_image_attachment(timeout=2.0)

    assert result is returned_embed
    validate_mock.assert_awaited_once()
    assert message.deleted


@pytest.mark.asyncio
async def test_wait_for_image_attachment_reports_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validation errors surface to the channel and return None."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=654, channel=cast(discord.TextChannel, channel))
    user = object()

    validate_mock = AsyncMock(return_value=(False, "Bad image"))
    monkeypatch.setattr("src.services.image_service.validate_image_url", validate_mock)

    message = _build_message(
        channel=channel,
        author=user,
        content="https://example.com/not-image",
    )
    modal.interaction = cast(discord.Interaction, SimpleNamespace(client=FakeClient(message), user=user))

    result = await modal._wait_for_image_attachment(timeout=2.0)

    assert result is None
    assert channel.sent and "Image Error" in str(channel.sent[0]["content"])
    validate_mock.assert_awaited_once()
    assert message.deleted


@pytest.mark.asyncio
async def test_resolve_tenor_url_fetches_gif(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valid Tenor URLs produce embeds with the resolved GIF URL."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=777, channel=cast(discord.TextChannel, channel))

    class _FakeResponse:
        status = 200

        async def json(self):
            return {
                "results": [
                    {
                        "media_formats": {
                            "gif": {"url": "https://media.tenor.com/abc123.gif"}
                        }
                    }
                ]
            }

        async def text(self):  # pragma: no cover - not triggered in success case
            return ""

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _FakeSession:
        def __init__(self, *args, **kwargs):
            self.recorded = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        def get(self, url: str, params: dict[str, str]):
            self.recorded = (url, params)
            return _FakeResponse()

    monkeypatch.setattr("src.commands.post_question.aiohttp.ClientSession", _FakeSession)
    monkeypatch.setenv("TENOR_API_KEY", "test-key")

    embed = await modal._resolve_tenor_url("https://tenor.com/view/test-slug-987654")

    assert embed is not None
    assert embed.image.url == "https://media.tenor.com/abc123.gif"


@pytest.mark.asyncio
async def test_resolve_tenor_url_handles_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without an API key the resolver returns None."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=888, channel=cast(discord.TextChannel, channel))

    monkeypatch.delenv("TENOR_API_KEY", raising=False)

    result = await modal._resolve_tenor_url("https://tenor.com/view/example-123")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_tenor_url_invalid_link(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected Tenor URLs that lack an ID return None."""

    channel = DummyChannel()
    modal = PostQuestionModal(guild_id=999, channel=cast(discord.TextChannel, channel))

    monkeypatch.setenv("TENOR_API_KEY", "present")

    result = await modal._resolve_tenor_url("https://tenor.com/no-id-here")
    assert result is None


async def _invoke_post_question_command(interaction: discord.Interaction) -> None:
    await post_question_command.callback(interaction)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_post_question_modal_handles_already_responded(mock_interaction, mock_channel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Modal continues after an InteractionResponded defer warning."""

    guild_id = mock_interaction.guild_id
    mock_interaction.guild.me = Mock()
    mock_interaction.response.defer.side_effect = discord.errors.InteractionResponded(Mock())
    mock_interaction.followup.send = AsyncMock()
    mock_channel.send = AsyncMock(return_value=Mock())

    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    for field_name, value in (
        ("yesterday_answer", ""),
        ("yesterday_winners", ""),
        ("todays_question", "What is the capital of Spain?"),
    ):
        field = Mock()
        field.value = value
        setattr(modal, field_name, field)

    watch_mock = AsyncMock()
    monkeypatch.setattr(modal, "_watch_for_image_and_edit", watch_mock)
    monkeypatch.setattr("src.commands.post_question.storage_service.save_session", lambda *args, **kwargs: None)

    await modal.on_submit(mock_interaction)
    await asyncio.sleep(0)

    assert mock_interaction.followup.send.await_count >= 1
    assert watch_mock.await_count == 1


@pytest.mark.asyncio
async def test_post_question_modal_handles_channel_send_error(mock_interaction, mock_channel, monkeypatch: pytest.MonkeyPatch) -> None:
    """Channel send failures fall back to error messaging."""

    guild_id = mock_interaction.guild_id
    mock_interaction.guild.me = Mock()
    mock_interaction.followup.send = AsyncMock()
    mock_channel.send = AsyncMock(side_effect=RuntimeError("send failure"))

    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    for field_name, value in (
        ("yesterday_answer", ""),
        ("yesterday_winners", ""),
        ("todays_question", "Question text"),
    ):
        field = Mock()
        field.value = value
        setattr(modal, field_name, field)

    monkeypatch.setattr("src.commands.post_question.storage_service.save_session", lambda *args, **kwargs: None)
    monkeypatch.setattr(modal, "_watch_for_image_and_edit", AsyncMock())

    await modal.on_submit(mock_interaction)

    # One followup for confirmation, one for the error fallback
    assert mock_interaction.followup.send.await_count >= 2


@pytest.mark.asyncio
async def test_answer_modal_handles_interaction_responded(mock_interaction, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer modal tolerates deferred interactions already being finished."""

    guild_id = "guild-1"
    answer_service.create_session(guild_id)

    modal = AnswerModal(guild_id=guild_id, user_id="user", username="User")
    modal.answer_text = Mock()
    modal.answer_text.value = "Answer"

    mock_interaction.response.defer.side_effect = discord.errors.InteractionResponded(Mock())
    mock_interaction.followup.send = AsyncMock()

    monkeypatch.setattr("src.commands.post_question.storage_service.save_session", lambda *args, **kwargs: None)

    await modal.on_submit(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_answer_modal_followup_not_found(mock_interaction, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Followup sending errors inside AnswerModal are handled."""

    guild_id = "guild-2"
    answer_service.create_session(guild_id)

    modal = AnswerModal(guild_id=guild_id, user_id="user", username="User")
    modal.answer_text = Mock()
    modal.answer_text.value = "Another"

    mock_interaction.followup.send = AsyncMock(side_effect=discord.errors.NotFound(Mock(), "expired"))
    monkeypatch.setattr("src.commands.post_question.storage_service.save_session", lambda *args, **kwargs: None)

    await modal.on_submit(mock_interaction)

    assert mock_interaction.followup.send.await_count == 1


@pytest.mark.asyncio
async def test_answer_button_error_fallback(mock_interaction, monkeypatch: pytest.MonkeyPatch) -> None:
    """Button error path sends a followup when modal invocation fails."""

    guild_id = str(mock_interaction.guild_id)
    answer_service.create_session(guild_id)

    mock_interaction.response.send_modal.side_effect = RuntimeError("modal failure")
    mock_interaction.response.is_done = Mock(return_value=False)
    mock_interaction.response.send_message = AsyncMock()
    mock_interaction.followup.send = AsyncMock()

    view = AnswerButton()
    button_component = next(item for item in view.children if isinstance(item, discord.ui.Button))

    await button_component.callback(mock_interaction)  # type: ignore[arg-type]

    assert mock_interaction.response.send_message.await_count == 1


@pytest.mark.asyncio
async def test_post_question_command_error_flow(mock_interaction, monkeypatch: pytest.MonkeyPatch) -> None:
    """Command level errors fall back to a followup response when required."""

    mock_interaction.response.send_modal.side_effect = RuntimeError("modal failure")
    mock_interaction.response.is_done = Mock(return_value=False)
    mock_interaction.response.send_message = AsyncMock()

    await _invoke_post_question_command(mock_interaction)

    assert mock_interaction.response.send_message.await_count == 1