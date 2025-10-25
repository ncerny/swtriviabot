"""Control panel view with persistent buttons for trivia bot."""

import discord
from discord import ui

from src.services import answer_service, permission_service, storage_service
from src.utils.formatters import format_answer_list


class AnswerModal(ui.Modal, title="Submit Your Trivia Answer"):
    """Modal form for submitting trivia answers."""

    answer_text = ui.TextInput(
        label="Your Answer",
        placeholder="Type your answer here...",
        required=True,
        max_length=4000,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, guild_id: str, user_id: str, username: str):
        super().__init__()
        self.guild_id = guild_id
        self.user_id = user_id
        self.username = username

    async def on_submit(self, interaction: discord.Interaction) -> None:
        """Handle modal submission."""
        try:
            answer, is_update = answer_service.submit_answer(
                guild_id=self.guild_id,
                user_id=self.user_id,
                username=self.username,
                text=str(self.answer_text.value),
            )

            session = answer_service.get_session(self.guild_id)
            if session:
                storage_service.save_session_to_disk(self.guild_id, session)

            if is_update:
                message = "🔄 You've already answered this question - updating your answer!"
            else:
                message = "✅ Your answer has been recorded!"

            await interaction.response.send_message(message, ephemeral=True)

        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
        except Exception as e:
            print(f"Error in answer modal: {e}")
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )


class TriviaControlPanel(ui.View):
    """Persistent button control panel for trivia bot."""

    def __init__(self):
        super().__init__(timeout=None)  # Persistent buttons never timeout

    @ui.button(
        label="Submit Answer",
        style=discord.ButtonStyle.primary,
        emoji="📝",
        custom_id="trivia:submit_answer",
    )
    async def submit_answer_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Handle submit answer button click."""
        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
        user_id = str(interaction.user.id)
        username = interaction.user.display_name

        if guild_id == "DM":
            await interaction.response.send_message(
                "❌ This feature can only be used in a server",
                ephemeral=True,
            )
            return

        modal = AnswerModal(guild_id=guild_id, user_id=user_id, username=username)
        await interaction.response.send_modal(modal)

    @ui.button(
        label="View Answers",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        custom_id="trivia:view_answers",
    )
    async def view_answers_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Handle view answers button click."""
        # Check admin permission
        if not permission_service.check_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this feature (Administrator required)",
                ephemeral=True,
            )
            return

        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"

        if guild_id == "DM":
            await interaction.response.send_message(
                "❌ This feature can only be used in a server",
                ephemeral=True,
            )
            return

        session = answer_service.get_session(guild_id)

        if not session or not session.answers:
            await interaction.response.send_message(
                "📋 No answers submitted yet",
                ephemeral=True,
            )
            return

        answers = session.get_all_answers()
        formatted_list = format_answer_list(answers)

        await interaction.response.send_message(formatted_list, ephemeral=True)

    @ui.button(
        label="Reset Answers",
        style=discord.ButtonStyle.danger,
        emoji="🔄",
        custom_id="trivia:reset_answers",
    )
    async def reset_answers_button(
        self, interaction: discord.Interaction, button: ui.Button
    ) -> None:
        """Handle reset answers button click."""
        # Check admin permission
        if not permission_service.check_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this feature (Administrator required)",
                ephemeral=True,
            )
            return

        guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"

        if guild_id == "DM":
            await interaction.response.send_message(
                "❌ This feature can only be used in a server",
                ephemeral=True,
            )
            return

        # Reset session
        answer_service.reset_session(guild_id)
        storage_service.delete_session_file(guild_id)

        await interaction.response.send_message(
            "🔄 All answers have been reset - ready for next question!",
            ephemeral=True,
        )
