"""Slash command handler for /search-gif command."""

import discord
from discord import app_commands, ui

from src.services.giphy_service import get_giphy_service
from src.services.klipy_service import KlipyService


class ProviderSelectionView(ui.View):
    """View for selecting GIF provider (Giphy or Klipy)."""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.provider = None
        
    @ui.button(label="Giphy", style=discord.ButtonStyle.primary, emoji="🎬")
    async def giphy_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Giphy provider selection."""
        self.provider = "giphy"
        await self.show_search_modal(interaction)
        
    @ui.button(label="Klipy", style=discord.ButtonStyle.primary, emoji="🎪")
    async def klipy_button(self, interaction: discord.Interaction, button: ui.Button):
        """Handle Klipy provider selection."""
        self.provider = "klipy"
        await self.show_search_modal(interaction)
        
    async def show_search_modal(self, interaction: discord.Interaction):
        """Show the search modal for the selected provider."""
        modal = GIFSearchModal(provider=self.provider)
        await interaction.response.send_modal(modal)


class GIFSearchModal(ui.Modal, title="Search for a GIF"):
    """Modal for searching GIFs."""
    
    def __init__(self, provider: str = "giphy"):
        super().__init__(title=f"Search {provider.title()} for GIFs")
        self.provider = provider
        
        # Update placeholder based on provider
        placeholder = "e.g., excited, happy, star wars"
        if provider == "klipy":
            placeholder = "Search KLIPY - e.g., excited, happy, star wars"
    
        self.search_query = ui.TextInput(
            label="Search Term",
            placeholder=placeholder,
            required=True,
            max_length=100,
            style=discord.TextStyle.short,
        )
        self.add_item(self.search_query)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle search submission."""
        await interaction.response.defer(ephemeral=True)
        
        query = self.search_query.value.strip()
        
        # Search using the selected provider
        if self.provider == "giphy":
            results = await self._search_giphy(interaction, query)
        else:  # klipy
            results = await self._search_klipy(interaction, query)
            
        if results is None:
            return  # Error message already sent
        
        if not results:
            # Provide more helpful error message for Klipy
            if self.provider == "klipy":
                await interaction.followup.send(
                    f"❌ No GIFs found for '{query}'\n\n"
                    f"**If you're getting no results for every search:**\n"
                    f"• Your API key might be for 'Testing/Sandbox' (which has no content)\n"
                    f"• Create a **Production** API key at: https://partner.klipy.com/api-keys\n"
                    f"• Or try using Giphy instead (select Giphy button when using /search-gif)",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ No GIFs found for '{query}'\n\nTry a different search term!",
                    ephemeral=True
                )
            return
        
        # Show results with selection buttons
        view = GIFSelectionView(results, provider=self.provider)
        
        emoji = "🎬" if self.provider == "giphy" else "🎪"
        embed = discord.Embed(
            title=f"{emoji} {self.provider.title()} Results for '{query}'",
            description=f"Found {len(results)} GIFs. Click a button to copy the URL:",
            color=discord.Color.blue()
        )
        
        # Add attribution footer as required
        if self.provider == "klipy":
            embed.set_footer(text="Powered by KLIPY")
        
        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )
    
    async def _search_giphy(self, interaction: discord.Interaction, query: str):
        """Search using Giphy API."""
        giphy_service = get_giphy_service()
        if not giphy_service.is_configured():
            await interaction.followup.send(
                "❌ Giphy is not configured.\n\n"
                "To enable this feature, add a GIPHY_API_KEY to your .env file.\n"
                "Get a free API key at: https://developers.giphy.com/",
                ephemeral=True
            )
            return None
        
        return await giphy_service.search_gifs(query, limit=10)
    
    async def _search_klipy(self, interaction: discord.Interaction, query: str):
        """Search using Klipy API."""
        klipy_service = KlipyService()
        
        try:
            # Use Discord user ID as customer_id (required by Klipy)
            customer_id = str(interaction.user.id)
            return await klipy_service.search_gifs(
                query=query,
                customer_id=customer_id,
                limit=10,
                content_filter="medium"  # Safe for general audiences
            )
        except ValueError as e:
            # API key not configured
            await interaction.followup.send(
                f"❌ Klipy is not configured.\n\n"
                f"To enable this feature, add a KLIPY_API_KEY to your .env file.\n"
                f"Get a free API key at: https://partner.klipy.com/api-keys\n\n"
                f"Error: {e}",
                ephemeral=True
            )
            return None
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error searching Klipy: {e}",
                ephemeral=True
            )
            return None


class GIFSelectionView(ui.View):
    """View with buttons for selecting a GIF from search results."""
    
    def __init__(self, results: list, provider: str = "giphy"):
        super().__init__(timeout=300)  # 5 minutes to select
        self.results = results
        self.provider = provider
        
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
            
            # Add provider attribution
            provider_note = ""
            if self.provider == "klipy":
                provider_note = "\n\n_Powered by KLIPY_"
                
            await interaction.response.send_message(
                f"✅ Selected: **{gif['title']}**\n\n"
                f"📋 Copy this URL and paste it in `/post-question`:\n"
                f"```\n{gif['url']}\n```\n"
                f"Preview: {gif['url']}{provider_note}",
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
    """Handle the /search-gif slash command by showing provider selection.

    Args:
        interaction: Discord interaction object
    """
    try:
        # Show provider selection view
        view = ProviderSelectionView()
        
        embed = discord.Embed(
            title="🔍 GIF Search",
            description=(
                "Choose a GIF provider to search:\n\n"
                "🎬 **Giphy** - Popular GIF library\n"
                "🎪 **Klipy** - GIFs, Clips, Stickers & Memes\n\n"
                "_Click a button to start searching_"
            ),
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

    except Exception as e:
        print(f"Error in /search-gif command: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred. Please try again.",
                ephemeral=True
            )

