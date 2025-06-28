import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import datetime

afks = {}

class AFK(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="afk", description="Set your AFK status.")
    @app_commands.describe(
        reason="Reason for going AFK",
        global_="Global AFK? (true/false)",
        silent="Hide AFK notification? (true/false)"
    )
    @app_commands.rename(global_="global")
    async def afk(
        self,
        interaction: discord.Interaction,
        reason: Optional[str] = None,
        global_: Optional[bool] = False,
        silent: Optional[bool] = False
    ):
        user = interaction.user
        reason_text = reason if reason else "No reason provided."
        afks[user.id] = {
            "reason": reason_text,
            "since": datetime.datetime.utcnow(),
            "global": global_ or False,
            "mention_count": 0
        }
        global_text = "🔕 You have set yourself AFK, with reason: \"{}\" (Global)".format(reason_text) if global_ else "🔕 You have set yourself AFK, with reason: \"{}\"".format(reason_text)
        embed = discord.Embed(
            title="AFK Set!",
            description=global_text,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=user.name, icon_url=user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=silent if silent is not None else False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        afk_data = afks.get(message.author.id)
        if afk_data:
            since = afk_data["since"]
            mention_count = afk_data.get("mention_count", 0)
            now = datetime.datetime.utcnow()
            delta = now - since
            seconds = int(delta.total_seconds())
            periods = [
                ('day', 60*60*24),
                ('hour', 60*60),
                ('minute', 60),
                ('second', 1)
            ]
            time_str = []
            for period_name, period_seconds in periods:
                if seconds >= period_seconds:
                    period_value, seconds = divmod(seconds, period_seconds)
                    if period_value > 0:
                        time_str.append(f"{period_value} {period_name}{'s' if period_value > 1 else ''}")
            time_str = ', '.join(time_str) if time_str else '0 seconds'
            await message.reply(f":stopwatch: Welcome back, {message.author.name}! You were AFK for **{time_str}** and received **{mention_count}** mention.", mention_author=False, delete_after=5)
            del afks[message.author.id]
            return

        mentioned_ids = [user.id for user in message.mentions]
        for user_id in mentioned_ids:
            afk_data = afks.get(user_id)
            if afk_data:
                afk_data["mention_count"] = afk_data.get("mention_count", 0) + 1
                since = afk_data["since"]
                reason = afk_data["reason"]
                user = message.guild.get_member(user_id)
                if user:
                    unix_ts = int(since.timestamp())
                    await message.reply(f"🔕 `{user.name}` is currently AFK for <t:{unix_ts}:R>: **{reason}**", mention_author=False, delete_after=5)
                break

async def setup(bot: commands.Bot):
    await bot.add_cog(AFK(bot)) 