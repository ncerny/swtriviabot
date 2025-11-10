"""Slash command handler for /post-question command."""

import asyncio
import logging
import os
import re
import discord
from discord import app_commands, ui
from dotenv import load_dotenv
import aiohttp

# Load environment variables from .env file
load_dotenv()

from src.services import answer_service, storage_service, image_service

logger = logging.getLogger(__name__)







class PostQuestionModal(ui.Modal, title="Post Trivia Question"):
    """Modal form for posting a trivia question with previous day's results."""

    yesterday_answer = ui.TextInput(
        label="Yesterday's Answer",
        placeholder="e.g., Paris",
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    yesterday_winners = ui.TextInput(
        label="Yesterday's Winners",
        placeholder="e.g., Curly, Larry, and Moe (leave blank if no winners)",
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )

    todays_question = ui.TextInput(
        label="Today's Question",
        placeholder="Enter the trivia question...",
        required=True,
        max_length=2000,
        style=discord.TextStyle.paragraph,
    )



    def __init__(self, guild_id: int, channel: discord.TextChannel):
        super().__init__()
        self.guild_id = str(guild_id)  # Convert to string for consistency with answer_service
        self.channel = channel
        self.interaction = None  # Will be set in on_submit



    async def _wait_for_image_attachment(self, timeout: float = 15.0) -> discord.Embed | None:
        """
        Wait for a follow-up message with an image embed from the same user.

        Args:
            timeout: Seconds to wait for the image message

        Returns:
            Embed if image found, None if timeout or no image
        """
        try:
            # Wait for the next message from the same user in the same channel
            message = await self.interaction.client.wait_for(
                'message',
                timeout=timeout,
                check=lambda m: (
                    m.author == self.interaction.user and
                    m.channel == self.channel and
                    (m.embeds or m.attachments or 'http' in m.content)  # Has embeds, attachments, or URLs
                )
            )

            # Check for image embeds (Tenor GIFs, uploaded images, etc.)
            if message.embeds:
                for embed in message.embeds:
                    if embed.type == 'image' or embed.type == 'gifv' or (embed.image and embed.image.url):
                        # Always delete the user's message since we're re-posting the image
                        try:
                            await message.delete()
                        except:
                            pass  # Ignore delete errors

                        # For Tenor embeds, always try to resolve to proper GIF URL
                        tenor_url = None

                        # Check all possible Tenor URL sources
                        if embed.url and 'tenor.com' in embed.url:
                            tenor_url = embed.url
                        elif embed.image and embed.image.url and 'tenor.com' in embed.image.url:
                            tenor_url = embed.image.url
                        elif embed.video and embed.video.url and 'tenor.com' in embed.video.url:
                            tenor_url = embed.video.url

                        # If we found any Tenor URL, resolve it to get the proper GIF
                        if tenor_url:
                            resolved_embed = await self._resolve_tenor_url(tenor_url)
                            if resolved_embed:
                                return resolved_embed

                        # Fallback: use the original embed's image URL (for non-Tenor images)
                        if embed.image and embed.image.url:
                            embed_copy = discord.Embed()
                            if embed.title:
                                embed_copy.title = embed.title
                            if embed.description:
                                embed_copy.description = embed.description
                            embed_copy.set_image(url=embed.image.url)
                            if embed.thumbnail:
                                embed_copy.set_thumbnail(url=embed.thumbnail.url)
                            if embed.footer:
                                embed_copy.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                            return embed_copy



            # Check for attachments (uploaded images)
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        # Always delete the user's message since we're re-posting the image
                        try:
                            await message.delete()
                        except:
                            pass

                        # Create embed for the attachment
                        embed = discord.Embed()
                        embed.set_image(url=attachment.url)
                        return embed

            # Check for image URLs in message content (if no embeds or attachments)
            if not (message.embeds or message.attachments):
                import re
                from src.services.image_service import validate_image_url

            # Look for URLs in the message content
                url_pattern = r'https?://[^\s]+'
                urls = re.findall(url_pattern, message.content.strip())
                if urls:
                    # Check if it's a Tenor URL - handle differently
                    if 'tenor.com' in urls[0]:
                        resolved_embed = await self._resolve_tenor_url(urls[0])
                        if resolved_embed:
                            # Delete the user's message
                            try:
                                await message.delete()
                            except:
                                pass
                            return resolved_embed
                    else:
                        # Process as direct image URL
                        success, result = await validate_image_url(urls[0])
                        if success and isinstance(result, discord.Embed):
                            # Delete the user's message
                            try:
                                await message.delete()
                            except:
                                pass
                            return result
                        elif not success and isinstance(result, str):
                            # Send error message to channel
                            await self.channel.send(f"⚠️ **Image Error**: {result}")
                            # Delete the user's message
                            try:
                                await message.delete()
                            except:
                                pass
                            return None

        except asyncio.TimeoutError:
            # No image message received within timeout
            pass

        return None

    async def _resolve_tenor_url(self, url: str) -> discord.Embed | None:
        """
        Resolve any Tenor URL to the actual full GIF using the API.

        Args:
            url: Any Tenor URL (HTML page or media URL)

        Returns:
            Discord embed with the actual GIF, or None if resolution fails
        """
        try:
            import re
            tenor_id = None

            # Check for HTML URL format: https://tenor.com/view/[slug]-[id]
            # The ID is after the last dash in the URL
            match = re.search(r'tenor\.com/view/.*-(\d+)(?:$|\?)', url)
            if match:
                tenor_id = match.group(1)
            else:
                # Check for media URL format: https://media.tenor.com/[id]/[filename].gif
                match = re.search(r'media\.tenor\.com/([a-zA-Z0-9]+)/', url)
                if match:
                    tenor_id = match.group(1)

            if not tenor_id:
                print(f"DEBUG: Could not extract Tenor ID from URL: {url}")
                return None

            print(f"DEBUG: Extracted Tenor ID: {tenor_id}")

            api_key = os.getenv('TENOR_API_KEY')
            print(f"DEBUG: Tenor API key present: {api_key is not None}")

            if not api_key:
                print("DEBUG: No Tenor API key configured")
                return None

            # Use Tenor API to get the GIF details
            api_url = "https://tenor.googleapis.com/v2/posts"
            params = {
                'ids': tenor_id,
                'key': api_key
            }

            print(f"DEBUG: Making API call to: {api_url}?{'&'.join(f'{k}={v}' for k,v in params.items())}")

            # Create a temporary session for the API call
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as temp_session:
                async with temp_session.get(api_url, params=params) as response:
                    if response.status != 200:
                        return None

                    try:
                        data = await response.json()
                        print(f"DEBUG: Tenor API response: {data}")
                    except Exception as e:
                        print(f"DEBUG: Failed to parse JSON response: {e}")
                        raw_text = await response.text()
                        print(f"DEBUG: Raw response text: {raw_text[:500]}")
                        return None

                    if not data or not isinstance(data, dict):
                        print(f"DEBUG: Invalid response data: {type(data)}")
                        return None

                    if not data.get('results'):
                        print("DEBUG: No results in Tenor API response")
                        return None

                    result = data['results'][0]
                    media_formats = result.get('media_formats', {})
                    print(f"DEBUG: Media formats available: {list(media_formats.keys())}")

                    gif_info = media_formats.get('gif')

                    if not gif_info or not gif_info.get('url'):
                        print("DEBUG: No GIF info or URL in Tenor response")
                        return None

                    gif_url = gif_info['url']
                    print(f"DEBUG: Resolved Tenor GIF URL: {gif_url}")

                    # Create embed with the actual GIF
                    embed = discord.Embed()
                    embed.set_image(url=gif_url)
                    return embed

        except Exception as e:
            print(f"Error resolving Tenor URL {url}: {e}")
            return None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            # Store interaction for use in other methods
            self.interaction = interaction

            # Defer response
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.InteractionResponded:
                logger.warning("Interaction already responded in PostQuestionModal")
            except Exception as e:
                logger.error(f"Failed to defer PostQuestionModal interaction: {e}", exc_info=True)
                return

            # Check bot permissions in the channel
            bot_permissions = self.channel.permissions_for(interaction.guild.me)
            if not bot_permissions.send_messages:
                try:
                    await interaction.followup.send(
                        "❌ I don't have permission to send messages in this channel.\n\n"
                        "Please give me the following permissions:\n"
                        "• Send Messages\n"
                        "• Embed Links\n"
                        "• Use Application Commands\n"
                        "• Manage Messages (optional - for deleting follow-up image messages)",
                        ephemeral=True,
                    )
                except discord.errors.NotFound:
                    logger.error("Interaction expired before permission error message", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to send permission error: {e}", exc_info=True)
                return

            if not bot_permissions.embed_links:
                try:
                    await interaction.followup.send(
                        "❌ I don't have permission to embed links in this channel.\n\n"
                        "Please enable the 'Embed Links' permission for me.",
                        ephemeral=True,
                    )
                except discord.errors.NotFound:
                    logger.error("Interaction expired before embed permission error", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to send embed permission error: {e}", exc_info=True)
                return

            # Get previous answers before resetting
            previous_session = answer_service.get_session(self.guild_id)
            previous_answers_message = None

            if previous_session and previous_session.answers:
                # Format previous answers
                answer_lines = []
                for answer in previous_session.answers.values():
                    timestamp_str = answer.timestamp.strftime("%Y-%m-%d %H:%M UTC")
                    answer_lines.append(
                        f"**{answer.username}** ({timestamp_str}):\n{answer.text}\n"
                    )

                answers_text = "\n".join(answer_lines)

                # Truncate if too long
                if len(answers_text) > 1800:
                    answers_text = answers_text[:1800] + "\n\n_(truncated due to length)_"

                previous_answers_message = (
                    f"📋 **Previous Session Answers** (before reset)\n\n"
                    f"{answers_text}\n"
                    f"_Total answers: {len(previous_session.answers)}_"
                )

            # Send previous answers to admin FIRST (before resetting)
            if previous_answers_message:
                try:
                    await interaction.followup.send(
                        previous_answers_message,
                        ephemeral=True,
                    )
                except discord.errors.NotFound:
                    logger.error("Interaction expired before sending previous answers", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to send previous answers: {e}", exc_info=True)
            else:
                try:
                    await interaction.followup.send(
                        "✅ Question posted!\n\n_No previous answers to display._",
                        ephemeral=True,
                    )
                except discord.errors.NotFound:
                    logger.error("Interaction expired before confirmation message", exc_info=True)
                except Exception as e:
                    logger.error(f"Failed to send confirmation message: {e}", exc_info=True)

            # Reset session and create new one
            answer_service.reset_session(self.guild_id)
            session = answer_service.create_session(self.guild_id)
            storage_service.save_session_to_disk(self.guild_id, session)



            # Create comprehensive message content
            message_parts = []

            # Yesterday's results section
            if self.yesterday_answer.value.strip() or self.yesterday_winners.value.strip():
                if self.yesterday_answer.value.strip():
                    message_parts.append(f"**Yesterday's Answer...**\n{self.yesterday_answer.value.strip()}")

                winners_text = ""
                if self.yesterday_winners.value.strip() and self.yesterday_winners.value.strip() != "no winners":
                    winners_text = f"Congrats to {self.yesterday_winners.value.strip()} your gold has been mailed. Thanks for playing!"
                else:
                    winners_text = "Unfortunately we had no winners, better luck next time!"

                message_parts.append(winners_text)
                message_parts.append("")  # Empty line

            # Today's question
            message_parts.append(f"**Today's Question...**\n{self.todays_question.value.strip()}")
            message_parts.append("")  # Empty line

            # Create the comprehensive message (without button instruction text)
            full_content = "\n".join(message_parts)
            view = AnswerButton()

            # Send the complete message with button
            question_message = await self.channel.send(
                content=full_content,
                view=view
            )

            # Wait for potential image attachment in follow-up message (up to 5 minutes)
            image_embed = await self._wait_for_image_attachment(timeout=300.0)  # 5 minutes

            # Edit message to add image if found
            if image_embed:
                # Edit the message to include the image
                await question_message.edit(embed=image_embed)

        except ValueError as e:
            try:
                await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
            except discord.errors.NotFound:
                logger.error("Interaction expired before validation error message", exc_info=True)
            except Exception as followup_error:
                logger.error(f"Failed to send validation error: {followup_error}", exc_info=True)
        except Exception as e:
            logger.error(
                f"Unexpected error in PostQuestionModal for user {interaction.user.id}",
                exc_info=True,
                extra={
                    "guild_id": self.guild_id,
                    "user_id": interaction.user.id
                }
            )
            try:
                await interaction.followup.send(
                    "❌ Something went wrong, please try again",
                    ephemeral=True,
                )
            except discord.errors.NotFound:
                logger.error("Interaction expired before error message", exc_info=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}", exc_info=True)


class AnswerModal(ui.Modal, title="Submit Your Trivia Answer"):
    """Modal form for submitting trivia answers."""

    answer_text = ui.TextInput(
        label="Your Answer",
        placeholder="Type your answer here...",
        required=True,
        max_length=4000,
        style=discord.TextStyle.paragraph,  # Multi-line text area
    )

    def __init__(self, guild_id: str, user_id: str, username: str):
        super().__init__()
        self.guild_id = guild_id
        self.user_id = user_id
        self.username = username

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            # Defer the response to prevent action menu from appearing
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.InteractionResponded:
                logger.warning("Interaction already responded in AnswerModal")
            except Exception as e:
                logger.error(f"Failed to defer AnswerModal interaction: {e}", exc_info=True)
                return
            
            # Submit or update answer
            answer, is_update = answer_service.submit_answer(
                guild_id=self.guild_id,
                user_id=self.user_id,
                username=self.username,
                text=str(self.answer_text.value),
            )

            # Save session to disk
            session = answer_service.get_session(self.guild_id)
            if session:
                storage_service.save_session_to_disk(self.guild_id, session)

            # Send appropriate response via followup
            if is_update:
                message = "🔄 You've already answered this question - updating your answer!"
            else:
                message = "✅ Your answer has been recorded!"

            try:
                await interaction.followup.send(message, ephemeral=True)
            except discord.errors.NotFound:
                logger.error("Interaction expired before answer confirmation", exc_info=True)
            except Exception as e:
                logger.error(f"Failed to send answer confirmation: {e}", exc_info=True)

        except ValueError as e:
            # Validation errors
            try:
                await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
            except discord.errors.NotFound:
                logger.error("Interaction expired before validation error", exc_info=True)
            except Exception as followup_error:
                logger.error(f"Failed to send validation error: {followup_error}", exc_info=True)
        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Unexpected error in AnswerModal for user {interaction.user.id}",
                exc_info=True,
                extra={
                    "guild_id": self.guild_id,
                    "user_id": self.user_id
                }
            )
            try:
                await interaction.followup.send(
                    "❌ Something went wrong, please try again",
                    ephemeral=True,
                )
            except discord.errors.NotFound:
                logger.error("Interaction expired before error message", exc_info=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}", exc_info=True)


class AnswerButton(ui.View):
    """Persistent view with button for answer submission."""

    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @ui.button(
        label="Submit Your Answer",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="trivia:submit_answer",
    )
    async def submit_answer_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Handle the submit answer button click."""
        try:
            # Get guild context
            guild_id = str(interaction.guild_id) if interaction.guild_id else None
            user_id = str(interaction.user.id)
            username = interaction.user.display_name

            if not guild_id:
                await interaction.response.send_message(
                    "❌ This button can only be used in a server",
                    ephemeral=True,
                )
                return

            # Check if there's an active session
            session = answer_service.get_session(guild_id)
            if not session:
                await interaction.response.send_message(
                    "❌ No active trivia question for this server",
                    ephemeral=True,
                )
                return

            # Open modal form
            modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
            await interaction.response.send_modal(modal)

        except Exception as e:
            logger.error(
                f"Error in submit answer button for user {interaction.user.id}",
                exc_info=True,
                extra={
                    "guild_id": guild_id if 'guild_id' in locals() else None,
                    "user_id": interaction.user.id
                }
            )
            # Check if we can still respond
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Something went wrong, please try again",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        "❌ Something went wrong, please try again",
                        ephemeral=True,
                    )
            except discord.errors.NotFound:
                logger.error("Interaction expired before button error message", exc_info=True)
            except Exception as followup_error:
                logger.error(f"Failed to send button error message: {followup_error}", exc_info=True)


@app_commands.command(
    name="post-question",
    description="Post a trivia question with previous results (Admin only)",
)
@app_commands.default_permissions(administrator=True)
async def post_question_command(interaction: discord.Interaction) -> None:
    """Handle the /post-question slash command by opening a modal.

    Args:
        interaction: Discord interaction object
    """
    try:
        # Get guild context
        guild_id = interaction.guild_id

        # Validate guild context (quick check, no await)
        if not guild_id:
            await interaction.response.send_message(
                "❌ This command can only be used in a server, not in DMs",
                ephemeral=True,
            )
            return

        # Open the modal immediately - permission checks happen in modal submission
        # This prevents interaction timeout when GIFs or attachments are present
        modal = PostQuestionModal(guild_id=guild_id, channel=interaction.channel)
        await interaction.response.send_modal(modal)

    except Exception as e:
        logger.error(
            f"Error in /post-question command for user {interaction.user.id}",
            exc_info=True,
            extra={
                "guild_id": interaction.guild_id,
                "user_id": interaction.user.id
            }
        )
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Something went wrong, please try again",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "❌ Something went wrong, please try again",
                    ephemeral=True,
                )
        except discord.errors.NotFound:
            logger.error("Interaction expired before command error message", exc_info=True)
        except Exception as followup_error:
            logger.error(f"Failed to send command error message: {followup_error}", exc_info=True)
