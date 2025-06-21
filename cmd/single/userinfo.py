import discord
from discord.ext import commands
from datetime import datetime

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='userinfo')
    async def user_info(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        account_creation = member.created_at.strftime("%d/%m/%Y %H:%M:%S")
        join_date = member.joined_at.strftime("%d/%m/%Y %H:%M:%S")

        roles = [role.mention for role in member.roles[1:]]
        roles = ", ".join(roles) if roles else "Không có vai trò"

        boost_count = ctx.guild.premium_subscription_count

        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

        embed = discord.Embed(title=f"Thông tin người dùng", color=0x00ff00)
        embed.add_field(name="Username", value=member.name, inline=False)
        embed.add_field(name="Thời gian tạo", value=account_creation, inline=False)
        embed.add_field(name="Thời gian tham gia", value=join_date, inline=False)
        embed.add_field(name="Số lần tăng cường", value=boost_count, inline=False)
        embed.add_field(name="Vai trò", value=roles, inline=False)
        
        embed.set_thumbnail(url=avatar_url)
        embed.set_footer(text="enou love you", icon_url=avatar_url)
        
        await ctx.send(embed=embed)

# Hàm setup để thêm Cog vào bot
async def setup(bot):
    await bot.add_cog(UserInfo(bot))