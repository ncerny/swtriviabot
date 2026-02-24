"""Main Discord bot entry point for the Trivia Bot."""

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import NoReturn

import discord
from discord import app_commands
from dotenv import load_dotenv

# Add parent directory to path to allow imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file in project root
# CRITICAL: Load this BEFORE importing any services that read env vars
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Verify .env was loaded (for debugging)
import os
_dev_mode_check = os.getenv("DEV_MODE", "not_set")
print(f"[STARTUP] .env file path: {env_path}")
print(f"[STARTUP] .env file exists: {env_path.exists()}")
print(f"[STARTUP] DEV_MODE from environment: '{_dev_mode_check}'")

from src.services import answer_service, storage_service
from src.commands.list_answers import list_answers_command
from src.commands.post_question import post_question_command, AnswerButton
from src.utils.performance import get_metrics
from src.utils.resource_monitor import get_resource_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Bot configuration - read after .env is loaded
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_TEST_GUILD_ID = os.getenv("DISCORD_TEST_GUILD_ID")
BOT_INSTANCE_ID = os.getenv("BOT_INSTANCE_ID", str(uuid.uuid4()))
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
LEADER_ELECTION_ENABLED = os.getenv("LEADER_ELECTION_ENABLED", "true").lower() == "true"


if not DISCORD_BOT_TOKEN:
    logger.error("DISCORD_BOT_TOKEN not found in environment variables")
    sys.exit(1)

# Discord client
intents = discord.Intents.none()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Register commands
tree.add_command(list_answers_command)
tree.add_command(post_question_command)

# Leader Election Globals
HEARTBEAT_INTERVAL = 10  # Seconds
LOCK_EXPIRY = 30  # Seconds
HEARTBEAT_MAX_FAILURES = 3  # Consecutive failures before SIGTERM
_heartbeat_stop_event = threading.Event()


def _get_firestore_db():
    # Helper to get DB from storage service (which initializes it)
    # We access the protected member for direct DB access for locking
    return storage_service._get_db()


def acquire_lock() -> bool:
    """Try to acquire the leader lock."""
    db = _get_firestore_db()
    if not db:
        return False

    # Use the same collection suffix as storage_service for isolation
    from src.services.storage_service import COLLECTION_SUFFIX
    collection_name = f"bot_status{COLLECTION_SUFFIX}"
    lock_ref = db.collection(collection_name).document("leader")
    
    logger.debug(f"Attempting to acquire lock from collection: {collection_name}")
    
    try:
        from firebase_admin import firestore
        from datetime import timedelta

        # Transactional lock acquisition
        @firestore.transactional
        def update_in_transaction(transaction, ref):
            snapshot = ref.get(transaction=transaction)
            now = datetime.now(timezone.utc)
            
            if snapshot.exists:
                data = snapshot.to_dict()
                expires_at = data.get("expires_at")
                current_leader = data.get("instance_id")
                
                # If lock is held by us, refresh it
                if current_leader == BOT_INSTANCE_ID:
                    transaction.update(ref, {
                        "expires_at": now + timedelta(seconds=LOCK_EXPIRY)
                    })
                    return True
                
                # If lock is valid and not us, fail
                if expires_at:
                    # Convert Firestore timestamp to datetime if needed
                    # Firestore SDK usually returns datetime objects
                    if expires_at > now:
                        return False

            # Lock is free or expired, take it
            transaction.set(ref, {
                "instance_id": BOT_INSTANCE_ID,
                "expires_at": now + timedelta(seconds=LOCK_EXPIRY),
                "acquired_at": now
            })
            return True
        
        transaction = db.transaction()
        return update_in_transaction(transaction, lock_ref)
        
    except Exception as e:
        logger.error(f"Error acquiring lock: {e}")
        return False


def release_lock() -> None:
    """Release the leader lock."""
    db = _get_firestore_db()
    if not db:
        return

    try:
        from src.services.storage_service import COLLECTION_SUFFIX
        lock_ref = db.collection(f"bot_status{COLLECTION_SUFFIX}").document("leader")
        # Only delete if we are the owner
        doc = lock_ref.get()
        if doc.exists and doc.to_dict().get("instance_id") == BOT_INSTANCE_ID:
            lock_ref.delete()
            logger.info("Released leader lock")
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")


def heartbeat_loop() -> None:
    """Background thread to refresh lock.

    Tolerates up to HEARTBEAT_MAX_FAILURES consecutive failures before
    treating the lock as lost.  This prevents transient Firestore errors
    (e.g. expired transactions) from killing a single-instance bot.
    """
    logger.info("Starting heartbeat loop")
    consecutive_failures = 0
    while not _heartbeat_stop_event.is_set():
        if acquire_lock():
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            logger.warning(
                "Heartbeat failed to acquire lock "
                f"({consecutive_failures}/{HEARTBEAT_MAX_FAILURES})"
            )
            if consecutive_failures >= HEARTBEAT_MAX_FAILURES:
                logger.error(
                    "Lost leader lock after %d consecutive failures! Shutting down...",
                    HEARTBEAT_MAX_FAILURES,
                )
                os.kill(os.getpid(), signal.SIGTERM)
                break
        time.sleep(HEARTBEAT_INTERVAL)


def load_example_answers() -> None:
    """Load example answers from example_answers.json if in DEV_MODE and DISCORD_TEST_GUILD_ID is set.

    The guild_id from the JSON file is ignored and replaced with DISCORD_TEST_GUILD_ID.
    This ensures test data only loads into the test guild.
    """
    if not DEV_MODE:
        return

    if not DISCORD_TEST_GUILD_ID:
        logger.info("DISCORD_TEST_GUILD_ID not set, skipping example data load")
        return

    example_file = Path(__file__).parent.parent / "example_answers.json"

    if not example_file.exists():
        logger.info("No example_answers.json found, skipping example data load")
        return

    try:
        logger.info(f"📝 DEV_MODE: Loading example answers from {example_file}")

        with open(example_file, 'r') as f:
            data = json.load(f)

        # Use TriviaSession.from_dict to parse the JSON
        from src.models.session import TriviaSession
        session = TriviaSession.from_dict(data)

        # Override the guild_id with DISCORD_TEST_GUILD_ID to ensure data goes to test guild
        test_guild_id = str(DISCORD_TEST_GUILD_ID)
        session.guild_id = test_guild_id

        # Save the session using storage_service (requires guild_id and session)
        storage_service.save_session(test_guild_id, session)

        logger.info(f"✅ Loaded {len(session.answers)} example answers for test guild {test_guild_id}")

    except Exception as e:
        logger.error(f"Failed to load example answers: {e}", exc_info=True)


@client.event
async def on_ready() -> None:
    """Called when the bot successfully connects to Discord."""
    user_info = f"{client.user} (ID: {client.user.id})" if client.user else "Unknown"
    logger.info(f"Logged in as {user_info}")
    print(f"✅ Logged in as {user_info}")

    # Register persistent views
    client.add_view(AnswerButton())

    # Sync commands
    try:
        if DISCORD_TEST_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_TEST_GUILD_ID))
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            logger.info(f"Synced commands to test guild {DISCORD_TEST_GUILD_ID}")
        else:
            await tree.sync()
            logger.info("Synced commands globally")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    # Load example answers if in DEV_MODE
    load_example_answers()

    logger.info("Bot is ready!")


@client.event
async def on_interaction(interaction: discord.Interaction) -> None:
    if interaction.type == discord.InteractionType.application_command:
        interaction.extras["start_time"] = time.perf_counter()


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    logger.error(f"Command error: {error}", exc_info=True)
    try:
        msg = "❌ Something went wrong"
        if isinstance(error, app_commands.MissingPermissions):
            msg = "❌ You don't have permission"
        elif isinstance(error, app_commands.CommandOnCooldown):
            msg = f"❌ Cooldown: {error.retry_after:.1f}s"
            
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except Exception:
        pass


def graceful_shutdown(signum: int, frame: object) -> NoReturn:
    """Handle graceful shutdown."""
    logger.info(f"Received signal {signum}, shutting down...")

    # Stop heartbeat
    _heartbeat_stop_event.set()

    # Release lock (only if leader election is enabled)
    if LEADER_ELECTION_ENABLED:
        release_lock()

    sys.exit(0)


signal.signal(signal.SIGTERM, graceful_shutdown)
signal.signal(signal.SIGINT, graceful_shutdown)


def main() -> None:
    """Main entry point."""
    from src.services.storage_service import COLLECTION_SUFFIX, DEV_MODE as STORAGE_DEV_MODE
    
    mode_str = "TEST/DEV" if STORAGE_DEV_MODE else "PRODUCTION"
    logger.info(f"Starting Discord Trivia Bot (Instance: {BOT_INSTANCE_ID})")
    logger.info(f"🔧 Running in {mode_str} mode (DEV_MODE={STORAGE_DEV_MODE})")
    logger.info(f"📦 Using collection suffix: '{COLLECTION_SUFFIX}'")
    logger.info(f"📊 Collections: sessions{COLLECTION_SUFFIX}, bot_status{COLLECTION_SUFFIX}")
    
    # 1. Migrate local data if any
    try:
        storage_service.migrate_local_data()
    except Exception as e:
        logger.error(f"Migration failed: {e}")

    # 2. Leader Election (skip if disabled for single-instance deployments)
    if LEADER_ELECTION_ENABLED:
        logger.info("Entering leader election loop...")
        while True:
            if acquire_lock():
                logger.info("👑 Acquired leader lock! Starting bot...")
                break
            else:
                logger.info("💤 Standby: Leader lock held by another instance. Retrying in 15s...")
                time.sleep(15)

        # 3. Start Heartbeat
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
    else:
        logger.info("Leader election disabled, starting bot immediately")

    # 4. Run Bot
    try:
        client.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        if LEADER_ELECTION_ENABLED:
            _heartbeat_stop_event.set()
            release_lock()


if __name__ == "__main__":
    main()
