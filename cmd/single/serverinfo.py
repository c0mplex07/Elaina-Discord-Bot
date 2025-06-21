import discord
from discord.ext import commands
from datetime import datetime

class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='serverinfo')
    async def server_info(self, ctx):
        guild = ctx.guild

        owner = guild.owner
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

        embed = discord.Embed(title=f"Thông tin server {guild.name}", color=0x00ff00)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text="Thông tin server", icon_url=guild.icon.url)

        embed.add_field(name="Chủ sở hữu", value=owner, inline=False)
        embed.add_field(name="Thời gian tạo", value=creation_date, inline=False)
        embed.add_field(name="Boost server", value=f"Level: {boost_level} - Số lượng: {boost_count}", inline=False)
        embed.add_field(name="Ngôn ngữ", value=language, inline=False)
        embed.add_field(name="Số lượng members", value=human_members, inline=True)
        embed.add_field(name="Số lượng bot", value=bots, inline=True)
        embed.add_field(name="Tổng số channels", value=total_channels, inline=True)
        embed.add_field(name="Channels text", value=text_channels, inline=True)
        embed.add_field(name="Channels voice", value=voice_channels, inline=True)
        embed.add_field(name="Bảo mật", value=f"Mức xác minh: {verification_level}", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))