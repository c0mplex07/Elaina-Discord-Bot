# ====================== IMPORTS ==============================
import os
import logging
import asyncio
from typing import Optional, Union

import discord
from discord.ext import commands, tasks
from discord import Activity, ActivityType
from dotenv import load_dotenv
from pymongo import MongoClient
from utils.mongo_handler import MongoHandler
# ============================================================

# ====================== ENVIRONMENT LOADING =================
def get_env_var(name, default=None, required=False, cast_type=None):
    """Lấy biến môi trường an toàn với ép kiểu và kiểm tra bắt buộc."""
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    if cast_type and value is not None:
        try:
            value = cast_type(value)
        except Exception:
            raise RuntimeError(f"Environment variable {name} must be of type {cast_type.__name__}")
    return value

load_dotenv()

TOKEN = get_env_var('DISCORD_BOT_TOKEN', required=True, cast_type=str)
MONGO_URI = get_env_var('MONGO_URI', required=True, cast_type=str)
ADMIN_UID = get_env_var('ADMIN_UID', required=True, cast_type=int)
LOG_CHANNEL_ID = get_env_var('LOG_CHANNEL_ID', required=True, cast_type=int)
LOG_CHANNEL_ID2 = get_env_var('LOG_CHANNEL_ID2', required=True, cast_type=int)
TARGET_CHANNEL_ID = get_env_var('TARGET_CHANNEL_ID', default=0, cast_type=int)
# ============================================================

# ====================== LOGGING CONFIG ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)
# ============================================================

# ====================== BOT CONFIG ==========================
ACTIVITIES = [
    "https://dsc.gg/elaina-support"
]
# ============================================================

# ====================== CUSTOM BOT CLASS ====================
class CustomBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_handler: Union[MongoHandler, None] = None
# ============================================================

# ====================== BOT INITIALIZATION ==================
bot = CustomBot(
    command_prefix='eac',
    help_command=None,
    intents=discord.Intents.all(),
    activity=Activity(type=ActivityType.listening, name="Khởi động...")
)

if MONGO_URI is None or LOG_CHANNEL_ID2 is None:
    raise RuntimeError("MONGO_URI and LOG_CHANNEL_ID2 must not be None")
bot.mongo_handler = MongoHandler(str(MONGO_URI), "enoubot", bot, int(LOG_CHANNEL_ID2))
# ============================================================

# ====================== BACKGROUND TASKS ====================
@tasks.loop(seconds=5.0)
async def change_activity():
    """Thay đổi activity của bot mỗi 5 giây."""
    if not bot.is_ready():
        return
    total_servers = len(bot.guilds)
    total_members = sum((guild.member_count or 0) for guild in bot.guilds)
    activity_content = ACTIVITIES[change_activity.current_loop % len(ACTIVITIES)]
    activity_content = activity_content.format(
        total_servers=total_servers,
        total_members=total_members
    )
    await bot.change_presence(
        status=discord.Status.idle,
        activity=Activity(
            type=ActivityType.listening,
            name=activity_content,
            state=f"{total_servers} Servers, {total_members} Members"
        )
    )

@tasks.loop(seconds=30.0)
async def keep_mongo_connection():
    """Ping MongoDB mỗi 30 giây để giữ kết nối."""
    mongo_handler = getattr(bot, 'mongo_handler', None)
    if mongo_handler is not None and hasattr(mongo_handler, 'client') and mongo_handler.client is not None:
        try:
            mongo_handler.client.admin.command('ping')
        except Exception as e:
            logger.error(f"MongoDB connection lost: {e}. Reconnecting...")
            if hasattr(mongo_handler, 'reconnect'):
                await mongo_handler.reconnect()
# ============================================================

# ====================== BOT EVENTS ==========================
@bot.event
async def on_ready():
    """Sự kiện khi bot sẵn sàng."""
    await bot.tree.sync()
    if bot.user:
        await log_to_channel(f"✅ Bot logged in as {bot.user} (ID: {bot.user.id})")
        logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")
    else:
        await log_to_channel("✅ Bot logged in (user unknown)")
        logger.info("Bot logged in (user unknown)")
    change_activity.start()
    keep_mongo_connection.start()

@bot.event
async def on_message(message):
    """Xử lý tin nhắn gửi đến bot."""
    if message.author.bot or message.mention_everyone or message.role_mentions:
        return
    if bot.user in message.mentions and len(message.mentions) == 1:
        await handle_bot_mention(message)
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
    """Sự kiện khi bot được thêm vào server mới."""
    if TARGET_CHANNEL_ID:
        try:
            invite = await guild.text_channels[0].create_invite(max_age=0, max_uses=0)
            await log_to_channel(
                f"Added to **{guild.name}**\n{invite.url}", 
                channel_id=TARGET_CHANNEL_ID
            )
        except Exception as e:
            logger.error(f"Failed to create invite: {str(e)}")

@bot.event
async def on_interaction(interaction):
    """Xử lý các interaction (slash command, v.v.)."""
    if interaction.type == discord.InteractionType.application_command:
        if await is_user_banned(interaction.user.id):
            await interaction.response.send_message("❌ Tài khoản của bạn đã bị cấm sử dụng bot", ephemeral=True)
# ============================================================

# ====================== HELPER FUNCTIONS =====================
async def handle_bot_mention(message):
    """Trả lời khi bot bị mention."""
    image_url = "https://c.tenor.com/Hpd6ebmlWHMAAAAC/tenor.gif"
    embed = discord.Embed(
        description=(
            f"Xin chào {message.author.mention}! Tớ là Elaina sinh ngày 17/10 tới từ Robetta.\n"
            "Pháp hiệu của tớ là Phù thuỷ Tro tàn, hiện tại tớ đang là một lữ khách lang thang."
        ),
        color=0xffb0f7
    )
    embed.set_image(url=image_url)
    await message.reply(embed=embed, delete_after=15)

async def log_to_channel(content, channel_id=LOG_CHANNEL_ID):
    """Gửi log tới kênh chỉ định."""
    if channel_id is None:
        return
    channel = bot.get_channel(int(channel_id))
    from discord import TextChannel
    if isinstance(channel, TextChannel):
        try:
            await channel.send(content)
        except Exception as e:
            logger.error(f"Failed to log to channel: {str(e)}")

async def reload_single_cog(cog_path):
    """Reload một cog cụ thể."""
    try:
        if cog_path in bot.extensions:
            await bot.reload_extension(cog_path)
        else:
            await bot.load_extension(cog_path)
        return (True, f"✅ Reloaded: `{cog_path}`")
    except Exception as e:
        return (False, f"❌ Failed `{cog_path}`: {str(e)}")

def format_reload_results(results):
    """Định dạng kết quả reload nhiều cog."""
    return "\n".join([msg for ok, msg in results])

async def is_user_banned(user_id):
    """Kiểm tra user có bị ban không."""
    mongo_handler = getattr(bot, 'mongo_handler', None)
    if mongo_handler is None:
        return False
    user_data = await bot.loop.run_in_executor(None, mongo_handler.get_user_data, str(user_id))
    return user_data.get('banned', False)

# ====================== LOAD INITIAL COGS ====================
async def load_initial_cogs():
    initial_cogs = ['cmd.group.embed_commands', 'cmd.group.greet_commands',
                    'cmd.group.moderation_commands',
                    
                    'cmd.script.greet_script', 'cmd.script.leave_script',
                    
                    'cmd.single.weather', 'cmd.single.chat', 'cmd.single.userinfo',
                    'cmd.single.replay', 'cmd.single.serverinfo', 'cmd.single.ping',
                    'cmd.single.about'
                    ]
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}")
            await log_to_channel(f"❌ Failed to load {cog}: {e}")
# ============================================================

# ====================== MAIN EXECUTION =======================
async def main():
    await load_initial_cogs()
    try:
        if not isinstance(TOKEN, str) or not TOKEN:
            raise RuntimeError("DISCORD_BOT_TOKEN is missing or invalid")
        await bot.start(str(TOKEN))
    except KeyboardInterrupt:
        pass
    finally:
        mongo_handler = getattr(bot, 'mongo_handler', None)
        if mongo_handler:
            mongo_handler.close_connection()
        await log_to_channel("❌ Bot stopped")
        logger.info("Bot stopped")

if __name__ == '__main__':
    asyncio.run(main())
# ============================================================