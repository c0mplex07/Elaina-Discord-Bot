import discord
from discord.ext import commands
from discord import app_commands
import datetime
import math

unit_names = {"s": "giây", "m": "phút", "h": "giờ", "w": "tuần"}

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    moderation_group = app_commands.Group(
        name="moderation",
        description="Commands related to moderation"
    )

    async def check_all_permissions(self, interaction: discord.Interaction, target: discord.User, required_perm: str) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Lệnh này chỉ có thể **sử dụng trong server**.")
            return False

        guild = interaction.guild
        invoker: discord.Member = interaction.user
        bot_member: discord.Member = guild.me

        if required_perm == "moderate":
            if not invoker.guild_permissions.moderate_members:
                await interaction.response.send_message("Bạn không có quyền **Timeout Members** để sử dụng lệnh này.")
                return False
        elif required_perm == "kick":
            if not invoker.guild_permissions.kick_members:
                await interaction.response.send_message("Bạn không có quyền **Kick Members** để sử dụng lệnh này.")
                return False
        elif required_perm == "ban":
            if not invoker.guild_permissions.ban_members:
                await interaction.response.send_message("Bạn không có quyền **Ban Members** để sử dụng lệnh này.")
                return False

        if required_perm == "moderate":
            if not bot_member.guild_permissions.moderate_members:
                await interaction.response.send_message("Hãy cấp cho tôi quyền **Timeout Members** để sử dụng lệnh.")
                return False
        elif required_perm == "kick":
            if not bot_member.guild_permissions.kick_members:
                await interaction.response.send_message("Hãy cấp cho tôi quyền **Kick Members** để sử dụng lệnh.")
                return False
        elif required_perm == "ban":
            if not bot_member.guild_permissions.ban_members:
                await interaction.response.send_message("Hãy cấp cho tôi quyền **Ban Members** để sử dụng lệnh.")
                return False

        target_member = guild.get_member(target.id)
        if target_member is not None:
            if invoker.top_role <= target_member.top_role:
                await interaction.response.send_message("**Role của bạn phải cao hơn đối tượng** trong tham số.")
                return False

            if bot_member.top_role <= target_member.top_role:
                await interaction.response.send_message("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
                return False

        return True

    @moderation_group.command(name="warn", description="Cảnh cáo một người dùng")
    @app_commands.describe(
        user="Người dùng bị cảnh cáo",
        reason="Lí do cảnh cáo"
    )
    async def warn(self, interaction: discord.Interaction, user: discord.User, reason: str = None):
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã bị cảnh cáo tại {guild.name}.\n"
            f"- Lý do cảnh cáo: {reason}.\n"
            f"- Thời gian: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")

        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.response.send_message(
            f"**{user.display_name}** đã bị cảnh cáo với lí do: `{reason}`."
        )

    @moderation_group.command(name="timeout", description="Timeout một người dùng")
    @app_commands.describe(
        user="Người dùng bị timeout",
        duration="Thời gian timeout (ví dụ: 30s, 5m, 1h, 1w)",
        reason="Lí do timeout"
    )
    async def timeout(self, interaction: discord.Interaction, user: discord.User, duration: str, reason: str = None):
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        await interaction.response.defer()
        try:
            unit = duration[-1].lower()
            value = int(duration[:-1])
        except Exception:
            await interaction.followup.send("Định dạng thời gian không hợp lệ. Ví dụ: 30s, 5m, 1h, 1w.")
            return

        if unit not in {"s", "m", "h", "w"}:
            await interaction.followup.send("Đơn vị thời gian không hợp lệ. **Chỉ sử dụng s, m, h, hoặc w**.")
            return

        timeout_seconds = value * {"s": 1, "m": 60, "h": 3600, "w": 604800}[unit]
        if timeout_seconds > 604800:
            await interaction.followup.send("Thời gian timeout tối đa là **1 tuần**.")
            return

        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        utc_expiration_time = utc_now + datetime.timedelta(seconds=timeout_seconds)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_expiration = utc_expiration_time.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        display_expiration_ts = int(display_expiration.timestamp())

        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("Không tìm thấy thành viên trong server.")
            return

        try:
            await member.timeout(utc_expiration_time, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền **Timeout Members** để sử dụng lệnh.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"Không thể timeout thành viên: {e}")
            return

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã bị timeout tại {guild.name}.\n"
            f"- Lý do timeout: {reason}.\n"
            f"- Thời gian timeout: <t:{display_expiration_ts}:F>.\n"
            f"- Thời gian sử dụng lệnh: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        friendly_duration = f"{value} {unit_names[unit]}"
        await interaction.followup.send(
            f"**{user.display_name}** đã bị timeout trong **{friendly_duration}** với lí do: `{reason}`."
        )

    @moderation_group.command(name="untimeout", description="Gỡ timeout cho một người dùng")
    @app_commands.describe(
        user="Người dùng được gỡ timeout",
        reason="Lí do gỡ timeout (tùy chọn)"
    )
    async def untimeout(self, interaction: discord.Interaction, user: discord.User, reason: str = None):
        if not await self.check_all_permissions(interaction, user, "moderate"):
            return

        await interaction.response.defer()
        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("Không tìm thấy thành viên trong server.")
            return

        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền **Timeout Members** để sử dụng lệnh.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"Không thể gỡ timeout thành viên: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())

        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã được gỡ timeout tại {guild.name}.\n"
            f"- Lý do gỡ timeout: {reason}.\n"
            f"- Thời gian sử dụng lệnh: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** đã được gỡ timeout với lí do: `{reason}`."
        )

    @moderation_group.command(name="kick", description="Kick một người dùng")
    @app_commands.describe(
        user="Người dùng bị kick",
        reason="Lí do kick (tùy chọn)"
    )
    async def kick(self, interaction: discord.Interaction, user: discord.User, reason: str = None):
        if not await self.check_all_permissions(interaction, user, "kick"):
            return

        await interaction.response.defer()
        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        member = guild.get_member(user.id)
        if member is None:
            await interaction.followup.send("Không tìm thấy thành viên trong server.")
            return

        try:
            await member.kick(reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền **Kick Members** để sử dụng lệnh.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"Không thể kick: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã bị kick tại {guild.name}.\n"
            f"- Lý do kick: {reason}.\n"
            f"- Thời gian sử dụng lệnh: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** đã bị kick với lí do: `{reason}`."
        )

    @moderation_group.command(name="ban", description="Ban một người dùng")
    @app_commands.describe(
        user="Người dùng bị ban",
        reason="Lí do ban",
        delete_message="Thời gian xóa tin nhắn (ví dụ: 30s, 5m, 1h, 1w)"
    )
    async def ban(self, interaction: discord.Interaction, user: discord.User, reason: str = None, delete_message: str = None):
        if not await self.check_all_permissions(interaction, user, "ban"):
            return

        await interaction.response.defer()
        if not reason or reason.strip() == "":
            reason = "no reason"
        delete_message_days = 0
        if delete_message:
            try:
                unit = delete_message[-1].lower()
                value = int(delete_message[:-1])
            except Exception:
                await interaction.followup.send("Định dạng delete message không hợp lệ. **Ví dụ: 30s, 5m, 1h, 1w**.")
                return

            multipliers = {"s": 1, "m": 60, "h": 3600, "w": 604800}
            if unit not in multipliers:
                await interaction.followup.send("Đơn vị delete message không hợp lệ. **Chỉ sử dụng s, m, h, hoặc w**.")
                return

            delete_seconds = value * multipliers[unit]
            if delete_seconds > 604800:
                await interaction.followup.send("Thời gian xóa tin nhắn tối đa là **1 tuần**.")
                return
            delete_message_days = math.floor(delete_seconds / 86400)
        
        guild = interaction.guild
        try:
            await guild.ban(user, delete_message_days=delete_message_days, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền **Ban Members** để sử dụng lệnh.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"Không thể ban: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã bị ban tại {guild.name}.\n"
            f"- Lý do ban: {reason}.\n"
            f"- Thời gian sử dụng lệnh: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        friendly_delete = f" và xóa tin nhắn trong vòng **{delete_message_days} ngày**" if delete_message and delete_message_days > 0 else ""
        await interaction.followup.send(
            f"**{user.display_name}** đã bị ban{friendly_delete} với lí do: `{reason}`."
        )

    @moderation_group.command(name="unban", description="Unban một người dùng")
    @app_commands.describe(
        user="Người dùng được unban",
        reason="Lí do unban"
    )
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str = None):
        if not await self.check_all_permissions(interaction, user, "ban"):
            return

        await interaction.response.defer()
        if not reason or reason.strip() == "":
            reason = "no reason"

        guild = interaction.guild
        try:
            await guild.unban(user, reason=reason)
        except discord.Forbidden as e:
            error_str = str(e).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền **Ban Members** để sử dụng lệnh.")
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"Không thể unban thành viên: {e}")
            return

        utc_now = datetime.datetime.now(datetime.timezone.utc)
        display_now = utc_now.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        display_now_ts = int(display_now.timestamp())
        embed = discord.Embed(color=discord.Colour(0xFF0000))
        embed.description = (
            f"- Bạn đã được unban tại {guild.name}.\n"
            f"- Lý do unban: {reason}.\n"
            f"- Thời gian sử dụng lệnh: <t:{display_now_ts}:F>."
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        bot_avatar = interaction.client.user.avatar.url if interaction.client.user.avatar else None
        if bot_avatar:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}", icon_url=bot_avatar)
        else:
            embed.set_footer(text=f"Lệnh thực hiển bởi {interaction.user.display_name}")
        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            f"**{user.display_name}** đã được unban với lí do: `{reason}`."
        )

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.followup.send("Bạn không có quyền sử dụng lệnh này.")
        elif isinstance(error, discord.Forbidden):
            error_str = str(error).lower()
            if "hierarchy" in error_str:
                await interaction.followup.send("Hãy kiểm tra thứ hạng role của tôi trong cài đặt để đảm bảo **role của tôi phải cao hơn đối tượng** trong tham số.")
            else:
                await interaction.followup.send("Hãy cấp cho tôi quyền cần thiết để sử dụng lệnh.")
        else:
            raise error

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
