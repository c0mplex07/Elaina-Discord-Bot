import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math
from typing import Optional, cast

# Human-readable English names for time units
unit_names = {"s": "seconds", "m": "minutes", "h": "hours", "w": "weeks"}

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    moderation_group = app_commands.Group(
        name="moderation",
        description="Moderation related commands"
    )

    async def check_all_permissions(self, interaction: discord.Interaction, target: discord.User, required_perm: str) -> bool:
        if interaction.guild is None:
            await interaction.followup.send("⚠️ This command can only be **used within a server**.")
            return False

        guild = interaction.guild
        invoker = cast(discord.Member, interaction.user)
        bot_member: discord.Member = guild.me

        if required_perm == "moderate":
            if not invoker.guild_permissions.moderate_members:
                await interaction.followup.send("❌ You do not have **Timeout Members** permission to use this command.")
                return False
        elif required_perm == "kick":
            if not invoker.guild_permissions.kick_members:
                await interaction.followup.send("❌ You do not have **Kick Members** permission to use this command.")
                return False
        elif required_perm == "ban":
            if not invoker.guild_permissions.ban_members:
                await interaction.followup.send("❌ You do not have **Ban Members** permission to use this command.")
                return False

        if required_perm == "moderate":
            if not bot_member.guild_permissions.moderate_members:
                await interaction.followup.send("⚠️ Please grant me **Timeout Members** permission so I can execute this command.")
                return False
        elif required_perm == "kick":
            if not bot_member.guild_permissions.kick_members:
                await interaction.followup.send("⚠️ Please grant me **Kick Members** permission so I can execute this command.")
                return False
        elif required_perm == "ban":
            if not bot_member.guild_permissions.ban_members:
                await interaction.followup.send("⚠️ Please grant me **Ban Members** permission so I can execute this command.")
                return False

        target_member = guild.get_member(target.id)
        if target_member is not None:
            if invoker.top_role <= target_member.top_role:
                await interaction.followup.send("⚠️ **Your role must be higher than the target member's role**.")
                return False

            if bot_member.top_role <= target_member.top_role:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target member's role**.")
                return False

        return True

    @moderation_group.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="User to warn",
        reason="Reason for warning"
    )
    async def warn(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        assert guild is not None
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- You have been warned in {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Time: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")

        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** has been warned for: `{reason}`."
        )

    @moderation_group.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="User to timeout",
        duration="Timeout duration (e.g., 30s, 5m, 1h, 1w)",
        reason="Reason for timeout"
    )
    async def timeout(self, interaction: discord.Interaction, user: discord.User, duration: str, reason: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        try:
            unit = duration[-1].lower()
            value = int(duration[:-1])
        except Exception:
            await interaction.followup.send("Invalid time format. Examples: 30s, 5m, 1h, 1w.")
            return

        if unit not in {"s", "m", "h", "w"}:
            await interaction.followup.send("Invalid time unit. **Use only s, m, h, or w**.")
            return

        timeout_seconds = value * {"s": 1, "m": 60, "h": 3600, "w": 604800}[unit]
        if timeout_seconds > 604800:
            await interaction.followup.send("Maximum timeout duration is **1 week**.")
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        assert guild is not None
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        utc_expiration_time = utc_now + datetime.timedelta(seconds=timeout_seconds)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_expiration = utc_expiration_time.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        display_expiration_ts = int(display_expiration.timestamp())

        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("Member not found in the server.")
            return

        try:
            await member.timeout(utc_expiration_time, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Cannot timeout member: {e}")
            return

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- You have been timed out in {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Timeout expires at: <t:{display_expiration_ts}:F>.\n"
            f"- Command issued at: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        friendly_duration = f"{value} {unit_names[unit]}"
        await interaction.followup.send(
            f"**{user.display_name}** has been timed out for **{friendly_duration}** for: `{reason}`."
        )

    @moderation_group.command(name="untimeout", description="Remove a user's timeout")
    @app_commands.describe(
        user="User to untimeout",
        reason="Reason for removing timeout (optional)"
    )
    async def untimeout(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        assert guild is not None
        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("Member not found in the server.")
            return

        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Cannot remove timeout: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Your timeout has been lifted in {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Command issued at: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** had their timeout removed for: `{reason}`."
        )

    @moderation_group.command(name="kick", description="Kick a user")
    @app_commands.describe(
        user="User to kick",
        reason="Reason for kick (optional)"
    )
    async def kick(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "kick"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        assert guild is not None
        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("❌ Member not found in the server.")
            return

        try:
            await member.kick(reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Cannot kick: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- You have been kicked from {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Command issued at: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** has been kicked for: `{reason}`."
        )

    @moderation_group.command(name="ban", description="Ban a user")
    @app_commands.describe(
        user="User to ban",
        reason="Reason for ban",
        delete_message="Message deletion timeframe (e.g., 30s, 5m, 1h, 1w)"
    )
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None, delete_message: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "ban"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"
        delete_message_days = 0
        if delete_message:
            try:
                unit = delete_message[-1].lower()
                value = int(delete_message[:-1])
            except Exception:
                await interaction.followup.send("❌ Invalid delete message format. **Examples: 30s, 5m, 1h, 1w**.")
                return

            multipliers = {"s": 1, "m": 60, "h": 3600, "w": 604800}
            if unit not in multipliers:
                await interaction.followup.send("❌ Invalid time unit for delete message. **Use only s, m, h, or w**.")
                return

            delete_seconds = value * multipliers[unit]
            if delete_seconds > 604800:
                await interaction.followup.send("❌ Maximum message deletion timeframe is **1 week**.")
                return
            delete_message_days = math.floor(delete_seconds / 86400)
        
        guild = interaction.guild
        assert guild is not None
        try:
            await guild.ban(user, delete_message_days=delete_message_days, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Cannot ban: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- You have been banned from {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Command issued at: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        friendly_delete = f" and deleted messages from the last **{delete_message_days} days**" if delete_message and delete_message_days > 0 else ""
        await interaction.followup.send(
            f"**{user.display_name}** has been banned{friendly_delete} for: `{reason}`."
        )

    @moderation_group.command(name="unban", description="Unban a user")
    @app_commands.describe(
        user="User to unban",
        reason="Reason for unban"
    )
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: Optional[str] = None):
        await interaction.response.defer()
        if not await self.check_all_permissions(interaction, user, "ban"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        assert guild is not None
        try:
            await guild.unban(user, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Cannot unban: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- You have been unbanned in {guild.name}.\n"
            f"- Reason: {reason}.\n"
            f"- Command issued at: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = None
        if interaction.client and interaction.client.user and interaction.client.user.avatar:
            bot_avatar = interaction.client.user.avatar.url
        if bot_avatar:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Command executed by {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** has been unbanned for: `{reason}`."
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.followup.send("❌ You do not have permission to use this command.")
        elif isinstance(error, discord.Forbidden):
            error_str = str(error).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("⚠️ Please check my role hierarchy in server settings to ensure **my role is higher than the target's role** in the parameter.")
            else:
                await interaction.followup.send("⚠️ Please grant me the required permissions to use this command.")
        else:
            raise error

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
