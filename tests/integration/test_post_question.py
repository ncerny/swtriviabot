"""Integration tests for post_question command and modals."""

import pytest
from unittest.mock import AsyncMock, Mock, MagicMock, patch
from datetime import datetime, timezone
import discord

from src.commands.post_question import (
    post_question_command,
    PostQuestionModal,
    AnswerModal,
    AnswerButton,
)
from src.services import answer_service, storage_service
from src.models.session import TriviaSession
from src.models.answer import Answer
from src.models.archived_session import ArchivedSession


@pytest.mark.asyncio
async def test_post_question_command_success(mock_interaction, tmp_path):
    """Test /post-question command opens modal successfully."""
    storage_service.DATA_DIR = tmp_path

    await post_question_command.callback(mock_interaction)

    # Verify modal was sent
    mock_interaction.response.send_modal.assert_called_once()
    modal = mock_interaction.response.send_modal.call_args[0][0]
    assert isinstance(modal, PostQuestionModal)


@pytest.mark.asyncio
async def test_post_question_command_dm_rejected(mock_interaction):
    """Test that /post-question cannot be used in DMs."""
    mock_interaction.guild_id = None

    await post_question_command.callback(mock_interaction)

    # Verify DM rejection message
    call_args = mock_interaction.response.send_message.call_args
    assert "can only be used in a server" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_post_question_command_sends_modal_immediately(mock_interaction):
    """Test that modal is sent immediately without checking permissions first.

    This prevents interaction timeout when GIFs or attachments are present.
    Permission checks are deferred to modal submission.
    """
    await post_question_command.callback(mock_interaction)

    # Verify modal was sent immediately
    mock_interaction.response.send_modal.assert_called_once()
    modal = mock_interaction.response.send_modal.call_args[0][0]
    assert isinstance(modal, PostQuestionModal)

    # Verify no permission checks happened in command handler
    assert not mock_interaction.channel.permissions_for.called


@pytest.mark.asyncio
async def test_post_question_modal_checks_send_permission(mock_interaction, mock_channel, tmp_path):
    """Test that modal submission checks for send message permission."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)

    # Mock insufficient permissions
    bot_permissions = Mock()
    bot_permissions.send_messages = False
    bot_permissions.embed_links = True
    mock_channel.permissions_for = Mock(return_value=bot_permissions)

    # Create modal
    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    modal.yesterday_answer = Mock()
    modal.yesterday_answer.value = ""
    modal.yesterday_winners = Mock()
    modal.yesterday_winners.value = ""
    modal.todays_question = Mock()
    modal.todays_question.value = "Test question"
    modal.image_url = Mock()
    modal.image_url.value = ""

    await modal.on_submit(mock_interaction)

    # Verify permission error was sent via followup
    followup_call = mock_interaction.followup.send.call_args
    assert "don't have permission to send messages" in followup_call[0][0]
    assert followup_call[1]["ephemeral"] is True

    # Verify question was NOT posted
    mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_post_question_modal_checks_embed_permission(
    mock_interaction, mock_channel, tmp_path
):
    """Test that modal submission checks for embed links permission."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)

    # Mock insufficient permissions
    bot_permissions = Mock()
    bot_permissions.send_messages = True
    bot_permissions.embed_links = False
    mock_channel.permissions_for = Mock(return_value=bot_permissions)

    # Create modal
    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    modal.yesterday_answer = Mock()
    modal.yesterday_answer.value = ""
    modal.yesterday_winners = Mock()
    modal.yesterday_winners.value = ""
    modal.todays_question = Mock()
    modal.todays_question.value = "Test question"
    modal.image_url = Mock()
    modal.image_url.value = ""

    await modal.on_submit(mock_interaction)

    # Verify permission error was sent via followup
    followup_call = mock_interaction.followup.send.call_args
    assert "don't have permission to embed links" in followup_call[0][0]
    assert followup_call[1]["ephemeral"] is True

    # Verify question was NOT posted
    mock_channel.send.assert_not_called()


@pytest.mark.asyncio
async def test_post_question_modal_submit_with_previous_answers(mock_interaction, mock_channel):
    """Test posting question with previous answers."""
    guild_id = str(mock_interaction.guild_id)

    with patch("src.services.answer_service.storage_service") as mock_storage:
        # Create previous session
        from src.models.session import TriviaSession

        session = TriviaSession(guild_id=guild_id)

        # Mock storage to return the session when loading
        mock_storage.load_session.return_value = session

        # Now submit answers (which will use the mocked session)
        answer_service.submit_answer(guild_id, "user1", "User1", "Previous answer 1")
        answer_service.submit_answer(guild_id, "user2", "User2", "Previous answer 2")

        # Create modal and mock the TextInput values
        modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)

        # Mock the TextInput attributes to have values
        modal.yesterday_answer = Mock()
        modal.yesterday_answer.value = "Coffee Ice Cream"
        modal.yesterday_winners = Mock()
        modal.yesterday_winners.value = "Player1, Player2"
        modal.todays_question = Mock()
        modal.todays_question.value = "What is the capital of France?"

        # Mock image attachment waiting to return None (no image)
        with patch.object(modal, "_wait_for_image_attachment", return_value=None):
            await modal.on_submit(mock_interaction)

        # Verify session was reset (delete was called)
        mock_storage.delete_session.assert_called_once_with(guild_id)

        # Verify new session was created (save was called)
        assert mock_storage.save_session.called

        # Verify question was posted to channel
        mock_channel.send.assert_called_once()
        call_args = mock_channel.send.call_args
        assert "content" in call_args[1]
        assert "view" in call_args[1]

        # Verify admin received previous answers
        followup_call = mock_interaction.followup.send.call_args
        assert "Previous Session Answers" in followup_call[0][0]
        assert "User1" in followup_call[0][0]
        assert "User2" in followup_call[0][0]


@pytest.mark.asyncio
async def test_post_question_modal_submit_no_previous_answers(
    mock_interaction, mock_channel, tmp_path
):
    """Test posting question with no previous answers."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)

    # Ensure no previous session
    answer_service.reset_session(guild_id)

    # Create modal and mock values
    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    modal.yesterday_answer = Mock()
    modal.yesterday_answer.value = "Coffee Ice Cream"
    modal.yesterday_winners = Mock()
    modal.yesterday_winners.value = ""
    modal.todays_question = Mock()
    modal.todays_question.value = "What is the capital of France?"

    # Mock image attachment waiting to return None (no image)
    with patch.object(modal, "_wait_for_image_attachment", return_value=None):
        await modal.on_submit(mock_interaction)

    # Verify question was posted
    mock_channel.send.assert_called_once()

    # Verify admin message indicates no previous answers
    followup_call = mock_interaction.followup.send.call_args
    assert "No previous answers to display" in followup_call[0][0]


# Removed: test_post_question_modal_with_image - modal no longer processes image URLs


@pytest.mark.asyncio
async def test_post_question_modal_no_winners_message(mock_interaction, mock_channel, tmp_path):
    """Test that 'no winners' shows appropriate message."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)

    # Create modal
    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    modal.yesterday_answer = Mock()
    modal.yesterday_answer.value = "Test Answer"
    modal.yesterday_winners = Mock()
    modal.yesterday_winners.value = "No Winners"  # Should trigger no winners message
    modal.todays_question = Mock()
    modal.todays_question.value = "Test Question"

    await modal.on_submit(mock_interaction)

    # Verify message contains "no winners" text
    call_args = mock_channel.send.call_args
    content = call_args[1]["content"]
    assert "no winners" in content.lower()


@pytest.mark.asyncio
async def test_answer_modal_submit_new_answer(mock_interaction):
    """Test submitting a new answer via modal."""
    guild_id = "123456789"
    user_id = "987654321"
    username = "TestUser"

    with patch("src.services.answer_service.storage_service") as mock_storage:
        # Create session
        from src.models.session import TriviaSession

        session = TriviaSession(guild_id=guild_id)
        mock_storage.load_session.return_value = session

        # Create and submit modal
        modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
        modal.answer_text = Mock()
        modal.answer_text.value = "Paris"

        await modal.on_submit(mock_interaction)

        # Verify response was deferred
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)

        # Verify answer was saved to storage
        assert mock_storage.save_session.called

        # Verify success message via followup
        call_args = mock_interaction.followup.send.call_args
        assert "✅" in call_args[0][0]
        assert "recorded" in call_args[0][0]


@pytest.mark.asyncio
async def test_answer_modal_update_existing_answer(mock_interaction):
    """Test updating an existing answer via modal."""
    guild_id = "123456789"
    user_id = "987654321"
    username = "TestUser"

    with patch("src.services.answer_service.storage_service") as mock_storage:
        # Create session
        from src.models.session import TriviaSession

        session = TriviaSession(guild_id=guild_id)

        # Mock storage to return the session when loading
        mock_storage.load_session.return_value = session

        # Submit initial answer (which will use the mocked session)
        answer_service.submit_answer(guild_id, user_id, username, "First answer")

        # Update with modal
        modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
        modal.answer_text = Mock()
        modal.answer_text.value = "Updated answer"

        await modal.on_submit(mock_interaction)

        # Verify response was deferred
        mock_interaction.response.defer.assert_called_once_with(ephemeral=True)

        # Verify answer was saved
        assert mock_storage.save_session.called

        # Verify update message via followup
        call_args = mock_interaction.followup.send.call_args
        assert "🔄" in call_args[0][0]
        assert "updating" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_answer_modal_validation_error(mock_interaction, tmp_path):
    """Test that validation errors are handled properly."""
    storage_service.DATA_DIR = tmp_path
    guild_id = "123456789"
    user_id = "987654321"
    username = "TestUser"

    # Create session
    answer_service.create_session(guild_id)

    # Submit empty answer (should be rejected by validator)
    modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
    modal.answer_text = Mock()
    modal.answer_text.value = "   "  # Whitespace only

    await modal.on_submit(mock_interaction)

    # Verify response was deferred
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)

    # Verify error message via followup
    call_args = mock_interaction.followup.send.call_args
    assert "❌" in call_args[0][0]
    assert call_args[1]["ephemeral"] is True


@pytest.mark.asyncio
async def test_answer_button_persistent_view():
    """Test that AnswerButton is configured as persistent view."""
    button = AnswerButton()

    # Verify timeout is None (persistent)
    assert button.timeout is None

    # Verify custom_id is set (required for persistent views)
    # Check the button in the view has a custom_id
    for item in button.children:
        if isinstance(item, discord.ui.Button):
            assert item.custom_id == "trivia:submit_answer"


class TestPostQuestionArchiveAndDM:
    """Tests for archive + DM behavior during post-question."""

    @pytest.fixture
    async def modal(self, mock_channel):
        modal = PostQuestionModal(guild_id=987654321098765432, channel=mock_channel)
        modal.yesterday_answer = MagicMock()
        modal.yesterday_answer.value = ""
        modal.yesterday_winners = MagicMock()
        modal.yesterday_winners.value = ""
        modal.todays_question = MagicMock()
        modal.todays_question.value = "New question?"
        return modal

    @patch("src.commands.post_question.answer_service")
    @patch("src.commands.post_question.storage_service")
    async def test_archives_session_before_reset(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(
            Answer(user_id="u1", username="Alice", text="answer", timestamp=now)
        )
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(guild_id="987654321098765432")

        await modal.on_submit(mock_interaction)

        mock_answer_svc.archive_session.assert_called_once_with("987654321098765432")

    @patch("src.commands.post_question.answer_service")
    @patch("src.commands.post_question.storage_service")
    async def test_dms_admin_on_archive(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(
            Answer(user_id="u1", username="Alice", text="answer", timestamp=now)
        )
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(guild_id="987654321098765432")

        mock_interaction.user.send = AsyncMock()

        await modal.on_submit(mock_interaction)

        mock_interaction.user.send.assert_called()
        dm_content = mock_interaction.user.send.call_args[0][0]
        assert "Alice" in dm_content
        assert "answer" in dm_content

    @patch("src.commands.post_question.answer_service")
    @patch("src.commands.post_question.storage_service")
    async def test_dm_failure_does_not_block_reset(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        now = datetime.now(timezone.utc)
        prev_session = TriviaSession(guild_id="987654321098765432")
        prev_session.add_or_update_answer(
            Answer(user_id="u1", username="Alice", text="answer", timestamp=now)
        )
        mock_answer_svc.get_session.return_value = prev_session

        archived = ArchivedSession(
            guild_id="987654321098765432",
            question_text="Old Q?",
            answers=prev_session.answers,
            created_at=now,
            archived_at=now,
        )
        mock_answer_svc.archive_session.return_value = archived
        mock_answer_svc.create_session.return_value = TriviaSession(guild_id="987654321098765432")

        # DM fails
        mock_interaction.user.send = AsyncMock(
            side_effect=discord.Forbidden(
                MagicMock(status=403), "Cannot send messages to this user"
            )
        )

        await modal.on_submit(mock_interaction)

        # Reset still happened
        mock_answer_svc.reset_session.assert_called_once()

    @patch("src.commands.post_question.answer_service")
    @patch("src.commands.post_question.storage_service")
    async def test_new_session_gets_question_text(
        self, mock_storage, mock_answer_svc, modal, mock_interaction
    ):
        mock_answer_svc.get_session.return_value = None
        mock_answer_svc.create_session.return_value = TriviaSession(guild_id="987654321098765432")

        await modal.on_submit(mock_interaction)

        # create_session should be called with question_text
        mock_answer_svc.create_session.assert_called_once_with(
            "987654321098765432", question_text="New question?"
        )
