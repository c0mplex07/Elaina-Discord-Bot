import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="Show server information")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("❌ This command can only be used in a server!", ephemeral=True)
            return

        owner = guild.owner
        owner_mention = owner.mention if owner else "Unknown"
        creation_date = guild.created_at.strftime("%d/%m/%Y %H:%M:%S")
        boost_count = guild.premium_subscription_count
        boost_level = guild.premium_tier
        language = guild.preferred_locale

        total_members = len(guild.members)
        bots = len([member for member in guild.members if member.bot])
        human_members = total_members - bots
        total_channels = len(guild.channels)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        verification_level = guild.verification_level.name

        embed_color = random.randint(0, 0xFFFFFF)
        embed = discord.Embed(title=f"{guild.name}", color=embed_color)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text="Server Information", icon_url=guild.icon.url)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(name="👑 Owner", value=owner_mention, inline=False)
        embed.add_field(name="📅 Created At", value=creation_date, inline=False)
        embed.add_field(name="🚀 Server Boost", value=f"Level: {boost_level} - Count: {boost_count}", inline=False)
        embed.add_field(name="🌐 Language", value=language, inline=False)
        embed.add_field(name="👥 Member Count", value=human_members, inline=True)
        embed.add_field(name="🤖 Bot Count", value=bots, inline=True)
        embed.add_field(name="💬 Total Channels", value=total_channels, inline=True)
        embed.add_field(name="💬 Text Channels", value=text_channels, inline=True)
        embed.add_field(name="🔊 Voice Channels", value=voice_channels, inline=True)
        embed.add_field(name="🔒 Security", value=f"Verification Level: {verification_level}", inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))