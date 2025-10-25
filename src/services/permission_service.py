"""Permission checking service for admin commands."""

import discord


def check_admin_permission(interaction: discord.Interaction) -> bool:
    """Check if the user has administrator permissions.

    Args:
        interaction: Discord interaction object

    Returns:
        True if user has administrator permission, False otherwise
    """
    # Check if in a guild (not DM)
    if not interaction.guild:
        return False

    # Check if user is a Member object with permissions
    if not isinstance(interaction.user, discord.Member):
        return False

    # Check for administrator permission
    return interaction.user.guild_permissions.administrator
