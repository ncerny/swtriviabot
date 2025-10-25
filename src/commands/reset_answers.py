"""Slash command handler for /reset-answers command."""

import discord
from discord import app_commands

from src.services import answer_service, storage_service


@app_commands.command(
    name="reset-answers",
    description="Clear all answers and start a new session (Admin only)",
)
@app_commands.checks.has_permissions(administrator=True)
async def reset_answers_command(interaction: discord.Interaction) -> None:
    """Handle the /reset-answers slash command.

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

        # Reset session in memory
        answer_service.reset_session(guild_id)

        # Delete session file from disk
        storage_service.delete_session_file(guild_id)

        # Send confirmation
        await interaction.followup.send(
            "🔄 All answers have been reset - ready for next question!",
            ephemeral=True,
        )

    except Exception as e:
        # Unexpected errors
        print(f"Error in /reset-answers command: {e}")
        await interaction.followup.send(
            "❌ Something went wrong, please try again",
            ephemeral=True,
        )


@reset_answers_command.error
async def reset_answers_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Handle errors for /reset-answers command.

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
        print(f"Unexpected error in /reset-answers: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
