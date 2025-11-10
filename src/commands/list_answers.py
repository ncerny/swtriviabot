"""Slash command handler for /list-answers command."""

import logging

import discord
from discord import app_commands

from src.services import answer_service

logger = logging.getLogger(__name__)


@app_commands.command(
    name="list-answers",
    description="View all submitted answers (Admin only)",
)
@app_commands.checks.has_permissions(administrator=True)
async def list_answers_command(interaction: discord.Interaction) -> None:
    """Handle the /list-answers slash command.

    Args:
        interaction: Discord interaction object
    """
    # Defer response to prevent timeout
    try:
        await interaction.response.defer(ephemeral=True)
    except discord.errors.InteractionResponded:
        # Already responded, can continue
        logger.warning("Interaction already responded in /list-answers")
    except Exception as e:
        logger.error(f"Failed to defer /list-answers interaction: {e}", exc_info=True)
        return

    try:
        # Get interaction details
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"

        # Validate guild context (no DMs)
        if guild_id == "DM":
            try:
                await interaction.followup.send(
                    "❌ This command can only be used in a server, not in DMs",
                    ephemeral=True,
                )
            except discord.errors.NotFound:
                logger.error("Interaction expired before DM rejection message", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to send DM rejection in /list-answers: {e}", exc_info=True)
            return

        # Get session and answers
        session = answer_service.get_session(guild_id)

        if not session or not session.answers:
            try:
                await interaction.followup.send(
                    "📋 No answers submitted yet",
                    ephemeral=True,
                )
            except discord.errors.NotFound:
                logger.error("Interaction expired before empty answers message", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to send empty answers message in /list-answers: {e}", exc_info=True)
            return

        # Format answer list to match post-question style
        answer_lines = []
        for answer in session.answers.values():
            timestamp_str = answer.timestamp.strftime("%Y-%m-%d %H:%M UTC")
            answer_lines.append(
                f"**{answer.username}** ({timestamp_str}):\n{answer.text}\n"
            )
        
        answers_text = "\n".join(answer_lines)
        
        # Truncate if too long (Discord has 2000 char limit per message)
        if len(answers_text) > 1800:
            answers_text = answers_text[:1800] + "\n\n_(truncated due to length)_"
        
        formatted_message = (
            f"📋 **Current Session Answers**\n\n"
            f"{answers_text}\n"
            f"_Total answers: {len(session.answers)}_"
        )

        try:
            await interaction.followup.send(formatted_message, ephemeral=True)
        except discord.errors.NotFound:
            logger.error("Interaction expired before sending answers", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to send answers in /list-answers: {e}", exc_info=True)

    except Exception as e:
        # Unexpected errors
        logger.error(
            f"Unexpected error in /list-answers for user {interaction.user.id}",
            exc_info=True,
            extra={
                "guild_id": interaction.guild_id,
                "channel_id": interaction.channel_id,
                "user_id": interaction.user.id
            }
        )
        try:
            await interaction.followup.send(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
        except discord.errors.NotFound:
            logger.error("Interaction expired before error message", exc_info=True)
        except Exception as followup_error:
            logger.error(f"Failed to send error message in /list-answers: {followup_error}", exc_info=True)


@list_answers_command.error
async def list_answers_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Handle errors for /list-answers command.

    Args:
        interaction: Discord interaction object
        error: Error that occurred
    """
    logger.error(
        f"Command error in /list-answers for user {interaction.user.id}: {error}",
        exc_info=True,
        extra={
            "guild_id": interaction.guild_id,
            "user_id": interaction.user.id,
            "error_type": type(error).__name__
        }
    )
    
    if isinstance(error, app_commands.MissingPermissions):
        error_message = "❌ You don't have permission to use this command (Administrator required)"
    else:
        error_message = "❌ Something went wrong, please try again"
    
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(error_message, ephemeral=True)
        else:
            await interaction.followup.send(error_message, ephemeral=True)
    except discord.errors.NotFound:
        logger.error("Interaction expired before error message could be sent", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to send error message in error handler: {e}", exc_info=True)
