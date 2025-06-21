import discord
from discord.ext import commands
from discord import app_commands
import datetime
import re

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

def update_embed_placeholders(embed: discord.Embed, interaction: discord.Interaction) -> discord.Embed:
    if interaction.guild is None:
        return embed

    member = interaction.user
    guild = interaction.guild

    if embed.title:
        embed.title = replace_placeholders(embed.title, member, guild)
    if embed.description:
        embed.description = replace_placeholders(embed.description, member, guild)

    if embed.footer.text:
        new_footer_text = replace_placeholders(embed.footer.text, member, guild)
        new_footer_icon = safe_replace_url(embed.footer.icon_url, member, guild) if embed.footer.icon_url else None
        embed.set_footer(text=new_footer_text, icon_url=new_footer_icon)

    if embed.author.name:
        new_author_name = replace_placeholders(embed.author.name, member, guild)
        new_author_icon = safe_replace_url(embed.author.icon_url, member, guild) if embed.author.icon_url else None
        embed.set_author(name=new_author_name, icon_url=new_author_icon)

    if embed.thumbnail.url:
        new_thumbnail = safe_replace_url(embed.thumbnail.url, member, guild)
        if new_thumbnail is not None:
            embed.set_thumbnail(url=new_thumbnail)

    if embed.image.url:
        new_image = safe_replace_url(embed.image.url, member, guild)
        if new_image is not None:
            embed.set_image(url=new_image)
    
    return embed

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
            embed.description = f"Embed {data.get('name')} hiện đang trống. Để chỉnh sửa hãy ấn vào các nút bên dưới!"

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

class AuthorModal(discord.ui.Modal, title="Chỉnh sửa Author"):
    author_name = discord.ui.TextInput(
        label="Author", 
        placeholder="Author Text", 
        required=True
    )
    author_image = discord.ui.TextInput(
        label="Author Image", 
        placeholder="URL ảnh hoặc từ chìa khóa", 
        required=False
    )

    def __init__(self, name: str, guild_id: int, view: discord.ui.View, bot: commands.Bot):
        super().__init__()
        self.name = name
        self.guild_id = guild_id
        self.view = view
        self.bot = bot
        embed_data = self.bot.mongo_handler.db["embed"].find_one({"guild_id": self.guild_id, "name": self.name})
        if embed_data and embed_data.get("author"):
            self.author_name.default = embed_data["author"].get("name", "")
            self.author_image.default = embed_data["author"].get("icon_url", "")
    
    async def on_submit(self, interaction: discord.Interaction):
        collection = self.bot.mongo_handler.db["embed"]
        collection.update_one(
            {"guild_id": self.guild_id, "name": self.name},
            {"$set": {"author": {"name": self.author_name.value, "icon_url": self.author_image.value or None}}}
        )
        data = collection.find_one({"guild_id": self.guild_id, "name": self.name})
        new_embed = build_embed(data)
        new_embed = update_embed_placeholders(new_embed, interaction)
        await self.view.message.edit(embed=new_embed, view=self.view)
        await interaction.response.defer(ephemeral=True)

class BodyModal(discord.ui.Modal, title="Chỉnh sửa Body"):
    title_input = discord.ui.TextInput(
        label="Title", 
        placeholder="Nhập tiêu đề", 
        required=False
    )
    description_input = discord.ui.TextInput(
        label="Description", 
        placeholder="Nhập nội dung", 
        style=discord.TextStyle.paragraph,
        required=False
    )
    hex_color = discord.ui.TextInput(
        label="Hex Color", 
        placeholder="Nhập mã màu hex (vd: #FF0000)", 
        required=False
    )

    def __init__(self, name: str, guild_id: int, view: discord.ui.View, bot: commands.Bot):
        super().__init__()
        self.name = name
        self.guild_id = guild_id
        self.view = view
        self.bot = bot
        embed_data = self.bot.mongo_handler.db["embed"].find_one({"guild_id": self.guild_id, "name": self.name})
        if embed_data:
            self.title_input.default = embed_data.get("title", "")
            self.description_input.default = embed_data.get("description", "")
            if embed_data.get("color"):
                self.hex_color.default = f"#{embed_data['color']:06x}"
            else:
                self.hex_color.default = ""
    
    async def on_submit(self, interaction: discord.Interaction):
        collection = self.bot.mongo_handler.db["embed"]
        color_value = None
        if self.hex_color.value:
            try:
                hex_str = self.hex_color.value.lstrip('#')
                color_value = int(hex_str, 16)
            except ValueError:
                color_value = None
        update_data = {
            "title": self.title_input.value if self.title_input.value else None,
            "description": self.description_input.value if self.description_input.value else None,
            "color": color_value
        }
        collection.update_one(
            {"guild_id": self.guild_id, "name": self.name},
            {"$set": update_data}
        )
        data = collection.find_one({"guild_id": self.guild_id, "name": self.name})
        new_embed = build_embed(data)
        new_embed = update_embed_placeholders(new_embed, interaction)
        await self.view.message.edit(embed=new_embed, view=self.view)
        await interaction.response.defer(ephemeral=True)

class FooterModal(discord.ui.Modal, title="Chỉnh sửa Footer"):
    footer_text = discord.ui.TextInput(
        label="Footer Text", 
        placeholder="Nhập text cho footer", 
        required=False
    )
    footer_image = discord.ui.TextInput(
        label="Footer Image", 
        placeholder="URL ảnh hoặc từ chìa khóa", 
        required=False
    )
    timestamp_input = discord.ui.TextInput(
        label="Timestamp (Yes/No)", 
        placeholder="Nhập Yes để bật timestamp", 
        required=False
    )

    def __init__(self, name: str, guild_id: int, view: discord.ui.View, bot: commands.Bot):
        super().__init__()
        self.name = name
        self.guild_id = guild_id
        self.view = view
        self.bot = bot
        embed_data = self.bot.mongo_handler.db["embed"].find_one({"guild_id": self.guild_id, "name": self.name})
        if embed_data and embed_data.get("footer"):
            footer = embed_data["footer"]
            self.footer_text.default = footer.get("text", "")
            self.footer_image.default = footer.get("icon_url", "")
            self.timestamp_input.default = "Yes" if footer.get("timestamp") else "No"
    
    async def on_submit(self, interaction: discord.Interaction):
        collection = self.bot.mongo_handler.db["embed"]
        timestamp_enabled = False
        if self.timestamp_input.value and self.timestamp_input.value.lower() == "yes":
            timestamp_enabled = True
        update_data = {
            "footer": {
                "text": self.footer_text.value if self.footer_text.value else None,
                "icon_url": self.footer_image.value or None,
                "timestamp": timestamp_enabled
            }
        }
        collection.update_one(
            {"guild_id": self.guild_id, "name": self.name},
            {"$set": update_data}
        )
        data = collection.find_one({"guild_id": self.guild_id, "name": self.name})
        new_embed = build_embed(data)
        new_embed = update_embed_placeholders(new_embed, interaction)
        await self.view.message.edit(embed=new_embed, view=self.view)
        await interaction.response.defer(ephemeral=True)

class ImageModal(discord.ui.Modal, title="Chỉnh sửa Image"):
    small_image = discord.ui.TextInput(
        label="Small Image", 
        placeholder="URL ảnh hoặc từ chìa khóa", 
        required=False
    )
    big_image = discord.ui.TextInput(
        label="Big Image", 
        placeholder="URL ảnh hoặc từ chìa khóa", 
        required=False
    )

    def __init__(self, name: str, guild_id: int, view: discord.ui.View, bot: commands.Bot):
        super().__init__()
        self.name = name
        self.guild_id = guild_id
        self.view = view
        self.bot = bot
        embed_data = self.bot.mongo_handler.db["embed"].find_one({"guild_id": self.guild_id, "name": self.name})
        if embed_data:
            self.small_image.default = embed_data.get("thumbnail", "")
            self.big_image.default = embed_data.get("image", "")
    
    async def on_submit(self, interaction: discord.Interaction):
        collection = self.bot.mongo_handler.db["embed"]
        update_data = {
            "thumbnail": self.small_image.value or None,
            "image": self.big_image.value or None
        }
        collection.update_one(
            {"guild_id": self.guild_id, "name": self.name},
            {"$set": update_data}
        )
        data = collection.find_one({"guild_id": self.guild_id, "name": self.name})
        new_embed = build_embed(data)
        new_embed = update_embed_placeholders(new_embed, interaction)
        await self.view.message.edit(embed=new_embed, view=self.view)
        await interaction.response.defer(ephemeral=True)

class EmbedView(discord.ui.View):
    def __init__(self, name: str, guild_id: int, bot: commands.Bot):
        super().__init__(timeout=None)
        self.name = name
        self.guild_id = guild_id
        self.bot = bot
        self.message: discord.Message = None

    @discord.ui.button(label="Author", style=discord.ButtonStyle.secondary, custom_id="embed_author")
    async def author_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AuthorModal(self.name, self.guild_id, self, self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Body (Title, Description,...)", style=discord.ButtonStyle.secondary, custom_id="embed_body")
    async def body_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = BodyModal(self.name, self.guild_id, self, self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Footer", style=discord.ButtonStyle.secondary, custom_id="embed_footer")
    async def footer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = FooterModal(self.name, self.guild_id, self, self.bot)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Image", style=discord.ButtonStyle.secondary, custom_id="embed_image")
    async def image_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ImageModal(self.name, self.guild_id, self, self.bot)
        await interaction.response.send_modal(modal)

class EmbedCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _check_permissions(self, interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        if not (perms.manage_guild and perms.manage_channels):
            await interaction.response.send_message(
                "<:x_:1335734856734347355> **|** Bạn thiếu quyền: Manage Guild và Manage Channels",
                ephemeral=True
            )
            return False
        return True

    embed_group = app_commands.Group(name="embed", description="Các lệnh liên quan đến Embed")

    @embed_group.command(name="create", description="Tạo embed mới")
    @app_commands.describe(name="Đặt tên cho embed")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def create_embed(self, interaction: discord.Interaction, name: str):
        if not await self._check_permissions(interaction):
            return
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh chỉ có thể sử dụng trong server.", ephemeral=True)
            return

        collection = self.bot.mongo_handler.db["embed"]
        existing = collection.find_one({"guild_id": guild_id, "name": name})
        if existing:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Embed đã tồn tại.", ephemeral=True)
            return

        default_data = {
            "guild_id": guild_id,
            "name": name,
            "author": None,
            "title": None,
            "description": None,
            "color": None,
            "footer": None,
            "thumbnail": None,
            "image": None
        }
        collection.insert_one(default_data)
        embed = build_embed(default_data)
        embed = update_embed_placeholders(embed, interaction)
        view = EmbedView(name, guild_id, self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg

    @embed_group.command(name="edit", description="Chỉnh sửa embed đã tạo")
    @app_commands.describe(name="Chọn embed cần chỉnh sửa")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def edit_embed(self, interaction: discord.Interaction, name: str):
        if not await self._check_permissions(interaction):
            return
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        collection = self.bot.mongo_handler.db["embed"]
        doc = collection.find_one({"guild_id": guild_id, "name": name})
        if not doc:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Không tìm thấy embed với tên này.", ephemeral=True)
            return
        embed = build_embed(doc)
        embed = update_embed_placeholders(embed, interaction)
        view = EmbedView(name, guild_id, self.bot)
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        view.message = msg

    @embed_group.command(name="delete", description="Xóa một embed")
    @app_commands.describe(name="Chọn embed cần xóa")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def delete_embed(self, interaction: discord.Interaction, name: str):
        if not await self._check_permissions(interaction):
            return
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        collection = self.bot.mongo_handler.db["embed"]
        result = collection.delete_one({"guild_id": guild_id, "name": name})
        if result.deleted_count > 0:
            await interaction.response.send_message("<:check_mark:1335734939185975378> **|** Embed đã được xóa.", ephemeral=True)
        else:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Không tìm thấy embed nào với tên này.", ephemeral=True)

    @embed_group.command(name="list", description="Danh sách embed đã tạo")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def list_embed(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh chỉ có thể sử dụng trong server.", ephemeral=True)
            return
        collection = self.bot.mongo_handler.db["embed"]
        docs = list(collection.find({"guild_id": guild_id}))
        count = len(docs)
        if count == 0:
            await interaction.response.send_message("<:warning:1335735040692322315> **|** Hãy tạo embed để dùng lệnh này!", ephemeral=True)
            return
        embed_names = [doc.get("name") for doc in docs if doc.get("name")]
        embed_desc = "\n".join(embed_names)
        list_embed = discord.Embed(title="Embed List", description=embed_desc, color=discord.Color(int("FFCCFF", 16)))
        if interaction.guild.icon is not None:
            list_embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url)
        else:
            list_embed.set_author(name=interaction.guild.name)
        list_embed.set_footer(text=f"Tổng {count} embeds")
        await interaction.response.send_message(embed=list_embed)

    @embed_group.command(name="key", description="Danh sách từ khóa embed")
    @app_commands.default_permissions(manage_guild=True, manage_channels=True)
    async def key(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("<:x_:1335734856734347355> **|** Lệnh này chỉ có thể sử dụng trong server.")
            return
        replacements = {
            "{user}": "Mention người dùng",
            "{user_tag}": "Nickname của người dùng",
            "{user_avatar}": "Avatar của người dùng",
            "{server_name}": "Tên server",
            "{server_membercount}": "Số lượng thành viên trong server",
            "{server_avatar}": "Avatar của server"
        }
        description_lines = [f"**{key}** - **{value}**" for key, value in replacements.items()]
        description = "\n".join(description_lines)
        key_count = len(replacements)
        embed = discord.Embed(
            title="Từ khóa embed",
            description=description,
            color=discord.Color(int("FFCCFF", 16))
        )
        if guild.icon:
            embed.set_author(name=guild.name, icon_url=guild.icon.url)
        else:
            embed.set_author(name=guild.name)
        embed.set_footer(text=f"Tổng {key_count} key")
        await interaction.response.send_message(embed=embed)

    @delete_embed.autocomplete("name")
    async def delete_embed_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            return []
        collection = self.bot.mongo_handler.db["embed"]
        docs = collection.find({"guild_id": guild_id})
        choices = []
        for doc in docs:
            embed_name = doc.get("name")
            if embed_name and current.lower() in embed_name.lower():
                choices.append(app_commands.Choice(name=embed_name, value=embed_name))
        return choices[:25]

    @edit_embed.autocomplete("name")
    async def edit_embed_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else None
        if not guild_id:
            return []
        collection = self.bot.mongo_handler.db["embed"]
        docs = collection.find({"guild_id": guild_id})
        choices = []
        for doc in docs:
            embed_name = doc.get("name")
            if embed_name and current.lower() in embed_name.lower():
                choices.append(app_commands.Choice(name=embed_name, value=embed_name))
        return choices[:25]

async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedCommands(bot))
