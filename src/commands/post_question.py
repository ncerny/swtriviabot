"""Slash command handler for /post-question command."""

import re
import discord
from discord import app_commands, ui

from src.services import answer_service, storage_service


def process_image_url(url: str) -> str:
    """Process image URL to ensure it's a direct link to the image.
    
    Handles special cases like Tenor and Giphy URLs.
    
    Args:
        url: The image URL provided by the user
        
    Returns:
        A direct URL to the image file, or the original URL if no processing is needed
    """
    if not url or not url.strip():
        return url
        
    url = url.strip()
    
    # Handle Giphy URLs - convert to direct media link
    # Format: https://giphy.com/gifs/name-name-ABCDEFG123
    if 'giphy.com/gifs/' in url:
        # Extract the alphanumeric ID at the end
        match = re.search(r'-([A-Za-z0-9]+)$', url.rstrip('/'))
        if match:
            gif_id = match.group(1)
            return f"https://media.giphy.com/media/{gif_id}/giphy.gif"
    
    # Handle media.giphy.com URLs (these are already direct)
    if 'media.giphy.com' in url:
        return url
    
    # Handle Tenor URLs - Discord can actually handle these directly in many cases
    # Just return as-is and let Discord's embed system handle it
    # Users can also right-click -> "Copy Image Address" for direct URLs
    if 'tenor.com' in url:
        return url
    
    # If it's already a direct image URL, return as-is
    if any(url.lower().endswith(ext) for ext in ['.gif', '.png', '.jpg', '.jpeg', '.webp', '.bmp']):
        return url
    
    # For other cases, return original URL and let Discord try to handle it
    return url


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

    image_url = ui.TextInput(
        label="Image URL (optional)",
        placeholder="Must be direct image URL ending in .gif, .png, etc.",
        required=False,
        max_length=500,
        style=discord.TextStyle.short,
    )

    def __init__(self, guild_id: str, channel: discord.TextChannel):
        super().__init__()
        self.guild_id = guild_id
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            # Defer response
            await interaction.response.defer(ephemeral=True)

            # Check bot permissions in the channel
            bot_permissions = self.channel.permissions_for(interaction.guild.me)
            if not bot_permissions.send_messages:
                await interaction.followup.send(
                    "❌ I don't have permission to send messages in this channel.\n\n"
                    "Please give me the following permissions:\n"
                    "• Send Messages\n"
                    "• Embed Links\n"
                    "• Use Application Commands",
                    ephemeral=True,
                )
                return

            if not bot_permissions.embed_links:
                await interaction.followup.send(
                    "❌ I don't have permission to embed links in this channel.\n\n"
                    "Please enable the 'Embed Links' permission for me.",
                    ephemeral=True,
                )
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

            # Reset session and create new one
            answer_service.reset_session(self.guild_id)
            session = answer_service.create_session(self.guild_id)
            storage_service.save_session_to_disk(self.guild_id, session)

            # Build the message content
            message_parts = []

            # Add yesterday's answer if provided
            if self.yesterday_answer.value.strip():
                message_parts.append(f"**Yesterday's Answer...**\n{self.yesterday_answer.value.strip()}")

            # Add yesterday's winners if provided
            if self.yesterday_winners.value.strip() and self.yesterday_winners.value.strip() != "" and self.yesterday_winners.value.strip().lower() != "no winners":
                message_parts.append(f"Congrats to {self.yesterday_winners.value.strip()} your gold has been mailed. Thanks for playing!")
            else:
                message_parts.append(f"Unfortunately we had no winners, better luck next time!")


            # Add today's question
            message_parts.append(f"**Today's Question...**\n{self.todays_question.value.strip()}")

            # Combine all parts
            message_content = "\n\n".join(message_parts)

            # Create embed for the question
            embed = discord.Embed(
                description=message_content,
                color=discord.Color.blue()
            )

            # Add image if URL provided
            if self.image_url.value and self.image_url.value.strip():
                original_url = self.image_url.value.strip()
                processed_url = process_image_url(original_url)
                
                try:
                    embed.set_image(url=processed_url)
                    # If URL was converted, log it
                    if processed_url != original_url:
                        print(f"Converted image URL: {original_url} -> {processed_url}")
                except Exception as e:
                    # If the image URL is invalid, log it but continue posting the question
                    print(f"Warning: Could not set image with URL '{processed_url}': {e}")

            # Always set footer
            embed.set_footer(text="Please click the button below to submit your answer!")

            # Create persistent button view
            view = AnswerButton()

            # Post question in the channel
            await self.channel.send(
                embed=embed,
                view=view,
            )

            # Send previous answers to admin if they existed
            if previous_answers_message:
                await interaction.followup.send(
                    previous_answers_message,
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "✅ Question posted!\n\n_No previous answers to display._",
                    ephemeral=True,
                )

        except ValueError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except Exception as e:
            print(f"Error in post question modal: {e}")
            await interaction.followup.send(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )


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
            await interaction.response.defer(ephemeral=True)
            
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

            await interaction.followup.send(message, ephemeral=True)

        except ValueError as e:
            # Validation errors
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except Exception as e:
            # Unexpected errors
            print(f"Error in answer modal: {e}")
            await interaction.followup.send(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )


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
            print(f"Error in submit answer button: {e}")
            # Check if we can still respond
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Something went wrong, please try again",
                    ephemeral=True,
                )


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
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"

        # Validate guild context (quick check, no await)
        if guild_id == "DM":
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
        print(f"Error in /post-question command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
