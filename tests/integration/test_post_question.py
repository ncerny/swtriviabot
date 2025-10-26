"""Integration tests for post_question command and modals."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import discord

from src.commands.post_question import (
    post_question_command,
    PostQuestionModal,
    AnswerModal,
    AnswerButton,
)
from src.services import answer_service, storage_service


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
async def test_post_question_modal_checks_embed_permission(mock_interaction, mock_channel, tmp_path):
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
async def test_post_question_modal_submit_with_previous_answers(mock_interaction, mock_channel, tmp_path):
    """Test posting question with previous answers."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)
    
    # Create previous session with answers
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
    modal.image_url = Mock()
    modal.image_url.value = ""
    
    await modal.on_submit(mock_interaction)
    
    # Verify session was reset
    session = answer_service.get_session(guild_id)
    assert session is not None
    assert len(session.answers) == 0  # New session, no answers yet
    
    # Verify question was posted to channel
    mock_channel.send.assert_called_once()
    call_args = mock_channel.send.call_args
    assert "embed" in call_args[1]
    assert "view" in call_args[1]
    
    # Verify admin received previous answers
    followup_call = mock_interaction.followup.send.call_args
    assert "Previous Session Answers" in followup_call[0][0]
    assert "User1" in followup_call[0][0]
    assert "User2" in followup_call[0][0]


@pytest.mark.asyncio
async def test_post_question_modal_submit_no_previous_answers(mock_interaction, mock_channel, tmp_path):
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
    modal.image_url = Mock()
    modal.image_url.value = ""
    
    await modal.on_submit(mock_interaction)
    
    # Verify question was posted
    mock_channel.send.assert_called_once()
    
    # Verify admin message indicates no previous answers
    followup_call = mock_interaction.followup.send.call_args
    assert "No previous answers to display" in followup_call[0][0]


@pytest.mark.asyncio
async def test_post_question_modal_with_image(mock_interaction, mock_channel, tmp_path):
    """Test posting question with image URL."""
    storage_service.DATA_DIR = tmp_path
    guild_id = str(mock_interaction.guild_id)
    
    # Create modal with image
    modal = PostQuestionModal(guild_id=guild_id, channel=mock_channel)
    modal.yesterday_answer = Mock()
    modal.yesterday_answer.value = ""
    modal.yesterday_winners = Mock()
    modal.yesterday_winners.value = "no winners"
    modal.todays_question = Mock()
    modal.todays_question.value = "What is this?"
    modal.image_url = Mock()
    modal.image_url.value = "https://example.com/image.png"
    
    await modal.on_submit(mock_interaction)
    
    # Verify embed has image
    call_args = mock_channel.send.call_args
    embed = call_args[1]["embed"]
    assert embed.image.url == "https://example.com/image.png"


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
    modal.image_url = Mock()
    modal.image_url.value = ""
    
    await modal.on_submit(mock_interaction)
    
    # Verify message contains "no winners" text
    call_args = mock_channel.send.call_args
    embed = call_args[1]["embed"]
    assert "no winners" in embed.description.lower()


@pytest.mark.asyncio
async def test_answer_modal_submit_new_answer(mock_interaction, tmp_path):
    """Test submitting a new answer via modal."""
    storage_service.DATA_DIR = tmp_path
    guild_id = "123456789"
    user_id = "987654321"
    username = "TestUser"
    
    # Create session
    answer_service.create_session(guild_id)
    
    # Create and submit modal
    modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
    modal.answer_text = Mock()
    modal.answer_text.value = "Paris"
    
    await modal.on_submit(mock_interaction)
    
    # Verify response was deferred
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    
    # Verify answer was recorded
    session = answer_service.get_session(guild_id)
    assert user_id in session.answers
    assert session.answers[user_id].text == "Paris"
    
    # Verify success message via followup
    call_args = mock_interaction.followup.send.call_args
    assert "✅" in call_args[0][0]
    assert "recorded" in call_args[0][0]


@pytest.mark.asyncio
async def test_answer_modal_update_existing_answer(mock_interaction, tmp_path):
    """Test updating an existing answer via modal."""
    storage_service.DATA_DIR = tmp_path
    guild_id = "123456789"
    user_id = "987654321"
    username = "TestUser"
    
    # Create session and initial answer
    answer_service.create_session(guild_id)
    answer_service.submit_answer(guild_id, user_id, username, "First answer")
    
    # Update with modal
    modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
    modal.answer_text = Mock()
    modal.answer_text.value = "Updated answer"
    
    await modal.on_submit(mock_interaction)
    
    # Verify response was deferred
    mock_interaction.response.defer.assert_called_once_with(ephemeral=True)
    
    # Verify answer was updated
    session = answer_service.get_session(guild_id)
    assert session.answers[user_id].text == "Updated answer"
    
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
async def test_add_image_button_view():
    """Test that AddImageButton view is created correctly."""
    from src.commands.post_question import AddImageButton
    mock_channel = Mock()
    
    button_view = AddImageButton(question_message_id=12345, channel=mock_channel)
    
    # Verify timeout is set (ephemeral, not persistent)
    assert button_view.timeout == 300
    
    # Verify message ID and channel are stored
    assert button_view.question_message_id == 12345
    assert button_view.channel == mock_channel


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
