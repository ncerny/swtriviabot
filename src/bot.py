"""Main Discord bot entry point for the Trivia Bot."""

import logging
import os
import signal
import sys
import time
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
# from src.commands.metrics import metrics_command  # TODO: Implement metrics command
from src.utils.performance import get_metrics
from src.utils.resource_monitor import get_resource_monitor

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

# Discord client with minimal intents for slash-command-only bot
# Use minimal intents to reduce memory usage from Discord's internal caches
intents = discord.Intents.none()
intents.guilds = True  # Required for guild context
intents.message_content = True  # Required for wait_for('message') in image attachment

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Register commands
tree.add_command(list_answers_command)
tree.add_command(post_question_command)
# tree.add_command(metrics_command)  # TODO: Implement metrics command


async def log_resource_stats_periodically() -> None:
    """Background task to log resource stats every hour."""
    import asyncio
    import gc
    await client.wait_until_ready()
    monitor = get_resource_monitor()
    
    while not client.is_closed():
        try:
            # Log cache sizes for debugging
            logger.info(
                f"Discord cache sizes: "
                f"messages={len(client.cached_messages)}, "
                f"guilds={len(client.guilds)}"
            )
            
            monitor.log_stats("periodic check")
            monitor.check_memory_threshold(warning_mb=100.0, critical_mb=120.0)
            
            # Force garbage collection to free unused memory
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
        except Exception as e:
            logger.error(f"Error logging resource stats: {e}", exc_info=True)
        
        # Wait 1 hour
        await asyncio.sleep(3600)


@client.event
async def on_ready() -> None:
    """Called when the bot successfully connects to Discord."""
    user_info = f"{client.user} (ID: {client.user.id})" if client.user else "Unknown"
    logger.info(f"Logged in as {user_info}")
    print(f"✅ Logged in as {user_info}")
    print("---")
    
    # Log initial resource usage
    monitor = get_resource_monitor()
    monitor.log_stats("startup")

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
    
    # Start periodic resource monitoring
    client.loop.create_task(log_resource_stats_periodically())


@client.event
async def on_interaction(interaction: discord.Interaction) -> None:
    """Track command performance metrics.

    Args:
        interaction: Discord interaction object
    """
    if interaction.type == discord.InteractionType.application_command:
        # Record command execution start time
        interaction.extras["start_time"] = time.perf_counter()
        interaction.extras["logged_slow"] = False  # Track if we've logged slow warning


@client.event
async def on_interaction_response(interaction: discord.Interaction) -> None:
    """Track interaction response timing to detect slow operations.

    Args:
        interaction: Discord interaction object
    """
    if "start_time" in interaction.extras and not interaction.extras.get("logged_slow", False):
        elapsed_time = time.perf_counter() - interaction.extras["start_time"]
        command_name = interaction.command.name if interaction.command else "unknown"
        
        # Warn if response took >2s (approaching Discord's 3s limit)
        if elapsed_time > 2.0:
            logger.warning(
                f"Slow interaction response for /{command_name}: {elapsed_time:.2f}s "
                f"(Discord requires <3s)"
            )
            interaction.extras["logged_slow"] = True
        
        # Record successful completion metrics
        get_metrics().record_command(command_name, elapsed_time * 1000, success=True)


@tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    """Global error handler for all slash commands.

    Args:
        interaction: Discord interaction object
        error: Error that occurred
    """
    # Record performance metrics
    if "start_time" in interaction.extras:
        elapsed_time = (time.perf_counter() - interaction.extras["start_time"]) * 1000
        command_name = interaction.command.name if interaction.command else "unknown"
        get_metrics().record_command(command_name, elapsed_time, success=False)
        
        # Log timing even on errors
        if elapsed_time > 2000:  # >2s
            logger.warning(f"Slow command before error /{command_name}: {elapsed_time/1000:.2f}s")
    
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
    
    # Log final resource usage
    monitor = get_resource_monitor()
    monitor.log_stats("shutdown")

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
