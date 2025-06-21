import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View
import aiohttp
import io

TARGET_CHANNEL_ID = 1337696927642423388

class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='avatar', description="Lấy avatar và banner người khác")
    @app_commands.describe(member="Lấy avatar và banner người khác")
    async def avatar(self, ctx: commands.Context, member: discord.Member = None):
        user_data = await self.bot.loop.run_in_executor(
            None, self.bot.mongo_handler.get_user_data, str(ctx.author.id)
        )
        if user_data.get('banned', False):
            return

        if member is None:
            member = ctx.author

        if member.avatar:
            is_animated_avatar = member.avatar.is_animated()
            avatar_format = "gif" if is_animated_avatar else "png"
            avatar_url = member.avatar.replace(format=avatar_format, size=1024).url
        else:
            avatar_url = member.default_avatar.url
            is_animated_avatar = False

        req = await self.bot.http.request(discord.http.Route("GET", f"/users/{member.id}"))
        banner_id = req.get("banner")
        banner_url = None
        is_animated_banner = False

        if banner_id:
            is_animated_banner = banner_id.startswith("a_")
            banner_format = "gif" if is_animated_banner else "png"
            banner_url = f"https://cdn.discordapp.com/banners/{member.id}/{banner_id}?size=1024&format={banner_format}"

        target_channel = self.bot.get_channel(TARGET_CHANNEL_ID)
        if not target_channel:
            await ctx.send("<:x_:1335734856734347355> **|** Lỗi: Không tìm thấy kênh đích!")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status != 200:
                    await ctx.send("<:x_:1335734856734347355> **|** Lỗi khi tải avatar!")
                    return
                avatar_data = await resp.read()
                avatar_ext = "gif" if is_animated_avatar else "png"
                avatar_file = discord.File(io.BytesIO(avatar_data), filename=f"avatar.{avatar_ext}")
                avatar_msg = await target_channel.send(file=avatar_file)
                avatar_link = avatar_msg.attachments[0].url if avatar_msg.attachments else None

            banner_link = None
            if banner_url:
                async with session.get(banner_url) as resp:
                    if resp.status == 200:
                        banner_data = await resp.read()
                        banner_ext = "gif" if is_animated_banner else "png"
                        banner_file = discord.File(io.BytesIO(banner_data), filename=f"banner.{banner_ext}")
                        banner_msg = await target_channel.send(file=banner_file)
                        if banner_msg.attachments:
                            banner_link = banner_msg.attachments[0].url

        embed = discord.Embed(title=f"Avatar của {member}", color=0x00ff00)
        embed.set_image(url=avatar_link)
        embed.add_field(name="Avatar Link", value=f"[Click here]({avatar_link})", inline=False)
        if banner_link:
            embed.add_field(name="Banner Link", value=f"[Click here]({banner_link})", inline=False)
        else:
            embed.add_field(name="Banner", value="Không có banner", inline=False)

        async def avatar_callback(interaction: discord.Interaction):
            user_data = await self.bot.loop.run_in_executor(
                None, self.bot.mongo_handler.get_user_data, str(interaction.user.id)
            )
            if user_data.get('banned', False):
                return

            embed.set_image(url=avatar_link)
            embed.title = f"Avatar của {member}"
            await interaction.response.edit_message(embed=embed)

        async def banner_callback(interaction: discord.Interaction):
            user_data = await self.bot.loop.run_in_executor(
                None, self.bot.mongo_handler.get_user_data, str(interaction.user.id)
            )
            if user_data.get('banned', False):
                return

            if banner_link:
                embed.set_image(url=banner_link)
                embed.title = f"Banner của {member}"
                await interaction.response.edit_message(embed=embed)
            else:
                await interaction.response.send_message("<:x_:1335734856734347355> **|** Không có banner!", ephemeral=True)

        view = View(timeout=60)

        avatar_button = Button(label="Avatar", style=discord.ButtonStyle.green)
        avatar_button.callback = avatar_callback
        view.add_item(avatar_button)

        banner_button = Button(label="Banner", style=discord.ButtonStyle.blurple)
        banner_button.callback = banner_callback
        view.add_item(banner_button)

        await ctx.send(embed=embed, view=view)

async def setup(bot: commands.Bot):
    await bot.add_cog(Avatar(bot))
