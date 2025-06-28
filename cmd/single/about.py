import discord
from discord.ext import commands
from discord import app_commands
import psutil

class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="about", description="Show information about the bot.")
    async def about(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="About Me",
            description="I'm Elaina a.k.a. The Ashen Witch, born on October 17th, from Robetta.",
            color=0xffb0f7
        )
        embed.add_field(name="🏠 Total servers", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="👥 Total members", value=f"{sum(len(guild.members) for guild in self.bot.guilds)}", inline=True)
        embed.add_field(name="💬 Total channels", value=f"{sum(len(guild.channels) for guild in self.bot.guilds)}", inline=True)
        embed.add_field(name="💬 Text & Voice channels", value=f"Text: {sum(len(guild.text_channels) for guild in self.bot.guilds)}, Voice: {sum(len(guild.voice_channels) for guild in self.bot.guilds)}", inline=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        embed.add_field(name="💻 CPU usage", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="💾 RAM usage", value=f"{ram_usage}%", inline=True)

        embed.set_footer(text="Made with discord.py by c0mplex", icon_url="https://images.opencollective.com/discordpy/25fb26d/logo/256.png")
        embed.set_image(url="https://c.tenor.com/Hpd6ebmlWHMAAAAC/tenor.gif")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(About(bot))