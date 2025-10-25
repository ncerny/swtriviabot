"""Unit tests for permission service."""

import pytest
from unittest.mock import Mock
import discord

from src.services.permission_service import check_admin_permission


def test_check_admin_permission_with_admin():
    """Test that admin users are correctly identified."""
    mock_interaction = Mock(spec=discord.Interaction)
    mock_guild = Mock(spec=discord.Guild)
    mock_member = Mock(spec=discord.Member)
    mock_permissions = discord.Permissions(administrator=True)
    
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member
    mock_member.guild_permissions = mock_permissions
    
    assert check_admin_permission(mock_interaction) is True


def test_check_admin_permission_without_admin():
    """Test that non-admin users are correctly identified."""
    mock_interaction = Mock(spec=discord.Interaction)
    mock_guild = Mock(spec=discord.Guild)
    mock_member = Mock(spec=discord.Member)
    mock_permissions = discord.Permissions(administrator=False)
    
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_member
    mock_member.guild_permissions = mock_permissions
    
    assert check_admin_permission(mock_interaction) is False


def test_check_admin_permission_in_dm():
    """Test that DM interactions return False."""
    mock_interaction = Mock(spec=discord.Interaction)
    mock_interaction.guild = None
    mock_interaction.user = Mock()
    
    assert check_admin_permission(mock_interaction) is False


def test_check_admin_permission_non_member():
    """Test that non-Member users return False."""
    mock_interaction = Mock(spec=discord.Interaction)
    mock_guild = Mock(spec=discord.Guild)
    mock_user = Mock(spec=discord.User)  # User, not Member
    
    mock_interaction.guild = mock_guild
    mock_interaction.user = mock_user
    
    assert check_admin_permission(mock_interaction) is False
