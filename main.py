import discord
from discord.ext import commands, tasks
from discord import Activity, ActivityType
import logging
import asyncio
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from utils.mongo_handler import MongoHandler

# ====================== LOAD ENVIRONMENT ======================
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
ADMIN_UID = int(os.getenv('ADMIN_UID'))
LOG_CHANNEL_ID = int(os.getenv('LOG_CHANNEL_ID'))
LOG_CHANNEL_ID2 = int(os.getenv('LOG_CHANNEL_ID2'))
TARGET_CHANNEL_ID = int(os.getenv('TARGET_CHANNEL_ID', 0))

ACTIVITIES = [
    "Nhắn 'ehelp' để xem lệnh",
    "https://dsc.gg/enousupport"
]
DEFAULT_PREFIXES = ['e', 'E']
# ===============================================================

# ====================== CONFIGURE LOGGING ======================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)
# ===============================================================

# ====================== UTILITY FUNCTIONS ======================
def get_prefix(_bot, message):
    custom_prefix = _bot.prefixes.get(message.guild.id) if message.guild else None
    return DEFAULT_PREFIXES + [custom_prefix] if custom_prefix else DEFAULT_PREFIXES
# ===============================================================

# ====================== BOT INITIALIZATION =====================
bot = commands.Bot(
    command_prefix=get_prefix,
    help_command=None,
    intents=discord.Intents.all(),
    activity=Activity(type=ActivityType.listening, name="Khởi động...")
)

bot.mongo_handler = MongoHandler(MONGO_URI, "enoubot", bot, LOG_CHANNEL_ID2)
# ===============================================================

# ====================== BACKGROUND TASKS =======================
@tasks.loop(seconds=5.0)
async def change_activity():
    if not bot.is_ready():
        return

    total_servers = len(bot.guilds)
    total_members = sum(guild.member_count for guild in bot.guilds)
    
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
    try:
        bot.mongo_handler.client.admin.command('ping')
    except Exception as e:
        logger.error(f"MongoDB connection lost: {e}. Reconnecting...")
        await bot.mongo_handler.reconnect()
# ===============================================================

# ====================== BOT EVENTS ============================
@bot.event
async def on_ready():
    await bot.tree.sync()
    await log_to_channel(f"✅ Bot logged in as {bot.user} (ID: {bot.user.id})")
    logger.info(f"Bot logged in as {bot.user} (ID: {bot.user.id})")

    change_activity.start()
    keep_mongo_connection.start()

@bot.event
async def on_message(message):
    if message.author.bot or message.mention_everyone or message.role_mentions:
        return
        
    if await is_user_banned(message.author.id):
        return
        
    if bot.user in message.mentions and len(message.mentions) == 1:
        await handle_bot_mention(message)
        
    await bot.process_commands(message)

@bot.event
async def on_guild_join(guild):
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
    if interaction.type == discord.InteractionType.application_command:
        if await is_user_banned(interaction.user.id):
            await interaction.response.send_message("❌ Tài khoản của bạn đã bị cấm sử dụng bot", ephemeral=True)
# ===============================================================

# ====================== DEVELOPER COMMANDS =========================
@bot.command(name="reload")
async def reload_cog(ctx, cog_name: str = "all"):
    if not await is_admin(ctx):
        return
        
    if cog_name.lower() == "all":
        results = [await reload_single_cog(cog) for cog in list(bot.extensions.keys())]
        await ctx.reply(format_reload_results(results))
    else:
        result = await reload_single_cog(f"cogs.{cog_name}")
        await ctx.reply(result[1])

@bot.command(name="sync")
async def sync_commands(ctx):
    if not await is_admin(ctx):
        return
        
    try:
        synced = await bot.tree.sync()
        await ctx.reply(f"✅ Synced {len(synced)} commands")
    except Exception as e:
        await ctx.reply(f"❌ Sync failed: {e}")

@bot.command(name="list_cogs")
async def list_cogs(ctx):
    if not await is_admin(ctx):
        return
        
    cogs = "\n".join(bot.extensions.keys())
    await ctx.reply(f"📜 Loaded cogs:\n```{cogs}```")
# ===============================================================

# ====================== HELPER FUNCTIONS =======================
async def is_admin(ctx):
    if ctx.author.id != ADMIN_UID:
        await ctx.reply("❌ Permission denied")
        return False
    return True

async def is_user_banned(user_id):
    user_data = await bot.loop.run_in_executor(None, bot.mongo_handler.get_user_data, str(user_id))
    return user_data.get('banned', False)

async def handle_bot_mention(message):
    embed = discord.Embed(
        description=(
            f"Xin chào {message.author.mention}! Tớ là Enou, prefix: `e`/`E`\n"
            "Nhắn `ehelp` để xem lệnh <:heart:1335171872404537384>"
        ),
        color=0x00FF00
    )
    await message.reply(embed=embed, delete_after=15)

async def log_to_channel(content, channel_id=LOG_CHANNEL_ID):
    channel = bot.get_channel(channel_id)
    if channel:
        try:
            await channel.send(content)
        except Exception as e:
            logger.error(f"Failed to log to channel: {str(e)}")

async def reload_single_cog(cog_path):
    try:
        if cog_path in bot.extensions:
            await bot.reload_extension(cog_path)
        else:
            await bot.load_extension(cog_path)
        return (True, f"✅ Reloaded: `{cog_path}`")
    except Exception as e:
        return (False, f"❌ Failed `{cog_path}`: {str(e)}")

def format_reload_results(results):
    success = [r[1] for r in results if r[0]]
    failed = [r[1] for r in results if not r[0]]
    
    msg = "**Reload Results:**\n"
    msg += "\n".join(success) + "\n\n"
    msg += "**Failures:**\n" + "\n".join(failed) if failed else "✅ All cogs reloaded"
    return msg

async def load_initial_cogs():
    initial_cogs = ['cmd.group.embed_commands']
    
    for cog in initial_cogs:
        try:
            await bot.load_extension(cog)
            logger.info(f"✅ Loaded cog: {cog}")
        except Exception as e:
            logger.error(f"❌ Failed to load {cog}: {e}")
            await log_to_channel(f"❌ Failed to load {cog}: {e}")
# ===============================================================

# ====================== MAIN EXECUTION =========================
async def main():
    await load_initial_cogs()
    try:
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        pass
    finally:
        bot.mongo_handler.close_connection()
        await log_to_channel("❌ Bot stopped")
        logger.info("Bot stopped")

if __name__ == '__main__':
    asyncio.run(main())