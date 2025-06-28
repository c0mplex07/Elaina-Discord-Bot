import discord
from discord.ext import commands
from discord import app_commands
import time

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        start_time = time.time()
        message = await interaction.response.send_message("Pinging...", ephemeral=True)
        end_time = time.time()

        bot_latency = round((end_time - start_time) * 1000)
        api_latency = round(self.bot.latency * 1000)    

        await interaction.edit_original_response(content=f"Bot Latency: `{bot_latency}ms`\nAPI Latency: `{api_latency}ms`")

async def setup(bot):
    await bot.add_cog(Ping(bot))