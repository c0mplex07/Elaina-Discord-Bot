import discord
from discord.ext import commands
import re
import datetime

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
            embed = build_embed(doc)
            embeds.append(embed)
    return embeds

class GreetingScript(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.collection = self.bot.mongo_handler.db["greeting"]

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        doc = self.collection.find_one({"_id": guild.id})
        if not doc:
            return

        channel_id = doc.get("channel_id")
        greeting_message = doc.get("message")
        if not channel_id or not greeting_message:
            return

        channel = guild.get_channel(channel_id)
        if channel is None:
            return

        greeting_message = greeting_message.replace("{user}", member.mention)
        greeting_message = greeting_message.replace("{user_tag}", member.display_name)
        greeting_message = greeting_message.replace("{user_avatar}", member.display_avatar.url)
        greeting_message = greeting_message.replace("{server_name}", guild.name)
        greeting_message = greeting_message.replace("{server_membercount}", str(guild.member_count))
        greeting_message = greeting_message.replace("{server_avatar}", guild.icon.url if guild.icon else "")

        embeds = get_embeds_from_placeholders(greeting_message, guild.id, self.bot.mongo_handler)
        updated_embeds = [update_embed_placeholders(embed, member, guild) for embed in embeds]

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
        except Exception as e:
            print(f"Lỗi khi gửi tin nhắn greeting tại guild {guild.id}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(GreetingScript(bot))
