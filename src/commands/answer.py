"""Slash command handler for /answer command."""

import discord
from discord import app_commands

from src.services import answer_service, storage_service


@app_commands.command(
    name="answer",
    description="Submit your answer to the current trivia question",
)
@app_commands.describe(text="Your answer to the trivia question")
async def answer_command(interaction: discord.Interaction, text: str) -> None:
    """Handle the /answer slash command.

    Args:
        interaction: Discord interaction object
        text: Answer text provided by user
    """
    # Defer response to prevent timeout for longer operations
    await interaction.response.defer(ephemeral=True)

    try:
        # Get interaction details
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        user_id = str(interaction.user.id)
        username = interaction.user.display_name

        # Validate guild context (no DMs)
        if guild_id == "DM":
            await interaction.followup.send(
                "❌ This command can only be used in a server, not in DMs",
                ephemeral=True,
            )
            return

        # Submit or update answer
        answer, is_update = answer_service.submit_answer(
            guild_id=guild_id,
            user_id=user_id,
            username=username,
            text=text,
        )

        # Save session to disk
        session = answer_service.get_session(guild_id)
        if session:
            storage_service.save_session_to_disk(guild_id, session)

        # Send appropriate response
        if is_update:
            message = "🔄 You've already answered this question - updating your answer!"
        else:
            message = "✅ Your answer has been recorded!"

        await interaction.followup.send(message, ephemeral=True)

    except ValueError as e:
        # Validation errors (empty text, too long, etc.)
        await interaction.followup.send(
            f"❌ {str(e)}",
            ephemeral=True,
        )
    except Exception as e:
        # Unexpected errors
        print(f"Error in /answer command: {e}")
        await interaction.followup.send(
            "❌ Something went wrong, please try again",
            ephemeral=True,
        )
