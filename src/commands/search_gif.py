"""Slash command handler for /search-gif command."""

import discord
from discord import app_commands, ui

from src.services.giphy_service import get_giphy_service


class GIFSearchModal(ui.Modal, title="Search for a GIF"):
    """Modal for searching GIFs."""
    
    search_query = ui.TextInput(
        label="Search Term",
        placeholder="e.g., excited, happy, star wars",
        required=True,
        max_length=100,
        style=discord.TextStyle.short,
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission."""
        await interaction.response.defer(ephemeral=True)
        
        giphy_service = get_giphy_service()
        if not giphy_service.is_configured():
            await interaction.followup.send(
                "❌ GIF search is not configured.\n\n"
                "To enable this feature, add a GIPHY_API_KEY to your .env file.\n"
                "Get a free API key at: https://developers.giphy.com/",
                ephemeral=True
            )
            return
        
        # Search for GIFs
        query = self.search_query.value.strip()
        results = await giphy_service.search_gifs(query, limit=10)
        
        if not results:
            await interaction.followup.send(
                f"❌ No GIFs found for '{query}'\n\nTry a different search term!",
                ephemeral=True
            )
            return
        
        # Show results with selection buttons
        view = GIFSelectionView(results)
        
        embed = discord.Embed(
            title=f"🔍 GIF Search Results for '{query}'",
            description=f"Found {len(results)} GIFs. Click a button to copy the URL:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )


class GIFSelectionView(ui.View):
    """View with buttons for selecting a GIF from search results."""
    
    def __init__(self, results: list):
        super().__init__(timeout=300)  # 5 minutes to select
        self.results = results
        
        # Add a button for each GIF (max 10, which is 2 rows of 5)
        for i, gif in enumerate(results[:10]):
            # Truncate title to fit button
            title = gif['title'][:40] if len(gif['title']) > 40 else gif['title']
            
            button = ui.Button(
                label=f"{i+1}. {title}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"gif_select_{i}",
                row=i // 5  # 5 buttons per row (rows 0-1)
            )
            button.callback = self.make_callback(i)
            self.add_item(button)
    
    def make_callback(self, index):
        """Create a callback for a specific GIF button."""
        async def callback(interaction: discord.Interaction):
            gif = self.results[index]
                
            await interaction.response.send_message(
                f"✅ Selected: **{gif['title']}**\n\n"
                f"📋 Copy this URL and paste it in `/post-question`:\n"
                f"```\n{gif['url']}\n```\n"
                f"Preview: {gif['url']}",
                ephemeral=True
            )
            # Disable all buttons after selection
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
        
        return callback


@app_commands.command(
    name="search-gif",
    description="Search for a GIF to use in your trivia question",
)
async def search_gif_command(interaction: discord.Interaction) -> None:
    """Handle the /search-gif slash command by opening a search modal.

    Args:
        interaction: Discord interaction object
    """
    try:
        modal = GIFSearchModal()
        await interaction.response.send_modal(modal)

    except Exception as e:
        print(f"Error in /search-gif command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Something went wrong, please try again",
                ephemeral=True,
            )
