import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional
import random

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Show user information")
    @app_commands.describe(member="The member to show info for (optional)")
    async def user_info(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await interaction.response.defer()
        if member is None:
            if isinstance(interaction.user, discord.Member):
                member = interaction.user
            elif interaction.guild is not None:
                member = interaction.guild.get_member(interaction.user.id)
            else:
                await interaction.followup.send("Could not resolve member information.", ephemeral=True)
                return
        if not isinstance(member, discord.Member):
            await interaction.followup.send("Could not resolve member information.", ephemeral=True)
            return

        account_creation = member.created_at.strftime("%Y-%m-%d %H:%M:%S") if member.created_at else "Unknown"
        join_date = member.joined_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(member, 'joined_at') and member.joined_at else "Unknown"

        roles = [role.mention for role in getattr(member, 'roles', [])[1:]] if hasattr(member, 'roles') else []
        roles_str = ", ".join(roles) if roles else "No roles"

        boost_count = 0
        if hasattr(member, 'premium_since') and member.premium_since is not None:
            boost_count = 1
        else:
            boost_count = 0

        avatar_url = member.avatar.url if member.avatar else member.default_avatar.url

        banner_url = None
        try:
            user_obj = await interaction.client.fetch_user(member.id)
            if hasattr(user_obj, 'banner') and user_obj.banner is not None:
                banner_url = user_obj.banner.url
        except Exception:
            banner_url = None

        embed_color = random.randint(0, 0xFFFFFF)

        embed = discord.Embed(title=f"User Information", color=embed_color)
        embed.add_field(name="Nickname", value=member.display_name, inline=False)
        embed.add_field(name="Username", value=member.name, inline=False)
        embed.add_field(name="Account Created", value=account_creation, inline=False)
        embed.add_field(name="Joined Server", value=join_date, inline=False)
        embed.add_field(name="Boost Count", value=boost_count, inline=False)
        embed.add_field(name="Roles", value=roles_str, inline=False)
        embed.set_thumbnail(url=avatar_url)
        if banner_url:
            embed.set_image(url=banner_url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name if hasattr(interaction.user, 'display_name') else interaction.user.name}")

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))