"""Script to clear old slash commands from Discord."""

import os
import asyncio
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = os.getenv('DISCORD_TEST_GUILD_ID')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    """Clear commands and sync."""
    print(f'Logged in as {client.user}')
    
    if GUILD_ID:
        # Clear guild-specific commands
        guild = discord.Object(id=int(GUILD_ID))
        tree.clear_commands(guild=guild)
        await tree.sync(guild=guild)
        print(f'✅ Cleared commands from test guild {GUILD_ID}')
    else:
        # Clear global commands
        tree.clear_commands(guild=None)
        await tree.sync()
        print('✅ Cleared global commands')
    
    await client.close()


if __name__ == '__main__':
    client.run(TOKEN)
