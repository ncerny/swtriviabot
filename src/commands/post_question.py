"""Slash command handler for /post-question command."""

import discord
from discord import app_commands, ui

from src.services import answer_service, storage_service



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
        placeholder="Direct URL to image",
        required=False,
        max_length=500,
        style=discord.TextStyle.short,
    )

    def __init__(self, guild_id: int, channel: discord.TextChannel):
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

                # Send previous answers to admin if they existed
                if previous_answers_message:
                    await self.channel.send(
                        previous_answers_message,
                        ephemeral=True,
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
            
            # Add image URL if provided
            if self.image_url.value and self.image_url.value.strip():
                image_url = self.image_url.value.strip()
                message_parts.append(image_url)
            
            # Add instruction to submit answer (after image so it appears below the embedded image)
            message_parts.append(f"Please click the button below to submit your answer!")

            # Combine all parts
            message_content = "\n\n".join(message_parts)

            # Create persistent button view
            view = AnswerButton()
            
            # Post question in the channel as content (not embed)
            question_message = await self.channel.send(
                content=message_content,
                view=view,
            )

            # Send previous answers to admin if they existed
            if previous_answers_message:
                await interaction.followup.send(
                    previous_answers_message,
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
        print(f"Error in /post-question command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
