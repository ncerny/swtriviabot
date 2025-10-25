"""Slash command handler for /list-answers command."""

import discord
from discord import app_commands

from src.services import answer_service


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
    await interaction.response.defer(ephemeral=True)

    try:
        # Get interaction details
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"

        # Validate guild context (no DMs)
        if guild_id == "DM":
            await interaction.followup.send(
                "❌ This command can only be used in a server, not in DMs",
                ephemeral=True,
            )
            return

        # Get session and answers
        session = answer_service.get_session(guild_id)

        if not session or not session.answers:
            await interaction.followup.send(
                "📋 No answers submitted yet",
                ephemeral=True,
            )
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

        await interaction.followup.send(formatted_message, ephemeral=True)

    except Exception as e:
        # Unexpected errors
        print(f"Error in /list-answers command: {e}")
        await interaction.followup.send(
            "❌ Something went wrong, please try again",
            ephemeral=True,
        )


@list_answers_command.error
async def list_answers_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Handle errors for /list-answers command.

    Args:
        interaction: Discord interaction object
        error: Error that occurred
    """
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command (Administrator required)",
            ephemeral=True,
        )
    else:
        print(f"Unexpected error in /list-answers: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
