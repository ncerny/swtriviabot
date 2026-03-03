"""Slash command handlers for weekly winner summary subscriptions."""

import logging

import discord
from discord import app_commands

from src.services import weekly_summary_service

logger = logging.getLogger(__name__)


@app_commands.command(
    name="trivia-summary-subscribe",
    description="Subscribe to a weekly DM summary of trivia winners (Admin only)",
)
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    schedule="Schedule string (example: Sunday 18:00 CT)",
)
async def weekly_summary_subscribe_command(
    interaction: discord.Interaction,
    schedule: str,
) -> None:
    """Handle /trivia-summary-subscribe command."""
    try:
        guild_id = interaction.guild_id
        if not guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server, not in DMs",
                ephemeral=True,
            )
            return

        subscription = weekly_summary_service.create_or_update_subscription_from_schedule(
            guild_id=str(guild_id),
            user_id=str(interaction.user.id),
            schedule=schedule,
        )

        day_label = weekly_summary_service.weekday_label(subscription.local_weekday)
        next_send = subscription.next_send_at.strftime("%Y-%m-%d %H:%M UTC")
        await interaction.response.send_message(
            "✅ Weekly summary subscription saved.\n"
            f"Schedule: {day_label} at {subscription.local_hour:02d}:{subscription.local_minute:02d} "
            f"{subscription.timezone_name}\n"
            f"Stored UTC schedule: {subscription.hour:02d}:{subscription.minute:02d} UTC\n"
            f"Next summary: {next_send}",
            ephemeral=True,
        )
    except ValueError as e:
        await interaction.response.send_message(f"❌ {e}", ephemeral=True)
    except Exception as e:
        logger.error(
            "Unexpected error in /trivia-summary-subscribe for user %s: %s",
            interaction.user.id,
            e,
            exc_info=True,
        )
        if interaction.response.is_done():
            await interaction.followup.send(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )


@weekly_summary_subscribe_command.error
async def weekly_summary_subscribe_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    """Handle errors for /trivia-summary-subscribe."""
    logger.error(
        "Command error in /trivia-summary-subscribe for user %s: %s",
        interaction.user.id,
        error,
        exc_info=True,
    )

    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You don't have permission to use this command (Administrator required)"
    else:
        message = "❌ Something went wrong, please try again"

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
