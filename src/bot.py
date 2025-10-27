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
from src.services.image_tracker import get_image_tracker
from src.commands.list_answers import list_answers_command
from src.commands.post_question import post_question_command, AnswerButton, process_image_url
# from src.commands.metrics import metrics_command  # TODO: Implement metrics command
from src.utils.performance import get_metrics

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
# tree.add_command(metrics_command)  # TODO: Implement metrics command


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


@client.event
async def on_message(message: discord.Message) -> None:
    """Monitor messages for image posts to auto-attach to questions.
    
    When a user posts a question without an image, the bot tracks it.
    If the user then posts a message with only an image within 3 minutes,
    the bot will automatically attach that image to the question and
    delete the follow-up message.
    
    Args:
        message: The message that was posted
    """
    # Skip bot messages
    if message.author.bot:
        return
    
    # Only process messages in guilds
    if not message.guild:
        return
    
    print(f"🔍 Processing message from {message.author.name} (ID: {message.author.id})")
    
    # Check if this user has a pending image upload
    image_tracker = get_image_tracker()
    print(f"🔍 Checking for pending upload: guild={message.guild.id}, user={message.author.id}")
    print(f"🔍 Total pending uploads in tracker: {image_tracker.count_pending()}")
    pending = image_tracker.get_pending(message.guild.id, message.author.id)
    
    if not pending:
        print(f"❌ No pending image upload found for user {message.author.id} in guild {message.guild.id}")
        return
    
    # Check if the pending upload has expired
    if pending.is_expired():
        image_tracker.remove_pending(message.guild.id, message.author.id)
        print(f"⏰ Expired pending image upload for user {message.author.id}")
        return
    
    print(f"📸 Found pending image upload for user {message.author.id}, checking message...")
    
    # Check if message is in the same channel as the question
    if message.channel.id != pending.channel_id:
        print(f"⚠️  Message in different channel ({message.channel.id} vs {pending.channel_id})")
        return
    
    # Check if message has attachments or embeds with images
    # Priority: attachments > message content URL > embed URLs
    image_url = None
    
    # 1. Check attachments first (preserves animation for uploaded files)
    if message.attachments:
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                image_url = attachment.url
                print(f"🖼️  Found image attachment: {attachment.filename} (animated: {attachment.content_type})")
                break
    
    # 2. If no attachment, check if message content is a direct image URL
    #    This preserves the original URL instead of Discord's embed preview
    if not image_url and message.content:
        text = message.content.strip()
        # Check if the text is a URL pointing to an image file
        if text.startswith(('http://', 'https://')) and any(text.lower().endswith(ext) for ext in ['.gif', '.png', '.jpg', '.jpeg', '.webp', '.bmp']):
            image_url = text
            print(f"🖼️  Found image URL in message text: {image_url[:100]}...")
    
    # 3. Check embeds (Discord GIF picker uses embeds with video URLs)
    if not image_url and message.embeds:
        for embed in message.embeds:
            # Discord GIF picker embeds have video field with the animated GIF
            if embed.video:
                image_url = embed.video.url
                print(f"🖼️  Found animated GIF from embed video: {image_url[:100]}...")
                break
            # Some embeds use the main URL for the GIF (Tenor)
            elif embed.url and any(embed.url.lower().endswith(ext) for ext in ['.gif', '.mp4', '.webm']):
                image_url = embed.url
                print(f"🖼️  Found animated content from embed URL: {image_url[:100]}...")
                break
            # Regular image embed
            elif embed.image:
                image_url = embed.image.url
                print(f"🖼️  Found image from embed: {image_url[:100]}...")
                break
            # Thumbnail as last resort (often static preview)
            elif embed.thumbnail:
                image_url = embed.thumbnail.url
                print(f"⚠️  Using embed thumbnail (may be static): {image_url[:100]}...")
                break
    
    # If no image found, ignore this message
    if not image_url:
        print(f"⚠️  No image found in message from user {message.author.id}")
        return
    
    # Note: We removed the "Found image in message" log since we now log at each detection point

    
    # Check if message has minimal text content (allow empty or very short messages)
    # This allows "here's the image" type messages but filters out regular conversation
    # Also allow messages where the text is just the image URL (pasted links)
    text_content = message.content.strip() if message.content else ""
    if len(text_content) > 50:
        # Allow if the text is just the image URL or a link
        if text_content != image_url and not text_content.startswith(('http://', 'https://')):
            print(f"⚠️  Message has too much text ({len(text_content)} chars), skipping auto-attach")
            return
        else:
            print(f"📝 Message has URL text ({len(text_content)} chars), but it's just a link - proceeding")

    
    try:
        # Fetch the original question message
        channel = message.guild.get_channel(pending.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            print(f"⚠️  Could not find channel {pending.channel_id}")
            image_tracker.remove_pending(message.guild.id, message.author.id)
            return
        
        question_message = await channel.fetch_message(pending.message_id)
        
        # Check if the user's message has embeds (like Discord GIF picker creates)
        # Instead of trying to modify embeds, edit the user's message to add question text  
        if message.embeds:
            user_embed = message.embeds[0]
            print(f"📎 User message has embed with video: {user_embed.video.url if user_embed.video else 'None'}")
            print(f"📋 Question message has {len(question_message.embeds)} embeds")
            
            if question_message.embeds:
                question_embed = question_message.embeds[0]
                print(f"✅ Both messages have embeds, proceeding with merge")
                
                # Edit the user's message to include the question text as content
                # Keep their embed untouched (preserves video field)
                question_text = question_embed.description
                
                await message.edit(content=question_text, embed=user_embed)
                print(f"✏️  Added question text to user's message")
                
                # Now delete the original question message since we've merged into user's message
                try:
                    await question_message.delete()
                    print(f"🗑️  Deleted original question message")
                except Exception as e:
                    print(f"⚠️  Could not delete original question: {e}")
                
                # Remove from tracker - DO NOT delete user's message
                image_tracker.remove_pending(message.guild.id, message.author.id)
                return
            else:
                print(f"⚠️  Question message has no embeds, cannot merge")
        
        # If no embed in user message, handle static images normally
        processed_url = await process_image_url(image_url)
        print(f"📎 Processed URL: {processed_url[:100]}...")
        
        # For static images, we can attach them to the embed
        if question_message.embeds:
            old_embed = question_message.embeds[0]
            
            # Create new embed with the image
            new_embed = discord.Embed(
                description=old_embed.description,
                color=old_embed.color,
                title=old_embed.title,
                url=old_embed.url
            )
            new_embed.set_image(url=processed_url)
            
            # Copy footer if it exists
            if old_embed.footer:
                new_embed.set_footer(text=old_embed.footer.text, icon_url=old_embed.footer.icon_url)
            
            # Edit the question with the new embed
            await question_message.edit(embed=new_embed)
            print(f"✏️  Attached image to question embed")
        
        # Delete the follow-up image message (for static images only, not embeds)
        try:
            await message.delete()
            print(f"✅ Auto-attached image to question {pending.message_id} and deleted follow-up message")
        except discord.Forbidden:
            print(f"⚠️  Could not delete follow-up message (missing 'Manage Messages' permission)")
            print(f"💡 Image was attached successfully! Grant 'Manage Messages' permission to auto-delete follow-up posts.")
        except Exception as e:
            print(f"⚠️  Could not delete follow-up message: {e}")
        
        # Remove from tracker
        image_tracker.remove_pending(message.guild.id, message.author.id)
            
    except discord.NotFound:
        print(f"⚠️  Could not find question message {pending.message_id}")
        image_tracker.remove_pending(message.guild.id, message.author.id)
    except discord.Forbidden:
        print(f"⚠️  Missing permissions to edit message {pending.message_id}")
        image_tracker.remove_pending(message.guild.id, message.author.id)
    except Exception as e:
        logger.error(f"Error auto-attaching image: {e}", exc_info=True)
        print(f"❌ Error auto-attaching image: {e}")
        image_tracker.remove_pending(message.guild.id, message.author.id)


@client.event
async def on_interaction(interaction: discord.Interaction) -> None:
    """Track command performance metrics.

    Args:
        interaction: Discord interaction object
    """
    if interaction.type == discord.InteractionType.application_command:
        # Record command execution start time
        interaction.extras["start_time"] = time.perf_counter()


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
