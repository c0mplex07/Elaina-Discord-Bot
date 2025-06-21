import discord
from discord.ext import commands
from discord import app_commands
import re
import datetime

def build_embed(data: dict) -> discord.Embed:
    embed = discord.Embed()
    if data.get("author") is not None and data["author"].get("name") is not None:
        embed.set_author(name=data["author"]["name"], icon_url=data["author"].get("icon_url"))
    else:
        if (data.get("title") is not None or data.get("description") is not None or
            data.get("footer") is not None or data.get("thumbnail") is not None or
            data.get("image") is not None):
            embed.set_author(name="")
        else:
            embed.set_author(name="Embed Trống")
    if data.get("title"):
        embed.title = data.get("title")
    if data.get("description") is not None:
        embed.description = data.get("description")
    else:
        if (data.get("author") is not None or data.get("title") is not None or
            data.get("footer") is not None or data.get("thumbnail") is not None or
            data.get("image") is not None):
            embed.description = ""
        else:
            embed.description = f"Embed `{data.get('name')}` hiện đang trống. Để chỉnh sửa hãy ấn vào các nút bên dưới!"
    if data.get("color"):
        embed.color = data.get("color")
    if data.get("footer") and data["footer"].get("text"):
        embed.set_footer(text=data["footer"]["text"], icon_url=data["footer"].get("icon_url"))
        if data["footer"].get("timestamp"):
            embed.timestamp = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    if data.get("thumbnail"):
        embed.set_thumbnail(url=data.get("thumbnail"))
    if data.get("image"):
        embed.set_image(url=data.get("image"))
    return embed

def get_embeds_from_placeholders(text: str, guild_id: int, mongo_handler) -> list:
    pattern = r"\{embed:([^}]+)\}"
    matches = re.findall(pattern, text)
    embeds = []
    for embed_name in matches:
        query = {
            "guild_id": guild_id,
            "name": {"$regex": f"^{re.escape(embed_name)}$", "$options": "i"}
        }
        doc = mongo_handler.db["embed"].find_one(query)
        if doc:
            embeds.append(build_embed(doc))
    return embeds

def replace_placeholders(text: str, member: discord.Member, guild: discord.Guild) -> str:
    if not text:
        return text
    replacements = {
        "{user}": member.mention,
        "{user_tag}": member.display_name,
        "{user_avatar}": member.display_avatar.url,
        "{server_name}": guild.name,
        "{server_membercount}": str(guild.member_count),
        "{server_avatar}": guild.icon.url if guild.icon else ""
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text

def safe_replace_url(url: str, member: discord.Member, guild: discord.Guild) -> str:
    try:
        new_url = replace_placeholders(url, member, guild)
        if new_url.startswith("http://") or new_url.startswith("https://"):
            return new_url
        else:
            return None
    except Exception:
        return None

def update_embed_placeholders(embed: discord.Embed, member: discord.Member, guild: discord.Guild) -> discord.Embed:
    if embed.title:
        embed.title = replace_placeholders(embed.title, member, guild)
    if embed.description:
        embed.description = replace_placeholders(embed.description, member, guild)
    
    if embed.author.name:
        new_author_name = replace_placeholders(embed.author.name, member, guild)
        new_author_icon = safe_replace_url(embed.author.icon_url, member, guild) if embed.author.icon_url else None
        embed.set_author(name=new_author_name, icon_url=new_author_icon)
    
    if embed.footer.text:
        new_footer_text = replace_placeholders(embed.footer.text, member, guild)
        new_footer_icon = safe_replace_url(embed.footer.icon_url, member, guild) if embed.footer.icon_url else None
        embed.set_footer(text=new_footer_text, icon_url=new_footer_icon)
    
    if embed.thumbnail.url:
        new_thumbnail = safe_replace_url(embed.thumbnail.url, member, guild)
        if new_thumbnail:
            embed.set_thumbnail(url=new_thumbnail)
    
    if embed.image.url:
        new_image = safe_replace_url(embed.image.url, member, guild)
        if new_image:
            embed.set_image(url=new_image)
    
    return embed

class GreetingModal(discord.ui.Modal, title="Chỉnh Sửa Tin Nhắn"):
    def __init__(self, guild_id: int, default_message: str, collection):
        super().__init__()
        self.guild_id = guild_id
        self.collection = collection
        self.greeting_input = discord.ui.TextInput(
            label="Nhập Tin Nhắn",
            style=discord.TextStyle.long,
            default=default_message,
            required=True,
            max_length=2000
        )
        self.add_item(self.greeting_input)

    async def on_submit(self, interaction: discord.Interaction):
        new_message = self.greeting_input.value
        self.collection.update_one(
            {"_id": self.guild_id},
            {"$set": {"message": new_message}},
            upsert=True
        )
        await interaction.response.send_message("<:check_mark:1335734939185975378> **|** Tin nhắn đã được cập nhật.", ephemeral=True)

class Greeting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.collection = self.bot.mongo_handler.db["greeting"]

    greeting_group = app_commands.Group(name="greet", description="Commands related to greet")
    
    async def _check_permissions(self, interaction: discord.Interaction):
        perms = interaction.user.guild_permissions
        if not (perms.manage_guild and perms.manage_channels):
            await interaction.response.send_message(
                "<:x_:1335734856734347355> **|** Bạn thiếu quyền: `Manage Guild` và `Manage Channels`",
                ephemeral=True
            )
            raise app_commands.CheckFailure("Thiếu quyền")

    @greeting_group.command(name="message", description="Set or edit greet message")
    @app_commands.describe(message="Set greet message")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def message(self, interaction: discord.Interaction, message: str = None):
        await self._check_permissions(interaction)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh này chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        if message:
            self.collection.update_one(
                {"_id": guild.id},
                {"$set": {"message": message}},
                upsert=True
            )
            await interaction.response.send_message("<:check_mark:1335734939185975378> **|** Tin nhắn đã được lưu.", ephemeral=True)
        else:
            doc = self.collection.find_one({"_id": guild.id})
            default_message = doc.get("message", "") if doc else ""
            modal = GreetingModal(guild_id=guild.id, default_message=default_message, collection=self.collection)
            await interaction.response.send_modal(modal)

    @greeting_group.command(name="channel", description="Set or edit greet channel")
    @app_commands.describe(channel="Set greet channel")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def greeting_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        await self._check_permissions(interaction)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh này chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        self.collection.update_one(
            {"_id": guild.id},
            {"$set": {"channel_id": channel.id}},
            upsert=True
        )
        await interaction.response.send_message(f"<:check_mark:1335734939185975378> **|** {channel.mention} đã được lưu.", ephemeral=True)

    @greeting_group.command(name="test", description="Greeting test")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def test(self, interaction: discord.Interaction):
        await self._check_permissions(interaction)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh này chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        doc = self.collection.find_one({"_id": guild.id})
        if doc is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Chưa có greet nào được thiết lập.", ephemeral=True)
            return
        channel_id = doc.get("channel_id")
        greeting_message = doc.get("message")
        if not channel_id or not greeting_message:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Greet chưa được thiết lập đầy đủ.", ephemeral=True)
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Channel được thiết lập không còn tồn tại hoặc không hợp lệ.", ephemeral=True)
            return

        greeting_message = greeting_message.replace("{user}", interaction.user.mention)
        greeting_message = greeting_message.replace("{user_tag}", interaction.user.display_name)
        greeting_message = greeting_message.replace("{user_avatar}", interaction.user.display_avatar.url)
        greeting_message = greeting_message.replace("{server_name}", guild.name)
        greeting_message = greeting_message.replace("{server_membercount}", str(guild.member_count))
        greeting_message = greeting_message.replace("{server_avatar}", guild.icon.url if guild.icon else "")
        
        embeds = get_embeds_from_placeholders(greeting_message, guild.id, self.bot.mongo_handler)
        updated_embeds = [update_embed_placeholders(embed, interaction.user, guild) for embed in embeds]
        greeting_message = re.sub(r"\{embed:[^}]+\}", "", greeting_message)
        
        try:
            if greeting_message.strip():
                await channel.send(
                    content=greeting_message.strip(),
                    embeds=updated_embeds if updated_embeds else None,
                    allowed_mentions=discord.AllowedMentions(roles=True, users=True)
                )
            else:
                if updated_embeds:
                    await channel.send(
                        embeds=updated_embeds,
                        allowed_mentions=discord.AllowedMentions(roles=True, users=True)
                    )
            await interaction.response.send_message("<:check_mark:1335734939185975378> **|** Tin nhắn đã được gửi.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Đã có lỗi xảy ra khi gửi tin nhắn.", ephemeral=True)

    @greeting_group.command(name="clear", description="Delete greet data (message, channel id, server id)")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def greeting_clear(self, interaction: discord.Interaction):
        await self._check_permissions(interaction)
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh này chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        result = self.collection.update_one(
            {"_id": guild.id},
            {"$unset": {"message": "", "channel_id": "", "server_id": ""}}
        )
        if result.modified_count > 0:
            await interaction.response.send_message("<:check_mark:1335734939185975378> **|** Đã xóa thông tin Greeting của server.", ephemeral=True)
        else:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Không có thông tin Greeting nào để xóa.", ephemeral=True)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
            return
        else:
            raise error

async def setup(bot):
    await bot.add_cog(Greeting(bot))
