"""Main Discord bot entry point for the Trivia Bot."""

import logging
import os
import signal
import sys
from typing import NoReturn

import discord
from discord import app_commands
from dotenv import load_dotenv

# Add parent directory to path to allow imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services import answer_service, storage_service
from src.commands.list_answers import list_answers_command
from src.commands.post_question import post_question_command, AnswerButton

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Bot configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_TEST_GUILD_ID = os.getenv("DISCORD_TEST_GUILD_ID")  # Optional: for faster testing

if not DISCORD_BOT_TOKEN:
    logger.error("DISCORD_BOT_TOKEN not found in environment variables")
    print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables")
    print("Please create a .env file with your bot token (see .env.example)")
    sys.exit(1)

# Discord client with intents
intents = discord.Intents.default()
intents.message_content = True  # Required for slash commands

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Register commands
tree.add_command(list_answers_command)
tree.add_command(post_question_command)


@client.event
async def on_ready() -> None:
    """Called when the bot successfully connects to Discord."""
    user_info = f"{client.user} (ID: {client.user.id})" if client.user else "Unknown"
    logger.info(f"Logged in as {user_info}")
    print(f"✅ Logged in as {user_info}")
    print("---")

    # Register persistent views for buttons (must be done on every startup)
    client.add_view(AnswerButton())
    logger.info("Registered persistent views")
    print("🔘 Registered persistent views")

    # Load all sessions from disk into memory
    try:
        sessions = storage_service.load_all_sessions()
        answer_service.load_sessions(sessions)
        logger.info(f"Loaded {len(sessions)} session(s) from disk")
        print(f"📂 Loaded {len(sessions)} session(s) from disk")
    except Exception as e:
        logger.error(f"Failed to load sessions from disk: {e}", exc_info=True)
        print(f"⚠️  Warning: Failed to load sessions from disk: {e}")

    # Sync slash commands with Discord
    try:
        if DISCORD_TEST_GUILD_ID:
            # Sync to test guild only (instant, for development)
            guild = discord.Object(id=int(DISCORD_TEST_GUILD_ID))
            tree.copy_global_to(guild=guild)
            synced = await tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} command(s) to test guild {DISCORD_TEST_GUILD_ID}")
            print(f"🔄 Synced {len(synced)} command(s) to test guild (dev mode)")
        else:
            # Sync globally (takes up to 1 hour to propagate)
            synced = await tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally")
            print(f"🔄 Synced {len(synced)} command(s) globally")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}", exc_info=True)
        print(f"❌ Failed to sync commands: {e}")

    logger.info("Bot is ready!")
    print("🎮 Bot is ready!")


@tree.error


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Global error handler for all slash commands.

    Args:
        interaction: Discord interaction object
        error: Error that occurred
    """
    logger.error(f"Command error in {interaction.command.name if interaction.command else 'unknown'}: {error}", exc_info=True)

    # Handle specific error types
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You don't have permission to use this command"
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"❌ This command is on cooldown. Try again in {error.retry_after:.1f}s"
    else:
        message = "❌ Something went wrong, please try again"

    # Send error message
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}", exc_info=True)


def graceful_shutdown(signum: int, frame: object) -> NoReturn:
    """Handle graceful shutdown on SIGTERM/SIGINT.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    print(f"\n🛑 Received signal {signum}, shutting down gracefully...")

    # Save all sessions to disk
    try:
        sessions = answer_service.get_all_sessions()
        for guild_id, session in sessions.items():
            storage_service.save_session_to_disk(guild_id, session)
        logger.info(f"Saved {len(sessions)} session(s) to disk")
        print(f"💾 Saved {len(sessions)} session(s) to disk")
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}", exc_info=True)
        print(f"⚠️  Warning: Failed to save sessions: {e}")

    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)


def main() -> None:
    """Main entry point for the bot."""
    logger.info("Starting Discord Trivia Bot...")
    print("🤖 Starting Discord Trivia Bot...")
    print(f"🐍 Python version: {sys.version}")
    print(f"📦 discord.py version: {discord.__version__}")

    try:
        client.run(DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.error("Failed to log in: Invalid token")
        print("❌ Failed to log in: Invalid token")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
